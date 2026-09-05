(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.SettleLensEngine = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const validStatuses = new Set(['credited','rejected']);
  const reasonText = {
    INVALID_BENEFICIARY: 'the beneficiary details are invalid',
    ACCOUNT_CLOSED: 'the beneficiary account is closed',
    BANK_TEMPORARILY_UNAVAILABLE: 'the bank was temporarily unavailable',
    COMPLIANCE_HOLD: 'the payout is held for a compliance review',
    KYC_RESTRICTION: 'the merchant account has a KYC restriction'
  };
  const sum = rows => rows.reduce((total,row)=>total+row.amount_minor,0);
  const byTime = (a,b) => new Date(a.occurred_at)-new Date(b.occurred_at);
  const money = minor => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',minimumFractionDigits:0,maximumFractionDigits:2}).format(minor/100);

  function dedupe(rows, warnings) {
    const seen = new Map();
    for (const row of rows) {
      const key = `${row.source}:${row.source_record_id}`;
      if (!seen.has(key)) seen.set(key,row);
      else if (JSON.stringify(seen.get(key)) !== JSON.stringify(row)) warnings.push(`Conflicting duplicate source record: ${row.source_record_id}`);
    }
    return [...seen.values()];
  }

  function findingBase(transaction, records, warnings, overrides) {
    return {
      transaction_id: transaction.id,
      merchant_id: transaction.merchant_id,
      settlement_id: transaction.settlement_id,
      currency: transaction.currency || 'INR',
      evidence_record_ids: records.map(row=>row.source_record_id),
      warnings,
      ...overrides
    };
  }

  function reconcile(transaction, options={}) {
    const asOf = options.asOf || new Date().toISOString();
    const warnings=[];
    const gateway=dedupe(transaction.gateway || [],warnings);
    const bank=dedupe(transaction.bank || [],warnings);
    const ledger=dedupe(transaction.ledger || [],warnings);
    const records=[...gateway,...bank,...ledger];
    const evidence=records.sort(byTime);
    const capture=gateway.find(row=>row.event_type==='payment_captured');
    const fees=ledger.filter(row=>row.event_type==='fee_deduction');
    const credits=bank.filter(row=>row.status==='credited');
    const rejected=bank.filter(row=>row.status==='rejected').sort(byTime);
    const schedules=gateway.filter(row=>row.event_type==='settlement_scheduled').sort(byTime);
    const initiated=gateway.filter(row=>row.event_type==='settlement_initiated');
    const postings=ledger.filter(row=>row.event_type==='settlement_posted');
    const missing=[];

    if (!capture) missing.push('gateway payment capture');
    if (!fees.length) missing.push('ledger fee entry');
    const identityFields=['merchant_id','transaction_id','settlement_id','currency'];
    const identityConflict=identityFields.some(field=>records.some(row=>row[field]!==transaction[field]));
    const invalidAmount=records.some(row=>!Number.isSafeInteger(row.amount_minor)||row.amount_minor<0);
    const invalidOutcome=bank.some(row=>!validStatuses.has(row.status));
    if (!capture || identityConflict || invalidAmount || invalidOutcome) {
      const problems=[];
      if(!capture)problems.push('payment capture is missing');
      if(identityConflict)problems.push('record identifiers or currency conflict');
      if(invalidAmount)problems.push('an amount is not a non-negative integer in minor currency units');
      if(invalidOutcome)problems.push('a bank outcome is unsupported');
      return findingBase(transaction,evidence,warnings,{
        status:'review',reason_code:'DATA_INVALID',certainty:'Cannot determine',title:'The source data needs review.',
        explanation:`Settlement status cannot be calculated because ${problems.join(' and ')}.`,
        exception:'The loaded records failed validation. No settlement conclusion should be sent to the merchant.',
        next:'Correct or replace the invalid source records, then run reconciliation again.',
        captured_minor:capture?.amount_minor || 0,fees_minor:sum(fees),expected_minor:0,credited_minor:sum(credits),ledger_posted_minor:sum(postings),has_bank_credit:credits.length>0,missing_evidence:missing,as_of:asOf
      });
    }

    const feeTotal=sum(fees);
    const expected=capture.amount_minor-feeTotal;
    const credited=sum(credits);
    const posted=sum(postings);
    if (warnings.length) {
      return findingBase(transaction,evidence,warnings,{
        status:'review',reason_code:'DUPLICATE_SOURCE_RECORD',certainty:'Needs review',title:'Duplicate evidence needs review.',
        explanation:'One or more source record IDs appear more than once with conflicting values.',
        exception:'The duplicate records may change the calculated outcome.',next:'Resolve the duplicate source records before confirming settlement.',
        captured_minor:capture.amount_minor,fees_minor:feeTotal,expected_minor:expected,credited_minor:credited,ledger_posted_minor:posted,has_bank_credit:credits.length>0,missing_evidence:[],as_of:asOf
      });
    }
    if (credits.length && (credited!==expected || posted!==credited)) {
      const difference=Math.abs(expected-credited);
      return findingBase(transaction,evidence,warnings,{
        status:'review',reason_code:'AMOUNT_MISMATCH',certainty:'Credit confirmed',title:'A credit arrived. The amounts do not match.',
        explanation:`The bank credited ${money(credited)}, but the expected payable and ledger posting are ${money(expected)}. The unexplained difference is ${money(difference)}.`,
        exception:`No adjustment, refund, or allocation record explains the ${money(difference)} difference.`,
        next:'Check the bank credit and settlement allocation with finance before making any additional payout.',
        captured_minor:capture.amount_minor,fees_minor:feeTotal,expected_minor:expected,credited_minor:credited,ledger_posted_minor:posted,has_bank_credit:true,missing_evidence:[],as_of:asOf
      });
    }
    if (credits.length) {
      const retried=rejected.length>0;
      return findingBase(transaction,evidence,warnings,{
        status:'settled',reason_code:retried?'RETRY_SETTLED':'SETTLED_CONFIRMED',certainty:'Confirmed',
        title:retried?'The retry worked. Your money is settled.':'Settled, matched, and accounted for.',
        explanation:`The bank confirms ${money(credited)} credited. The captured payment of ${money(capture.amount_minor)}, less the recorded ${money(feeTotal)} fee, matches the ledger posting.${retried?' An earlier attempt was rejected before the successful retry.':''}`,
        exception:'',next:'No follow-up is needed. Use the bank reference in the evidence to locate the credit.',
        captured_minor:capture.amount_minor,fees_minor:feeTotal,expected_minor:expected,credited_minor:credited,ledger_posted_minor:posted,has_bank_credit:true,bank_reference:credits.at(-1)?.bank_reference || null,missing_evidence:[],as_of:asOf
      });
    }
    if (rejected.length) {
      const last=rejected.at(-1);
      const described=reasonText[last.reason_code];
      return findingBase(transaction,evidence,warnings,{
        status:'failed',reason_code:last.reason_code || 'BANK_REJECTED',certainty:'Failure confirmed',
        title:last.reason_code==='ACCOUNT_CLOSED'?'The bank rejected a closed account.':'The payment succeeded. The payout did not.',
        explanation:`The ${money(capture.amount_minor)} payment was captured. The ${money(expected)} settlement attempt was rejected because ${described || 'the bank returned an unmapped rejection code'}.`,
        exception:'No later successful attempt appears in the loaded records. A new payout date cannot be confirmed.',
        next:described?'Verify the beneficiary or account restriction, then confirm whether a retry is scheduled.':'Escalate the unmapped bank reason code to payment operations before advising the merchant.',
        captured_minor:capture.amount_minor,fees_minor:feeTotal,expected_minor:expected,credited_minor:0,ledger_posted_minor:posted,has_bank_credit:false,missing_evidence:[],as_of:asOf
      });
    }
    if (schedules.length) {
      const schedule=schedules.at(-1);
      const overdue=new Date(schedule.scheduled_for)<=new Date(asOf);
      return findingBase(transaction,evidence,warnings,{
        status:overdue?'review':'pending',reason_code:overdue?'SETTLEMENT_OVERDUE':'SETTLEMENT_SCHEDULED',certainty:'Schedule recorded',
        title:overdue?'The scheduled time passed without a bank outcome.':'Scheduled and not overdue.',
        explanation:overdue?`The ${money(expected)} settlement was scheduled for ${schedule.scheduled_for}, but no bank outcome is present as of ${asOf}.`:`The ${money(capture.amount_minor)} payment was captured and ${money(expected)} is scheduled for ${schedule.scheduled_for}.`,
        exception:overdue?'The records do not explain why the expected bank outcome is missing.':'A future bank credit is not guaranteed until the bank confirms it.',
        next:overdue?'Request the bank outcome and check holiday, cutoff, hold, and retry rules.':'Check the bank outcome after the scheduled payout time.',
        captured_minor:capture.amount_minor,fees_minor:feeTotal,expected_minor:expected,credited_minor:0,ledger_posted_minor:posted,has_bank_credit:false,missing_evidence:['bank settlement outcome'],as_of:asOf,scheduled_for:schedule.scheduled_for
      });
    }
    if (initiated.length) {
      return findingBase(transaction,evidence,warnings,{
        status:'review',reason_code:'BANK_OUTCOME_MISSING',certainty:'Outcome unknown',title:'Initiated, but the bank outcome is missing.',
        explanation:`The gateway initiated a ${money(expected)} settlement after capturing ${money(capture.amount_minor)}. No matching bank outcome is available.`,
        exception:'The bank outcome and confirmed settlement deadline are missing. A delay cause cannot be established.',
        next:'Obtain the bank outcome and expected deadline. Do not retry solely because the bank record is missing.',
        captured_minor:capture.amount_minor,fees_minor:feeTotal,expected_minor:expected,credited_minor:0,ledger_posted_minor:posted,has_bank_credit:false,missing_evidence:['bank settlement outcome','confirmed settlement deadline'],as_of:asOf
      });
    }
    return findingBase(transaction,evidence,warnings,{
      status:'review',reason_code:'SETTLEMENT_INSTRUCTION_MISSING',certainty:'Outcome unknown',title:'No settlement instruction was found.',
      explanation:'The payment was captured, but no settlement schedule or initiation record is available.',
      exception:'The gateway settlement instruction is missing.',next:'Check the gateway settlement configuration and retrieve the missing instruction.',
      captured_minor:capture.amount_minor,fees_minor:feeTotal,expected_minor:expected,credited_minor:0,ledger_posted_minor:posted,has_bank_credit:false,missing_evidence:['gateway settlement instruction','bank settlement outcome'],as_of:asOf
    });
  }

  return Object.freeze({reconcile,money});
});
