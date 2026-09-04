'use strict';

// Entirely local prototype: no network requests, database, authentication, or LLM.
const ICONS = {
  overview: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  transactions: '<path d="M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4"/>',
  alert: '<path d="m10.3 4-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4h.01"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
  sparkles: '<path d="m12 3 2.8 6.2L21 12l-6.2 2.8L12 21l-2.8-6.2L3 12l6.2-2.8L12 3ZM20 2v4m-2-2h4"/>',
  'arrow-right': '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  'arrow-up-right': '<path d="M6 18 18 6M6 6h12v12"/>',
  'arrow-up': '<path d="M12 20V4m-6 6 6-6 6 6"/>',
  chevrons: '<path d="m8 9 4-4 4 4m-8 6 4 4 4-4"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4m0 4h.01"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 15v5h16v-5"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 11h18"/>',
  card: '<rect x="2" y="5" width="20" height="14" rx="3"/><path d="M2 10h20M6 15h4"/>',
  bank: '<path d="m3 8 9-5 9 5H3Zm2 3v7m7-7v7m7-7v7M3 21h18M3 18h18"/>',
  ledger: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h4"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  link: '<path d="m10 13 4-4m-5 7-2 2a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 0 2-2a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0"/>',
  file: '<path d="M14 2H5v20h14V7l-5-5Zm0 0v6h5M8 12h8m-8 4h6"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.file}</svg>`;
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const escapeHTML = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const money = minor => new Intl.NumberFormat('en-IN', {style:'currency',currency:'INR',maximumFractionDigits:2,minimumFractionDigits:0}).format(minor / 100);
const shortMoney = minor => minor >= 10000000 ? `₹${(minor/10000000).toFixed(1)}L` : minor >= 100000 ? `₹${(minor/100000).toFixed(1)}k` : money(minor);
const dateLabel = date => new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'Asia/Kolkata'}).format(new Date(date+'T12:00:00+05:30'));
const timeLabel = date => new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Kolkata'}).format(new Date(date));
const MERCHANT = 'merchant_northstar_demo';
const AS_OF = '2026-09-04T18:00:00+05:30';
const STATUS_LABEL = {settled:'Settled',pending:'Pending',failed:'Failed',review:'Needs review'};
const fixtureRows = [
  {n:1042,customer:'Aarav Mehta',amount:250000,date:'2026-09-03',status:'failed',reason:'INVALID_BENEFICIARY'},
  {n:1041,customer:'Maya Rao',amount:849900,date:'2026-09-03',status:'settled',retry:true,creditDate:'2026-09-04'},
  {n:1043,customer:'Kabir Sethi',amount:399900,date:'2026-09-02',status:'settled',creditDate:'2026-09-03'},
  {n:1044,customer:'Zoya Khan',amount:1299900,date:'2026-09-04',status:'pending'},
  {n:1045,customer:'Isha Kapoor',amount:59900,date:'2026-09-01',status:'settled',creditDate:'2026-09-01'},
  {n:1046,customer:'Rohan Das',amount:749900,date:'2026-09-03',status:'review',missing:true},
  {n:1047,customer:'Ananya Roy',amount:199900,date:'2026-09-01',status:'settled',creditDate:'2026-09-02'},
  {n:1048,customer:'Dev Malhotra',amount:149900,date:'2026-09-03',status:'failed',reason:'ACCOUNT_CLOSED'},
  {n:1049,customer:'Nisha Patel',amount:329900,date:'2026-09-04',status:'pending'},
  {n:1050,customer:'Arjun Shah',amount:999900,date:'2026-09-02',status:'review',mismatch:true,creditDate:'2026-09-03'},
  {n:1051,customer:'Tara Menon',amount:459900,date:'2026-09-02',status:'settled',creditDate:'2026-09-02'},
  {n:1052,customer:'Neil Verma',amount:89900,date:'2026-09-01',status:'settled',creditDate:'2026-09-01'}
];

// Fixtures contain observable records. Explanations below are derived from these records.
function makeFixture(f) {
  const id = `TXN-${f.n}`, settlementId = `SET-${f.n}`, fee = Math.round(f.amount * .02);
  const expected = f.amount - fee;
  const base = {merchant_id:MERCHANT,transaction_id:id,settlement_id:settlementId,currency:'INR'};
  const gateway = [{...base,record_id:`G-${f.n}-01`,event:'payment_captured',amount_minor:f.amount,event_at:`${f.date}T10:02:00+05:30`}];
  const ledger = [
    {...base,record_id:`L-${f.n}-01`,entry_type:'captured_receivable',amount_minor:f.amount,event_at:`${f.date}T10:02:02+05:30`},
    {...base,record_id:`L-${f.n}-02`,entry_type:'fee_deduction',amount_minor:fee,event_at:`${f.date}T10:02:03+05:30`}
  ];
  const bank = [];
  if (f.status === 'pending') {
    gateway.push({...base,record_id:`G-${f.n}-02`,event:'settlement_scheduled',amount_minor:expected,event_at:`${f.date}T10:05:00+05:30`,scheduled_for:'2026-09-07T09:00:00+05:30'});
  } else {
    const attemptDate = f.creditDate || '2026-09-04';
    gateway.push({...base,record_id:`G-${f.n}-02`,event:'settlement_initiated',attempt_id:`ATT-${f.n}-1`,amount_minor:expected,event_at:`${attemptDate}T09:00:00+05:30`});
    // Same-day fixtures are initiated after capture; prior-day captures retain 09:00.
    if (attemptDate === f.date) gateway[1].event_at = `${attemptDate}T11:00:00+05:30`;
    if (f.status === 'failed' || f.retry) bank.push({...base,record_id:`B-${f.n}-01`,attempt_id:`ATT-${f.n}-1`,status:'rejected',amount_minor:expected,reason_code:f.reason || 'BANK_TEMPORARILY_UNAVAILABLE',event_at:`${attemptDate}T09:06:00+05:30`});
    if (f.retry) gateway.push({...base,record_id:`G-${f.n}-03`,event:'settlement_initiated',attempt_id:`ATT-${f.n}-2`,amount_minor:expected,event_at:`${attemptDate}T11:00:00+05:30`});
    if (f.status === 'settled' || f.mismatch) {
      bank.push({...base,record_id:`B-${f.n}-${f.retry?'02':'01'}`,attempt_id:`ATT-${f.n}-${f.retry?2:1}`,status:'credited',amount_minor:expected-(f.mismatch?20000:0),bank_reference:`UTR_DEMO_${f.n}`,event_at:`${attemptDate}T11:32:00+05:30`});
      ledger.push({...base,record_id:`L-${f.n}-03`,entry_type:'settlement_posted',amount_minor:expected,event_at:`${attemptDate}T11:35:00+05:30`});
    }
  }
  return {...f,id,settlementId,fee,expected,gateway,bank,ledger};
}
const transactions = fixtureRows.map(makeFixture);
const state = {view:'overview',filter:'all',search:'',date:'all',selected:'TXN-1042'};
const sourceRecords = type => transactions.flatMap(t => t[type]);
const statusBadge = status => `<span class="status ${status}">${STATUS_LABEL[status]}</span>`;
function reconcile(t) {
  const capture = t.gateway.find(r=>r.event==='payment_captured');
  const fees = t.ledger.filter(r=>r.entry_type==='fee_deduction').reduce((sum,r)=>sum+r.amount_minor,0);
  const expected = capture.amount_minor-fees;
  const credits = t.bank.filter(r=>r.status==='credited');
  const credited = credits.reduce((sum,r)=>sum+r.amount_minor,0);
  const lastBank = [...t.bank].sort((a,b)=>new Date(b.event_at)-new Date(a.event_at))[0];
  const schedule = t.gateway.find(r=>r.event==='settlement_scheduled');
  const posted = t.ledger.filter(r=>r.entry_type==='settlement_posted').reduce((sum,r)=>sum+r.amount_minor,0);
  let status, title, explanation, exception, next, certainty;
  if (credits.length && (credited!==expected || posted!==credited)) {
    status='review';title='A credit arrived. The amounts don’t match.';certainty='Credit confirmed';
    explanation=`The bank credited ${money(credited)}, but the expected payable and ledger posting are ${money(expected)}. There is an unexplained difference of ${money(Math.abs(expected-credited))}.`;
    exception=`The records do not explain the ${money(Math.abs(expected-credited))} difference. No supporting adjustment or refund entry is available.`;
    next='Check the bank credit and settlement allocation with finance. Verify the difference before making any additional payout.';
  } else if (credits.length) {
    status='settled';title=t.retry?'The retry worked. Your money is settled.':'Settled, matched, and accounted for.';certainty='Confirmed';
    explanation=`The bank confirms a credit of ${money(credited)}. The captured payment of ${money(capture.amount_minor)}, less the recorded ${money(fees)} fee, matches the ledger posting.${t.retry?' The earlier failed attempt was followed by a successful retry.':''}`;
    exception='';next='No follow-up is needed for the loaded records. Use the bank reference in the evidence if you need to locate the credit.';
  } else if (lastBank?.status==='rejected') {
    status='failed';certainty='Failure confirmed';title=lastBank.reason_code==='ACCOUNT_CLOSED'?'The bank rejected a closed account.':'The payment succeeded. The payout didn’t.';
    const reason = lastBank.reason_code==='ACCOUNT_CLOSED'?'the beneficiary account is closed':'the beneficiary details are invalid';
    explanation=`Your ${money(capture.amount_minor)} payment was captured. The ${money(expected)} settlement attempt was rejected because ${reason}. The recorded fee is ${money(fees)}.`;
    exception='No subsequent retry appears in the loaded records. A new payout date cannot be confirmed.';
    next='Verify the beneficiary details with the merchant, then ask the payments team to confirm whether a retry is scheduled.';
  } else if (schedule) {
    status='pending';certainty='Schedule recorded';title='On the schedule. Not overdue.';
    explanation=`The ${money(capture.amount_minor)} payment was captured. A settlement of ${money(expected)} is scheduled for ${timeLabel(schedule.scheduled_for)} IST. That date is after this demo’s 04 Sep snapshot.`;
    exception='The scheduled date is recorded, but a future bank credit is not guaranteed.';
    next='Check the bank outcome after the scheduled payout. No failed bank attempt is present in the loaded records.';
  } else {
    status='review';certainty='Outcome unknown';title='Initiated, but the bank outcome is missing.';
    explanation=`The gateway initiated a ${money(expected)} settlement after capturing ${money(capture.amount_minor)}. There is no matching bank outcome in the loaded data, so credit or failure cannot be confirmed.`;
    exception='The bank outcome and a confirmed settlement deadline are missing. Neither a delay cause nor an overdue status can be established.';
    next='Obtain the bank outcome for this settlement and verify the expected deadline. Do not retry solely because the bank record is missing.';
  }
  return {transaction_id:t.id,merchant_id:MERCHANT,status,title,explanation,exception,next,certainty,captured_minor:capture.amount_minor,fees_minor:fees,expected_minor:expected,credited_minor:credited,has_bank_credit:credits.length>0,ledger_posted_minor:posted,bank_reference:credits[0]?.bank_reference||null,as_of:AS_OF};
}
const getSelected = () => transactions.find(t=>t.id===state.selected);
function renderIcons(root=document){root.querySelectorAll('[data-icon]').forEach(el=>{el.innerHTML=icon(el.dataset.icon);});}
function filteredRows(){
  return transactions.filter(t=>{
    const r=reconcile(t), attention=['failed','review'].includes(r.status);
    return (state.view!=='exceptions'||attention) && (state.filter==='all'||(state.filter==='attention'?attention:r.status===state.filter)) && (state.date==='all'||t.date===state.date) && (!state.search||`${t.id} ${t.customer}`.toLowerCase().includes(state.search.toLowerCase()));
  });
}
function renderMetrics(){
  const settled=transactions.filter(t=>reconcile(t).status==='settled');
  const pending=transactions.filter(t=>reconcile(t).status==='pending');
  const attention=transactions.filter(t=>['failed','review'].includes(reconcile(t).status));
  const metrics=[
    {label:'Settled & reconciled',value:shortMoney(settled.reduce((s,t)=>s+reconcile(t).credited_minor,0)),note:`${settled.length} transactions matched`,icon:'bank',color:'#81b5a0',points:'0,23 8,18 15,20 24,11 31,14 40,7 49,11 58,2'},
    {label:'Awaiting settlement',value:shortMoney(pending.reduce((s,t)=>s+reconcile(t).expected_minor,0)),note:`${pending.length} payouts scheduled`,icon:'clock',color:'#c8ad7c',points:'0,22 10,18 20,18 28,11 40,11 48,7 58,7'},
    {label:'Needs your attention',value:String(attention.length).padStart(2,'0'),note:'2 failed · 2 to review',icon:'alert',color:'#cba0b1',points:'0,20 10,16 21,19 30,9 41,9 48,4 58,4'}
  ];
  $('#metrics').innerHTML=metrics.map(m=>`<article class="metric"><div class="metric-label">${m.label}<span class="metric-icon">${icon(m.icon)}</span></div><strong>${m.value}</strong><div class="metric-bottom"><i></i>${m.note}</div><svg class="metric-sparkline" viewBox="0 0 60 28" aria-hidden="true"><polyline points="${m.points}" fill="none" stroke="${m.color}" stroke-width="1.5"/></svg></article>`).join('');
  $('#nav-exceptions').textContent=attention.length;
  const credited=transactions.filter(t=>reconcile(t).has_bank_credit);
  $('#flow-total').textContent=money(credited.reduce((s,t)=>s+reconcile(t).credited_minor,0));
  $('#flow-count').textContent=`${credited.length} credits · includes 1 amount mismatch`;
  const days=['2026-09-01','2026-09-02','2026-09-03','2026-09-04'];
  const values=days.map(d=>transactions.flatMap(t=>t.bank).filter(r=>r.status==='credited'&&r.event_at.startsWith(d)).reduce((s,r)=>s+r.amount_minor,0));
  const max=Math.max(...values);
  $('#chart').innerHTML=days.map((d,i)=>`<div class="chart-column" title="${dateLabel(d)}: ${money(values[i])}"><span class="chart-value">${shortMoney(values[i])}</span><div class="chart-bar" style="height:${Math.round(values[i]/max*55)}px"></div><span class="chart-date">0${i+1} Sep</span></div>`).join('');
  $('#chart').setAttribute('aria-label',days.map((d,i)=>`${dateLabel(d)}: ${money(values[i])}`).join('; '));
}
function renderTable(){
  const rows=filteredRows();
  $('#transaction-count').textContent=rows.length;
  $('#transaction-rows').innerHTML=rows.length?rows.map(t=>`<tr data-id="${t.id}" class="${state.selected===t.id?'selected':''}"><td><button class="transaction-id" aria-label="Investigate ${t.id}">${t.id}</button><span class="customer-name">${t.customer}</span></td><td class="amount-cell">${money(t.amount)}</td><td>${statusBadge(reconcile(t).status)}</td><td class="date-cell">${dateLabel(t.date)}</td><td>${icon('chevron')}</td></tr>`).join(''):`<tr><td class="empty-state" colspan="5"><strong>No matching transactions</strong><p>Try another ID, customer, date, or status.</p><button class="button button-outline" id="reset-filters">Clear filters</button></td></tr>`;
  $('#table-summary').textContent=`Showing ${rows.length} of ${transactions.length} demo transactions`;
  $$('.tab').forEach(b=>{b.classList.toggle('active',b.dataset.filter===state.filter);b.setAttribute('aria-pressed',String(b.dataset.filter===state.filter));});
}
function timeline(t){
  const capture=t.gateway.find(r=>r.event==='payment_captured');
  const events=[{at:capture.event_at,title:'Payment captured',detail:`${money(t.amount)} · ${capture.record_id}`,kind:'settled',icon:'check'}];
  const fee=t.ledger.find(r=>r.entry_type==='fee_deduction');
  events.push({at:fee.event_at,title:'Merchant payable recorded',detail:`${money(t.expected)} after fees · ${fee.record_id}`,kind:'settled',icon:'check'});
  t.gateway.filter(r=>r.event==='settlement_initiated').forEach(r=>events.push({at:r.event_at,title:r.attempt_id.endsWith('-2')?'Retry initiated':'Settlement initiated',detail:r.attempt_id,kind:'settled',icon:'check'}));
  t.gateway.filter(r=>r.event==='settlement_scheduled').forEach(r=>events.push({at:r.event_at,title:'Future payout scheduled',detail:`${timeLabel(r.scheduled_for)} IST · ${r.record_id}`,kind:'pending',icon:'clock'}));
  t.bank.forEach(r=>events.push({at:r.event_at,title:r.status==='credited'?'Bank credit confirmed':'Bank rejected attempt',detail:r.status==='credited'?`${money(r.amount_minor)} · ${r.record_id}`:`${r.reason_code.replaceAll('_',' ').toLowerCase()} · ${r.record_id}`,kind:r.status==='credited'?'settled':'failed',icon:r.status==='credited'?'check':'close'}));
  const sorted=events.sort((a,b)=>new Date(a.at)-new Date(b.at));
  if(t.missing)sorted.push({at:AS_OF,title:'Bank outcome unavailable',detail:'Unknown as of this snapshot',kind:'review',icon:'help'});
  return sorted;
}
function renderTimeline(t,full=false){
  let events=timeline(t);
  if(!full&&events.length>4)events=[events[0],events[1],...events.slice(-2)];
  return events.map(e=>`<div class="timeline-step"><span class="timeline-step-icon ${e.kind}">${icon(e.icon)}</span><div><strong>${e.title}</strong><small>${full?`${timeLabel(e.at)} IST · `:''}${escapeHTML(e.detail)}</small></div></div>`).join('');
}
function evidenceChips(t){return ['gateway','bank','ledger'].map(type=>`<button class="evidence-chip" data-source="${type}" data-transaction="${t.id}">${icon(type==='gateway'?'card':type==='bank'?'bank':'ledger')}${type[0].toUpperCase()+type.slice(1)} <span>${t[type].length?'↗':'· missing'}</span></button>`).join('');}
function selectTransaction(id,question,scroll=false){
  const t=transactions.find(t=>t.id===id);if(!t)return;
  state.selected=id;const r=reconcile(t);
  const defaultQuestion=r.status==='settled'?`Has ${id} settled successfully?`:r.status==='pending'?`When will ${id} settle?`:r.status==='failed'?`Why hasn’t ${id} settled?`:`What happened to ${id}?`;
  $('#investigation-content').innerHTML=`<div class="query-bubble">${escapeHTML(question||defaultQuestion)}<small>Northstar Store · ${id}</small></div><div class="response-label">${icon('sparkles')}Settle copilot<span>Local evidence</span></div>${statusBadge(r.status)}<h3 class="answer-title">${r.title}</h3><p class="answer-description">${escapeHTML(r.explanation)}</p><div class="evidence-chips">${evidenceChips(t)}</div><div class="mini-timeline">${renderTimeline(t)}</div><div class="exception-box ${r.exception?'':'no-exception'}"><div class="exception-box-title">${icon(r.exception?'alert':'shield')}${r.exception?'What we can’t confirm':'The records agree'}</div><p>${escapeHTML(r.exception||'No exceptions detected in the loaded gateway, bank, and ledger records.')}</p></div><p class="next-step"><strong>Next step</strong><br>${escapeHTML(r.next)}</p><button class="trace-button" data-trace="${t.id}">View full investigation ${icon('arrow-up-right')}</button><div id="followups"></div>`;
  renderTable();
  $('#copilot-body').scrollTop=0;
  if(scroll&&window.innerWidth<=850)$('.copilot').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
}
const dialog=$('#detail-dialog');
let restoreFocus=null;
function openDialog(title,content,eyebrow='INVESTIGATION'){
  restoreFocus=document.activeElement;$('#dialog-title').textContent=title;$('#dialog-eyebrow').textContent=eyebrow;$('#dialog-content').innerHTML=content;if(!dialog.open)dialog.showModal();$('#dialog-close').focus();
}
function closeDialog(){dialog.close();if(restoreFocus?.isConnected)restoreFocus.focus();}
function breakdownHTML(t){
  const r=reconcile(t);
  return `<div class="breakdown-row"><span>Payment captured</span><strong>${money(r.captured_minor)}</strong></div><div class="breakdown-row"><span>Recorded fee deduction</span><strong>−${money(r.fees_minor)}</strong></div><div class="breakdown-row total"><span>Expected payable</span><strong>${money(r.expected_minor)}</strong></div><div class="breakdown-row"><span>Confirmed bank credit</span><strong>${r.has_bank_credit?money(r.credited_minor):'Not confirmed'}</strong></div>${r.has_bank_credit?`<div class="breakdown-row"><span>Difference from expected</span><strong>${money(Math.abs(r.expected_minor-r.credited_minor))}</strong></div>`:''}`;
}
function showTrace(id){
  const t=transactions.find(t=>t.id===id),r=reconcile(t);
  openDialog(`${t.id} · Full investigation`,`<div class="detail-summary"><p>${t.customer} · Northstar Store<br>Snapshot: 04 Sep 2026, 18:00 IST</p>${statusBadge(r.status)}</div><h3 class="answer-title">${r.title}</h3><p class="detail-description">${r.explanation}</p><div class="detail-grid"><div><h3 class="detail-heading">The complete timeline</h3><div class="detail-timeline">${renderTimeline(t,true)}</div></div><div><h3 class="detail-heading">Follow the money</h3>${breakdownHTML(t)}<p class="guide-notice">The demo records one fee deduction per payment. These synthetic amounts do not represent a provider’s fee or tax policy.</p></div></div><div class="exception-box ${r.exception?'':'no-exception'}"><div class="exception-box-title">${icon(r.exception?'alert':'check')}${r.exception?'Open exception':'No exceptions detected'}</div><p>${r.exception||'All loaded records reconcile for this transaction.'}</p></div><p class="next-step"><strong>Recommended next step</strong><br>${r.next}</p><h3 class="detail-heading">Inspect the evidence</h3><div class="evidence-list">${evidenceChips(t)}</div><button class="button button-outline" style="margin-top:20px" data-export-case="${id}">${icon('download')}Export investigation JSON</button>`);
}
function showEvidence(type,id){
  const t=transactions.find(t=>t.id===id),records=t[type];
  openDialog(`${type[0].toUpperCase()+type.slice(1)} evidence · ${id}`,`<p class="detail-description">${records.length?`${records.length} synthetic record${records.length===1?'':'s'} from this transaction.`:'No matching bank records are available. Absence of a record does not establish payment failure.'} All timestamps include the +05:30 timezone offset.</p><pre class="record-json">${escapeHTML(JSON.stringify(records.length?records:{transaction_id:id,source:type,records:[],finding:'Bank outcome unknown',source_snapshot:AS_OF},null,2))}</pre><button class="button button-outline" data-trace="${id}">${icon('arrow-right')}Back to full investigation</button>`,'SOURCE EVIDENCE');
}
function showGuide(){
  openDialog('Meet your settlement copilot.',`<p class="guide-intro">One place to answer the question that keeps coming back: <strong>“Where is my settlement?”</strong></p><div class="guide-step"><span class="guide-number">1</span><div><strong>Find a payment</strong><p>Search an ID or customer, filter by payment date, or open the exceptions queue.</p></div></div><div class="guide-step"><span class="guide-number">2</span><div><strong>Connect the evidence</strong><p>Select a transaction to inspect its gateway, bank, and ledger records. Open the full investigation to see every retry.</p></div></div><div class="guide-step"><span class="guide-number">3</span><div><strong>Know what’s known</strong><p>Read the confirmed outcome, inspect any uncertainty, and export a case summary for support.</p></div></div><div class="guide-scenarios"><button data-demo-case="TXN-1042">Bank rejection ↗</button><button data-demo-case="TXN-1041">Successful retry ↗</button><button data-demo-case="TXN-1046">Missing evidence ↗</button><button data-demo-case="TXN-1050">Amount mismatch ↗</button></div><p class="guide-notice"><strong>Prototype scope:</strong> 12 synthetic transactions, one demo merchant, and a fixed snapshot of 04 Sep 2026. Responses use local rules and templates. Login, merchant authorization, live integrations, database access, and an LLM are not implemented. The illustrated analyst identity is not an authenticated account.</p>`,'A QUICK TOUR');
}
function renderSources(){
  const sources=[{key:'gateway',title:'Payment gateway',file:'gateway_logs.csv',icon:'card',description:'Captured payments, scheduled settlements, and payout initiation events.'},{key:'bank',title:'Bank settlements',file:'bank_settlements.csv',icon:'bank',description:'Recorded credit outcomes and failed payout attempts. Missing outcomes remain unknown.'},{key:'ledger',title:'Merchant ledger',file:'ledger_entries.csv',icon:'ledger',description:'Captured receivables, recorded fee deductions, and settlement postings.'}];
  $('#source-view').innerHTML=`<p class="source-intro">The same transaction IDs connect three independent views of a payment. Inspect or download the synthetic records behind every answer.</p>${sources.map(s=>`<article class="card source-card"><div class="source-card-header"><span class="source-card-icon">${icon(s.icon)}</span><div><h2>${s.title}</h2><p>${s.file}</p></div><span class="source-pill">Fixture loaded</span></div><p class="source-intro">${s.description}</p><div class="source-meta"><div><strong>${sourceRecords(s.key).length}</strong>source records</div><div><strong>04 Sep, 18:00</strong>snapshot · IST</div><div><strong>1 merchant</strong>Northstar Store</div></div><button class="button button-outline" data-download-source="${s.key}">${icon('download')}Download mock CSV</button></article>`).join('')}<p class="source-footnote">These fixtures intentionally include one missing bank outcome and one unexplained amount mismatch. No real bank, gateway, or merchant account is connected.</p>`;
}
function setView(view){
  state.view=view;state.filter='all';state.search='';state.date='all';$('#transaction-search').value='';$('#date-filter').value='all';
  const info={overview:['Overview','Your money. In the clear.','A little less chasing. A lot more clarity.'],transactions:['Transactions','Every payment, connected.','Follow a payment from capture to bank credit.'],exceptions:['Exceptions','The gaps worth a closer look.','Failed attempts and records that need verification.'],sources:['Data sources','The evidence behind the answer.','Three sources. One connected view of your payments.']}[view];
  $('#breadcrumb-current').textContent=info[0];$('#page-title').textContent=info[1];$('#page-subtitle').textContent=info[2];
  $$('.nav-item').forEach(b=>{b.classList.toggle('active',b.dataset.view===view);if(b.dataset.view===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  $('#hero').hidden=view!=='overview';$('#flow-card').hidden=view!=='overview';$('#metrics').hidden=view==='sources';$('#transaction-card').hidden=view==='sources';$('#source-view').hidden=view!=='sources';$('.tabs').hidden=view==='exceptions';$('#table-title').textContent=view==='exceptions'?'Exception queue':'Transactions';
  $('#export-button').hidden=view==='sources';renderTable();if(view==='sources')renderSources();
}
function appendFollowup(question,answer){
  const content=document.createElement('div');content.className='followup-response';content.innerHTML=`<div class="query-bubble">${escapeHTML(question)}</div><div class="response-label">${icon('sparkles')}Settle copilot<span>Local evidence</span></div>${answer}`;$('#followups').append(content);const body=$('#copilot-body');body.scrollTop=body.scrollHeight;
}
function ask(question){
  question=question.trim().slice(0,600);if(!question)return;
  const matches=question.match(/\bTXN[-\s]?\d+\b/gi)||[];
  const ids=[...new Set(matches.map(x=>x.toUpperCase().replace(/^TXN[-\s]?/,'TXN-')))];
  if(ids.length>1){appendFollowup(question,'<p>This demo investigates one transaction at a time. Select one transaction ID, or use the transaction list to compare statuses.</p>');return;}
  if(ids.length&&!transactions.some(t=>t.id===ids[0])){appendFollowup(question,`<p>No matching record for <strong>${escapeHTML(ids[0])}</strong> in Northstar Store’s 12 demo transactions. This does not establish whether the transaction exists elsewhere.</p>`);return;}
  const t=ids.length?transactions.find(t=>t.id===ids[0]):getSelected();
  if(ids.length&&t.id!==state.selected)selectTransaction(t.id,question);
  const r=reconcile(t), q=question.toLowerCase();
  if(/breakdown|deduct|fee|amount|how much/.test(q))appendFollowup(question,`<p>Here is the recorded breakdown for <strong>${t.id}</strong>.</p><div class="mini-breakdown">${breakdownHTML(t)}</div><div class="evidence-chips">${evidenceChips(t)}</div>`);
  else if(/next|should|action|retry|fix/.test(q))appendFollowup(question,`<p>${escapeHTML(r.next)}</p><p>${escapeHTML(r.exception||'No open exception was detected in the loaded records.')}</p>`);
  else if(/missing|exception|uncertain|sure|confiden/.test(q))appendFollowup(question,`<p><strong>${escapeHTML(r.certainty)}.</strong> ${escapeHTML(r.exception||'The credited amount, expected payable, and ledger posting agree in the loaded records.')}</p><div class="evidence-chips">${evidenceChips(t)}</div>`);
  else if(ids.length||/status|why|settle|credit|payout|trace|happened/.test(q))selectTransaction(t.id,question);
  else appendFollowup(question,`<p>This local demo can explain the status, amount breakdown, next step, and missing evidence for <strong>${t.id}</strong>. Try “What’s the status?” or enter another demo transaction ID.</p>`);
  if(window.innerWidth<=850)$('.copilot').scrollIntoView({behavior:'smooth',block:'start'});
}
function notify(message){const toast=$('#toast');toast.textContent=message;toast.classList.add('show');clearTimeout(notify.timer);notify.timer=setTimeout(()=>toast.classList.remove('show'),3500);}
function download(filename,content,type){const blob=new Blob([content],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);notify(`Downloaded ${filename}`);}
function csv(rows){const keys=[...new Set(rows.flatMap(Object.keys))];const cell=v=>{let s=String(v??'');if(/^[=+@\-\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};return '\uFEFF'+[keys.map(cell).join(','),...rows.map(row=>keys.map(k=>cell(row[k])).join(','))].join('\r\n');}
function exportReport(){
  const rows=filteredRows().map(t=>{const r=reconcile(t);return {transaction_id:t.id,merchant_id:MERCHANT,customer:t.customer,payment_date:t.date,currency:'INR',captured_minor:r.captured_minor,fee_minor:r.fees_minor,expected_minor:r.expected_minor,confirmed_bank_credit_minor:r.has_bank_credit?r.credited_minor:'',status:r.status,explanation:r.explanation,exception:r.exception,next_step:r.next,as_of:AS_OF};});
  if(!rows.length){notify('No matching transactions to export. Clear the filters first.');return;}
  download('settle-report.csv',csv(rows),'text/csv;charset=utf-8');
}

renderIcons();renderMetrics();renderTable();selectTransaction(state.selected);setView('overview');
document.addEventListener('click',e=>{
  const el=e.target.closest('button,a,tr[data-id]');if(!el)return;
  if(el.matches('.brand')){e.preventDefault();setView('overview');return;}
  if(el.dataset.view){setView(el.dataset.view);return;}
  if(el.dataset.filter){state.filter=el.dataset.filter;renderTable();return;}
  if(el.dataset.trace){showTrace(el.dataset.trace);return;}
  if(el.dataset.source){showEvidence(el.dataset.source,el.dataset.transaction);return;}
  if(el.dataset.demoCase){closeDialog();setView('transactions');selectTransaction(el.dataset.demoCase,null,true);return;}
  if(el.dataset.question){ask(el.dataset.question==='breakdown'?'Show the amount breakdown.':'What should I do next?');return;}
  if(el.dataset.downloadSource){const key=el.dataset.downloadSource;download({gateway:'gateway_logs.csv',bank:'bank_settlements.csv',ledger:'ledger_entries.csv'}[key],csv(sourceRecords(key)),'text/csv;charset=utf-8');return;}
  if(el.dataset.exportCase){const t=transactions.find(t=>t.id===el.dataset.exportCase);download(`${t.id}-investigation.json`,JSON.stringify({demo:true,rule_version:'demo-1.0',...reconcile(t),evidence:{gateway:t.gateway,bank:t.bank,ledger:t.ledger}},null,2),'application/json');return;}
  if(el.id==='reset-filters'){state.filter='all';state.search='';state.date='all';$('#transaction-search').value='';$('#date-filter').value='all';renderTable();return;}
  const row=el.closest('tr[data-id]');if(row)selectTransaction(row.dataset.id,null,true);
});
$('#transaction-search').addEventListener('input',e=>{state.search=e.target.value.slice(0,100);renderTable();});
$('#date-filter').addEventListener('change',e=>{state.date=e.target.value;renderTable();});
$('#chat-form').addEventListener('submit',e=>{e.preventDefault();const value=$('#chat-input').value;$('#chat-input').value='';ask(value);});
$('#chat-input').maxLength=600;
$('#chat-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('#chat-form').requestSubmit();}});
$('#dialog-close').addEventListener('click',closeDialog);
dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeDialog();}});
$('#guide-button').addEventListener('click',showGuide);$('#help-button').addEventListener('click',showGuide);
$('#export-button').addEventListener('click',exportReport);
$('#hero-investigate').addEventListener('click',()=>{selectTransaction('TXN-1042',null,true);$('#chat-input').focus({preventScroll:true});notify('Try TXN-1041 for a successful retry, or TXN-1046 for missing evidence.');});
