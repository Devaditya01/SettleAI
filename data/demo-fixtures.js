(function (root, factory) {
  const dataset = factory();
  if (typeof module === 'object' && module.exports) module.exports = dataset;
  if (root) root.SettleLensDemoData = dataset;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const merchantId = 'merchant_northstar_demo';
  const asOf = '2026-09-04T18:00:00+05:30';
  const specs = [
    {n:1041,customer:'Maya Rao',amount:849900,date:'2026-09-03',outcome:'settled',retry:true,creditDate:'2026-09-04'},
    {n:1042,customer:'Aarav Mehta',amount:250000,date:'2026-09-03',outcome:'rejected',reason:'INVALID_BENEFICIARY'},
    {n:1043,customer:'Kabir Sethi',amount:399900,date:'2026-09-02',outcome:'settled',creditDate:'2026-09-03'},
    {n:1044,customer:'Zoya Khan',amount:1299900,date:'2026-09-04',outcome:'scheduled',scheduledFor:'2026-09-07T09:00:00+05:30'},
    {n:1045,customer:'Isha Kapoor',amount:59900,date:'2026-09-01',outcome:'settled',creditDate:'2026-09-01'},
    {n:1046,customer:'Rohan Das',amount:749900,date:'2026-09-03',outcome:'missing_bank'},
    {n:1047,customer:'Ananya Roy',amount:199900,date:'2026-09-01',outcome:'settled',creditDate:'2026-09-02'},
    {n:1048,customer:'Dev Malhotra',amount:149900,date:'2026-09-03',outcome:'rejected',reason:'ACCOUNT_CLOSED'},
    {n:1049,customer:'Nisha Patel',amount:329900,date:'2026-09-04',outcome:'scheduled',scheduledFor:'2026-09-07T09:00:00+05:30'},
    {n:1050,customer:'Arjun Shah',amount:999900,date:'2026-09-02',outcome:'mismatch',creditDate:'2026-09-03',creditDifference:20000},
    {n:1051,customer:'Tara Menon',amount:459900,date:'2026-09-02',outcome:'settled',creditDate:'2026-09-02'},
    {n:1052,customer:'Neil Verma',amount:89900,date:'2026-09-01',outcome:'settled',creditDate:'2026-09-01'}
  ];

  const gateway = [];
  const bank = [];
  const ledger = [];
  const transactions = [];

  function base(spec) {
    return {
      merchant_id: merchantId,
      transaction_id: `TXN-${spec.n}`,
      settlement_id: `SET-${spec.n}`,
      currency: 'INR'
    };
  }

  for (const spec of specs) {
    const common = base(spec);
    const fee = Math.round(spec.amount * 0.02);
    const payable = spec.amount - fee;
    const captureAt = `${spec.date}T10:02:00+05:30`;
    transactions.push({
      ...common,
      customer: spec.customer,
      payment_date: spec.date,
      captured_minor: spec.amount,
      scenario: spec.outcome
    });
    gateway.push({...common,source:'gateway',source_record_id:`G-${spec.n}-01`,event_type:'payment_captured',status:'captured',amount_minor:spec.amount,occurred_at:captureAt,attempt_id:''});
    ledger.push({...common,source:'ledger',source_record_id:`L-${spec.n}-01`,event_type:'captured_receivable',status:'posted',amount_minor:spec.amount,occurred_at:`${spec.date}T10:02:02+05:30`,attempt_id:''});
    ledger.push({...common,source:'ledger',source_record_id:`L-${spec.n}-02`,event_type:'fee_deduction',status:'posted',amount_minor:fee,occurred_at:`${spec.date}T10:02:03+05:30`,attempt_id:''});

    if (spec.outcome === 'scheduled') {
      gateway.push({...common,source:'gateway',source_record_id:`G-${spec.n}-02`,event_type:'settlement_scheduled',status:'scheduled',amount_minor:payable,occurred_at:`${spec.date}T10:05:00+05:30`,scheduled_for:spec.scheduledFor,attempt_id:''});
      continue;
    }

    const attemptDate = spec.creditDate || '2026-09-04';
    const firstAt = attemptDate === spec.date ? `${attemptDate}T11:00:00+05:30` : `${attemptDate}T09:00:00+05:30`;
    gateway.push({...common,source:'gateway',source_record_id:`G-${spec.n}-02`,event_type:'settlement_initiated',status:'initiated',amount_minor:payable,occurred_at:firstAt,attempt_id:`ATT-${spec.n}-1`});

    if (spec.outcome === 'rejected' || spec.retry) {
      bank.push({...common,source:'bank',source_record_id:`B-${spec.n}-01`,event_type:'settlement_outcome',status:'rejected',amount_minor:payable,occurred_at:`${attemptDate}T09:06:00+05:30`,attempt_id:`ATT-${spec.n}-1`,reason_code:spec.reason || 'BANK_TEMPORARILY_UNAVAILABLE',bank_reference:''});
    }
    if (spec.retry) {
      gateway.push({...common,source:'gateway',source_record_id:`G-${spec.n}-03`,event_type:'settlement_initiated',status:'initiated',amount_minor:payable,occurred_at:`${attemptDate}T11:00:00+05:30`,attempt_id:`ATT-${spec.n}-2`});
    }
    if (spec.outcome === 'settled' || spec.outcome === 'mismatch') {
      const attempt = spec.retry ? 2 : 1;
      const credited = payable - (spec.creditDifference || 0);
      bank.push({...common,source:'bank',source_record_id:`B-${spec.n}-${String(attempt).padStart(2,'0')}`,event_type:'settlement_outcome',status:'credited',amount_minor:credited,occurred_at:`${attemptDate}T11:32:00+05:30`,attempt_id:`ATT-${spec.n}-${attempt}`,reason_code:'',bank_reference:`UTR_DEMO_${spec.n}`});
      ledger.push({...common,source:'ledger',source_record_id:`L-${spec.n}-03`,event_type:'settlement_posted',status:'posted',amount_minor:payable,occurred_at:`${attemptDate}T11:35:00+05:30`,attempt_id:`ATT-${spec.n}-${attempt}`});
    }
  }

  return Object.freeze({
    schema_version: '1.0.0',
    merchant_id: merchantId,
    merchant_name: 'Northstar Store',
    as_of: asOf,
    transactions: Object.freeze(transactions),
    sources: Object.freeze({gateway:Object.freeze(gateway),bank:Object.freeze(bank),ledger:Object.freeze(ledger)})
  });
});
