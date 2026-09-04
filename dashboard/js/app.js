'use strict';

// CSV-backed settlement records are loaded from data/real-data.js.
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
const money = window.SettleEngine.money;
const shortMoney = minor => minor >= 10000000 ? `₹${(minor/10000000).toFixed(1)}L` : minor >= 100000 ? `₹${(minor/100000).toFixed(1)}k` : money(minor);
const dateLabel = date => new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'Asia/Kolkata'}).format(new Date(date+'T12:00:00+05:30'));
const timeLabel = date => new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Kolkata'}).format(new Date(date));
const DATASET = window.SettleRealData;
if (!DATASET || !window.SettleEngine) throw new Error('Settlement data or reconciliation engine failed to load.');
const MERCHANT = DATASET.merchant_id;
const MERCHANT_NAME = DATASET.merchant_name || 'Imported Records';
const AS_OF = DATASET.as_of;
const STATUS_LABEL = {settled:'Settled',pending:'Pending',failed:'Failed',review:'Needs review'};
const sourceTypes = ['gateway','bank','ledger'];
const sourceIndex = Object.fromEntries(sourceTypes.map(type=>[type,new Map()]));
for (const type of sourceTypes) {
  for (const row of DATASET.sources[type] || []) {
    const bucket = sourceIndex[type].get(row.transaction_id) || [];
    bucket.push(row);
    sourceIndex[type].set(row.transaction_id,bucket);
  }
}
const recordsFor = (type,id) => sourceIndex[type].get(id) || [];
const transactions = DATASET.transactions.map(meta=>({
  ...meta,
  id:meta.transaction_id,
  settlementId:meta.settlement_id,
  amount:meta.captured_minor,
  date:meta.payment_date,
  gateway:recordsFor('gateway',meta.transaction_id),
  bank:recordsFor('bank',meta.transaction_id),
  ledger:recordsFor('ledger',meta.transaction_id)
}));
const state = {view:'overview',filter:'all',search:'',date:'all',selected: transactions.length > 0 ? transactions[0].id : null};
const sourceRecords = type => DATASET.sources[type] || [];
const statusBadge = status => {const safe=Object.hasOwn(STATUS_LABEL,status)?status:'review';return `<span class="status ${safe}">${STATUS_LABEL[safe]}</span>`;};
const reconcile = transaction => window.SettleEngine.reconcile(transaction,{asOf:AS_OF});
const getSelected = () => transactions.find(t=>t.id===state.selected);
const compactId = value => String(value).toUpperCase().replace(/[\s-]/g,'');
const normalizeTransactionId = value => transactions.find(t=>compactId(t.id)===compactId(value))?.id || String(value).toUpperCase();
function initials(value){
  const parts=String(value||'').replace(/@.*/,'').split(/[\s._-]+/).filter(Boolean);
  if(parts.length>=2)return (parts[0][0]+parts[parts.length-1][0]).toUpperCase();
  return (parts[0] || 'U').slice(0,2).toUpperCase();
}
function dateRangeText(){
  const days=[...new Set(transactions.map(t=>t.date).filter(Boolean))].sort();
  if(!days.length)return 'No dated records';
  const start=dateLabel(days[0]).replace(/ 2026$/,'');
  const end=dateLabel(days.at(-1)).replace(/ 2026$/,'');
  return start===end?start:`${start} - ${end}`;
}
function renderDateOptions(){
  const select=$('#date-filter');
  const days=[...new Set(transactions.map(t=>t.date).filter(Boolean))].sort().reverse();
  select.innerHTML='<option value="all">All dates</option>'+days.map(day=>`<option value="${escapeHTML(day)}">${escapeHTML(dateLabel(day))}</option>`).join('');
}
function renderDatasetChrome(){
  $('#workspace-name').textContent=MERCHANT_NAME;
  $('#workspace-logo').textContent=initials(MERCHANT_NAME);
  $('#date-range-label').textContent=dateRangeText();
  const sample=transactions.find(t=>reconcile(t).has_bank_credit) || transactions[0];
  if(!sample)return;
  const result=reconcile(sample);
  $('#hero-gateway-amount').textContent=money(result.captured_minor);
  $('#hero-gateway-meta').textContent=`${sample.id} · fee ${money(result.fees_minor)}`;
  $('#hero-bank-amount').textContent=result.has_bank_credit?money(result.credited_minor):'Not confirmed';
  $('#hero-bank-meta').innerHTML=`<i>${result.has_bank_credit?'✓':'?'}</i>${escapeHTML(result.title)}`;
}
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
  const failed=attention.filter(t=>reconcile(t).status==='failed').length;
  const review=attention.length-failed;
  const metrics=[
    {label:'Settled',value:shortMoney(settled.reduce((s,t)=>s+reconcile(t).credited_minor,0)),note:`${settled.length} transactions matched`,icon:'bank',color:'#81b5a0',points:'0,23 8,18 15,20 24,11 31,14 40,7 49,11 58,2'},
    {label:'Pending',value:shortMoney(pending.reduce((s,t)=>s+reconcile(t).expected_minor,0)),note:`${pending.length} payouts scheduled`,icon:'clock',color:'#c8ad7c',points:'0,22 10,18 20,18 28,11 40,11 48,7 58,7'},
    {label:'Needs attention',value:String(attention.length).padStart(2,'0'),note:`${failed} failed · ${review} to review`,icon:'alert',color:'#cba0b1',points:'0,20 10,16 21,19 30,9 41,9 48,4 58,4'}
  ];
  $('#metrics').innerHTML=metrics.map(m=>`<article class="metric"><div class="metric-label">${m.label}<span class="metric-icon">${icon(m.icon)}</span></div><strong>${m.value}</strong><div class="metric-bottom"><i></i>${m.note}</div><svg class="metric-sparkline" viewBox="0 0 60 28" aria-hidden="true"><polyline points="${m.points}" fill="none" stroke="${m.color}" stroke-width="1.5"/></svg></article>`).join('');
  $('#nav-exceptions').textContent=attention.length;
  const credited=transactions.filter(t=>reconcile(t).has_bank_credit);
  const mismatch=transactions.filter(t=>reconcile(t).reason_code==='AMOUNT_MISMATCH').length;
  $('#flow-total').textContent=money(credited.reduce((s,t)=>s+reconcile(t).credited_minor,0));
  $('#flow-count').textContent=`${credited.length} credits${mismatch?` · includes ${mismatch} amount mismatch${mismatch===1?'':'es'}`:''}`;
  const days=[...new Set(transactions.map(t=>t.date))].sort();
  const values=days.map(d=>sourceRecords('bank').filter(r=>r.status==='credited'&&r.occurred_at.startsWith(d)).reduce((s,r)=>s+r.amount_minor,0));
  const max=Math.max(1,...values);
  $('#chart').innerHTML=days.map((d,i)=>`<div class="chart-column" title="${dateLabel(d)}: ${money(values[i])}"><span class="chart-value">${shortMoney(values[i])}</span><div class="chart-bar" style="height:${Math.round(values[i]/max*55)}px"></div><span class="chart-date">${dateLabel(d).replace(/ 2026$/,'')}</span></div>`).join('');
  $('#chart').setAttribute('aria-label',days.map((d,i)=>`${dateLabel(d)}: ${money(values[i])}`).join('; '));
}
function renderTable(){
  const rows=filteredRows();
  $('#transaction-count').textContent=rows.length;
  $('#transaction-rows').innerHTML=rows.length?rows.map(t=>`<tr data-id="${escapeHTML(t.id)}" class="${state.selected===t.id?'selected':''}"><td><button class="transaction-id" aria-label="Investigate ${escapeHTML(t.id)}">${escapeHTML(t.id)}</button><span class="customer-name">${escapeHTML(t.customer)}</span></td><td class="amount-cell">${money(t.amount)}</td><td>${statusBadge(reconcile(t).status)}</td><td class="date-cell">${dateLabel(t.date)}</td><td>${icon('chevron')}</td></tr>`).join(''):`<tr><td class="empty-state" colspan="5"><strong>No matching transactions</strong><p>Try another ID, customer, date, or status.</p><button class="button button-outline" id="reset-filters">Clear filters</button></td></tr>`;
  $('#table-summary').textContent=`Showing ${rows.length} of ${transactions.length} loaded transactions`;
  $$('.tab').forEach(b=>{b.classList.toggle('active',b.dataset.filter===state.filter);b.setAttribute('aria-pressed',String(b.dataset.filter===state.filter));});
}
function timeline(t){
  const result=reconcile(t);
  const capture=t.gateway.find(r=>r.event_type==='payment_captured');
  const events=capture?[{at:capture.occurred_at,title:'Payment captured',detail:`${money(t.amount)} · ${capture.source_record_id}`,kind:'settled',icon:'check'}]:[];
  const fee=t.ledger.find(r=>r.event_type==='fee_deduction');
  if(fee)events.push({at:fee.occurred_at,title:'Merchant payable recorded',detail:`${money(result.expected_minor)} after fees · ${fee.source_record_id}`,kind:'settled',icon:'check'});
  t.gateway.filter(r=>r.event_type==='settlement_initiated').forEach((r,index)=>events.push({at:r.occurred_at,title:index?'Retry initiated':'Settlement initiated',detail:r.attempt_id,kind:'settled',icon:'check'}));
  t.gateway.filter(r=>r.event_type==='settlement_scheduled').forEach(r=>events.push({at:r.occurred_at,title:'Future payout scheduled',detail:`${timeLabel(r.scheduled_for)} IST · ${r.source_record_id}`,kind:'pending',icon:'clock'}));
  t.bank.forEach(r=>events.push({at:r.occurred_at,title:r.status==='credited'?'Bank credit confirmed':'Bank rejected attempt',detail:r.status==='credited'?`${money(r.amount_minor)} · ${r.source_record_id}`:`${String(r.reason_code||'unmapped reason').replaceAll('_',' ').toLowerCase()} · ${r.source_record_id}`,kind:r.status==='credited'?'settled':'failed',icon:r.status==='credited'?'check':'close'}));
  const sorted=events.sort((a,b)=>new Date(a.at)-new Date(b.at));
  if(result.reason_code==='BANK_OUTCOME_MISSING')sorted.push({at:AS_OF,title:'Bank outcome unavailable',detail:'Unknown as of this snapshot',kind:'review',icon:'help'});
  return sorted;
}
function renderTimeline(t,full=false){
  let events=timeline(t);
  if(!full&&events.length>4)events=[events[0],events[1],...events.slice(-2)];
  return events.map(e=>`<div class="timeline-step"><span class="timeline-step-icon ${e.kind}">${icon(e.icon)}</span><div><strong>${escapeHTML(e.title)}</strong><small>${full?`${timeLabel(e.at)} IST · `:''}${escapeHTML(e.detail)}</small></div></div>`).join('');
}
function evidenceChips(t){return ['gateway','bank','ledger'].map(type=>`<button class="evidence-chip" data-source="${type}" data-transaction="${escapeHTML(t.id)}">${icon(type==='gateway'?'card':type==='bank'?'bank':'ledger')}${type[0].toUpperCase()+type.slice(1)} <span>${t[type].length?'↗':'· missing'}</span></button>`).join('');}
function selectTransaction(id,question,scroll=false){
  const t=transactions.find(t=>t.id===id);if(!t)return;
  state.selected=id;const r=reconcile(t);
  const defaultQuestion=r.status==='settled'?`Has ${id} settled successfully?`:r.status==='pending'?`When will ${id} settle?`:r.status==='failed'?`Why hasn’t ${id} settled?`:`What happened to ${id}?`;
  $('#investigation-content').innerHTML=`<div class="query-bubble">${escapeHTML(question||defaultQuestion)}<small>${escapeHTML(MERCHANT_NAME)} · ${escapeHTML(id)}</small></div><div class="response-label">${icon('sparkles')}Settle copilot<span>Verified rules</span></div>${statusBadge(r.status)}<div class="finding-meta"><span>${escapeHTML(r.reason_code)}</span><span>${escapeHTML(r.certainty)}</span></div><h3 class="answer-title">${escapeHTML(r.title)}</h3><p class="answer-description">${escapeHTML(r.explanation)}</p><div class="evidence-chips">${evidenceChips(t)}</div><div class="mini-timeline">${renderTimeline(t)}</div><div class="exception-box ${r.exception?'':'no-exception'}"><div class="exception-box-title">${icon(r.exception?'alert':'shield')}${r.exception?'What we can’t confirm':'The records agree'}</div><p>${escapeHTML(r.exception||'No exceptions detected in the loaded gateway, bank, and ledger records.')}</p></div><p class="next-step"><strong>Next step</strong><br>${escapeHTML(r.next)}</p><button class="trace-button" data-trace="${escapeHTML(t.id)}">View full investigation ${icon('arrow-up-right')}</button><div id="followups"></div>`;
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
  openDialog(`${t.id} · Full investigation`,`<div class="detail-summary"><p>${escapeHTML(t.customer)} · ${escapeHTML(MERCHANT_NAME)}<br>Snapshot: ${escapeHTML(timeLabel(AS_OF))} IST</p>${statusBadge(r.status)}</div><div class="finding-meta"><span>${escapeHTML(r.reason_code)}</span><span>${escapeHTML(r.certainty)}</span></div><h3 class="answer-title">${escapeHTML(r.title)}</h3><p class="detail-description">${escapeHTML(r.explanation)}</p><div class="detail-grid"><div><h3 class="detail-heading">The complete timeline</h3><div class="detail-timeline">${renderTimeline(t,true)}</div></div><div><h3 class="detail-heading">Follow the money</h3>${breakdownHTML(t)}<p class="guide-notice">The payable amount is calculated from the loaded records for this transaction.</p></div></div><div class="exception-box ${r.exception?'':'no-exception'}"><div class="exception-box-title">${icon(r.exception?'alert':'check')}${r.exception?'Open exception':'No exceptions detected'}</div><p>${escapeHTML(r.exception||'All loaded records reconcile for this transaction.')}</p></div><p class="next-step"><strong>Recommended next step</strong><br>${escapeHTML(r.next)}</p><h3 class="detail-heading">Inspect the evidence</h3><div class="evidence-list">${evidenceChips(t)}</div><button class="button button-outline" style="margin-top:20px" data-export-case="${escapeHTML(id)}">${icon('download')}Export investigation JSON</button>`);
}
function showEvidence(type,id){
  const t=transactions.find(t=>t.id===id),records=t[type];
  openDialog(`${type[0].toUpperCase()+type.slice(1)} evidence · ${id}`,`<p class="detail-description">${records.length?`${records.length} loaded record${records.length===1?'':'s'} from this transaction.`:'No matching bank records are available. Absence of a record does not establish payment failure.'} All timestamps include the +05:30 timezone offset.</p><pre class="record-json">${escapeHTML(JSON.stringify(records.length?records:{transaction_id:id,source:type,records:[],finding:'Bank outcome unknown',source_snapshot:AS_OF},null,2))}</pre><button class="button button-outline" data-trace="${id}">${icon('arrow-right')}Back to full investigation</button>`,'SOURCE EVIDENCE');
}
function showGuide(){
  const examples=transactions.slice(0,4).map(t=>`<button data-demo-case="${escapeHTML(t.id)}">${escapeHTML(t.id)} ↗</button>`).join('');
  openDialog('Meet your settlement copilot.',`<p class="guide-intro">One place to answer the question that keeps coming back: <strong>“Where is my settlement?”</strong></p><div class="guide-step"><span class="guide-number">1</span><div><strong>Find a payment</strong><p>Search a real transaction ID, filter by payment date, or open the exceptions queue.</p></div></div><div class="guide-step"><span class="guide-number">2</span><div><strong>Connect the evidence</strong><p>Select a transaction to inspect its gateway, bank, and ledger records.</p></div></div><div class="guide-step"><span class="guide-number">3</span><div><strong>Know what’s known</strong><p>Read the confirmed outcome, inspect any uncertainty, and export a case summary for support.</p></div></div><div class="guide-scenarios">${examples}</div><p class="guide-notice"><strong>Loaded scope:</strong> ${transactions.length} transactions across ${sourceTypes.length} source systems. Responses use deterministic reconciliation rules over the loaded records.</p>`,'A QUICK TOUR');
}
function renderSources(){
  const sources=[{key:'gateway',title:'Payment gateway',file:'gateway_logs.csv',icon:'card',description:'Captured payments, scheduled settlements, and payout initiation events.'},{key:'bank',title:'Bank settlements',file:'bank_settlements.csv',icon:'bank',description:'Recorded credit outcomes and failed payout attempts. Missing outcomes remain unknown.'},{key:'ledger',title:'Merchant ledger',file:'ledger_entries.csv',icon:'ledger',description:'Captured receivables, recorded fee deductions, and settlement postings.'}];
  $('#source-view').innerHTML=`<p class="source-intro">The same transaction IDs connect three independent views of a payment. Inspect or download the loaded records behind every answer.</p>${sources.map(s=>`<article class="card source-card"><div class="source-card-header"><span class="source-card-icon">${icon(s.icon)}</span><div><h2>${s.title}</h2><p>${s.file}</p></div><span class="source-pill">Loaded</span></div><p class="source-intro">${s.description}</p><div class="source-meta"><div><strong>${sourceRecords(s.key).length}</strong>source records</div><div><strong>${escapeHTML(timeLabel(AS_OF))}</strong>snapshot · IST</div><div><strong>${transactions.length}</strong>transactions</div></div><button class="button button-outline" data-download-source="${s.key}">${icon('download')}Download CSV</button></article>`).join('')}<p class="source-footnote">These records are compiled from the local gateway, bank, and ledger CSV files.</p>`;
}
function setSidebarActive(view){
  $$('.nav-item').forEach(b=>{
    b.classList.toggle('active',b.dataset.view===view);
    if(b.dataset.view===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');
  });
}
let scrollNavPending=false;
function updateOverviewScrollNav(){
  scrollNavPending=false;
  if(state.view!=='overview')return;
  const transactionCard=$('#transaction-card');
  if(!transactionCard||transactionCard.hidden)return;
  const triggerLine=window.innerHeight*0.42;
  setSidebarActive(transactionCard.getBoundingClientRect().top<=triggerLine?'transactions':'overview');
}
function scheduleOverviewScrollNav(){
  if(scrollNavPending)return;
  scrollNavPending=true;
  requestAnimationFrame(updateOverviewScrollNav);
}
function setView(view){
  state.view=view;state.filter='all';state.search='';state.date='all';$('#transaction-search').value='';$('#date-filter').value='all';
  const info={overview:['Overview','Overview','A little less chasing. A lot more clarity.'],transactions:['Transactions','Transactions','Follow a payment from capture to bank credit.'],exceptions:['Exceptions','Exceptions','Failed attempts and records that need verification.'],sources:['Data sources','Data sources','Three sources. One connected view of your payments.']}[view];
  $('#breadcrumb-current').textContent=info[0];$('#page-title').textContent=info[1];$('#page-subtitle').textContent=info[2];
  setSidebarActive(view);
  $('#hero').hidden=view!=='overview';$('#flow-card').hidden=view!=='overview';$('#metrics').hidden=view==='sources';$('#transaction-card').hidden=view==='sources';$('#source-view').hidden=view!=='sources';$('.tabs').hidden=view==='exceptions';$('#table-title').textContent=view==='exceptions'?'Exception queue':'Transactions';
  $('#export-button').hidden=view==='sources';renderTable();if(view==='sources')renderSources();updateOverviewScrollNav();
}
function appendFollowup(question,answer){
  const content=document.createElement('div');content.className='followup-response';content.innerHTML=`<div class="query-bubble">${escapeHTML(question)}</div><div class="response-label">${icon('sparkles')}Settle copilot<span>Local evidence</span></div>${answer}`;$('#followups').append(content);const body=$('#copilot-body');body.scrollTop=body.scrollHeight;
}
function ask(question){
  question=question.trim().slice(0,600);if(!question)return;
  const matches=question.match(/\bTXN[-\s]?\d+\b/gi)||[];
  const ids=[...new Set(matches.map(normalizeTransactionId))];
  if(ids.length>1){appendFollowup(question,'<p>This workspace investigates one transaction at a time. Select one transaction ID, or use the transaction list to compare statuses.</p>');return;}
  if(ids.length&&!transactions.some(t=>t.id===ids[0])){appendFollowup(question,`<p>No matching record for <strong>${escapeHTML(ids[0])}</strong> in ${escapeHTML(MERCHANT_NAME)} records. This does not establish whether the transaction exists elsewhere.</p>`);return;}
  const t=ids.length?transactions.find(t=>t.id===ids[0]):getSelected();
  if(ids.length&&t.id!==state.selected)selectTransaction(t.id,question);
  const r=reconcile(t), q=question.toLowerCase();
  if(/breakdown|deduct|fee|amount|how much/.test(q))appendFollowup(question,`<p>Here is the recorded breakdown for <strong>${t.id}</strong>.</p><div class="mini-breakdown">${breakdownHTML(t)}</div><div class="evidence-chips">${evidenceChips(t)}</div>`);
  else if(/next|should|action|retry|fix/.test(q))appendFollowup(question,`<p>${escapeHTML(r.next)}</p><p>${escapeHTML(r.exception||'No open exception was detected in the loaded records.')}</p>`);
  else if(/missing|exception|uncertain|sure|confiden/.test(q))appendFollowup(question,`<p><strong>${escapeHTML(r.certainty)}.</strong> ${escapeHTML(r.exception||'The credited amount, expected payable, and ledger posting agree in the loaded records.')}</p><div class="evidence-chips">${evidenceChips(t)}</div>`);
  else if(ids.length||/status|why|settle|credit|payout|trace|happened/.test(q))selectTransaction(t.id,question);
  else appendFollowup(question,`<p>This workspace can explain the status, amount breakdown, next step, and missing evidence for <strong>${t.id}</strong>. Try “What’s the status?” or enter another transaction ID.</p>`);
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

renderIcons();renderDateOptions();renderDatasetChrome();renderMetrics();renderTable();selectTransaction(state.selected);setView('overview');
window.addEventListener('scroll',scheduleOverviewScrollNav,{passive:true});
window.addEventListener('resize',scheduleOverviewScrollNav);
updateOverviewScrollNav();
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
  if(el.dataset.exportCase){const t=transactions.find(t=>t.id===el.dataset.exportCase);download(`${t.id}-investigation.json`,JSON.stringify({rule_version:'csv-rules-1.0',...reconcile(t),evidence:{gateway:t.gateway,bank:t.bank,ledger:t.ledger}},null,2),'application/json');return;}
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
$('#hero-investigate').addEventListener('click',()=>{selectTransaction(transactions[0].id,null,true);$('#chat-input').focus({preventScroll:true});});

// --- Supabase User Profile Sync ---
(async () => {
  const isDemoMode = !window.SETTLE_CONFIG?.SUPABASE_URL || window.SETTLE_CONFIG.SUPABASE_URL === 'YOUR_SUPABASE_URL';
  
  const logoutBtn = $('#logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      if (!isDemoMode && window.supabase) {
        const client = window.supabase.createClient(window.SETTLE_CONFIG.SUPABASE_URL, window.SETTLE_CONFIG.SUPABASE_ANON_KEY);
        await client.auth.signOut();
      }
      window.location.replace('/login.html');
    });
  }

  if (isDemoMode || !window.supabase) return;

  const client = window.supabase.createClient(
    window.SETTLE_CONFIG.SUPABASE_URL,
    window.SETTLE_CONFIG.SUPABASE_ANON_KEY
  );

  const { data: { session } } = await client.auth.getSession();
  if (session && session.user) {
    const user = session.user;
    const displayName = user.user_metadata?.full_name || user.user_metadata?.name || user.email || 'Signed in user';
    const roleLabel = user.email || 'Authenticated account';
    const nameEl = $('#user-name');
    const roleEl = $('#user-role');
    const avatarEl = $('#user-avatar');

    if (nameEl) nameEl.textContent = displayName;
    if (roleEl) roleEl.textContent = roleLabel;
    if (avatarEl) avatarEl.textContent = initials(displayName);
  }
})();
