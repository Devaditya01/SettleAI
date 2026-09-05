'use strict';
const root = document.documentElement;
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
const finePointer = window.matchMedia('(pointer: fine)');
let motionPaused=false;
if (!reduced.matches) root.classList.add('js-motion');
document.querySelectorAll('.edition').forEach(link => {
  link.addEventListener('click', () => {
    const edition = link.getAttribute('href').includes('pearl') ? 'pearl' : 'midnight';
    try { localStorage.setItem('settlelens-edition', edition); } catch (_) {}
  });
});
// No image or network request can indefinitely hold the entry transition.
setTimeout(() => root.classList.add('ready'), reduced.matches ? 0 : 80);
const nav = document.querySelector('.nav-wrap');
const hero = document.querySelector('.hero');
const visible = new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      const number = entry.target.querySelector('[data-count]');
      if (number) animateNumber(number);
      visible.unobserve(entry.target);
    }
  }
}, {threshold: .12, rootMargin: '0px 0px -18px 0px'});
document.querySelectorAll('.reveal').forEach((el, index) => {
  // Modest stagger inside a section, never accumulating over the whole page.
  if (el.closest('.number-grid')) el.style.transitionDelay = `${index % 3 * .1}s`;
  visible.observe(el);
});
function animateNumber(el) {
  const target = Number(el.dataset.count);
  if (reduced.matches) {el.textContent=String(target).padStart(2,'0');return;}
  const start=performance.now();
  function tick(now) {
    const progress=Math.min(1,(now-start)/1200);
    el.textContent=String(Math.round(target*(1-Math.pow(1-progress,3)))).padStart(2,'0');
    if(progress<1)requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
let scrollPending=false;
function onScroll() {
  if(scrollPending)return;
  scrollPending=true;
  requestAnimationFrame(()=>{
    const max=Math.max(1,document.documentElement.scrollHeight-window.innerHeight);
    root.style.setProperty('--scroll-progress',window.scrollY/max);
    nav.classList.toggle('scrolled',window.scrollY>70);
    if(!reduced.matches&&!motionPaused)root.style.setProperty('--hero-scroll',Math.min(1,window.scrollY/hero.offsetHeight));
    scrollPending=false;
  });
}
window.addEventListener('scroll',onScroll,{passive:true});window.addEventListener('resize',onScroll);onScroll();
hero.addEventListener('pointermove',event=>{
  if(reduced.matches||motionPaused||!finePointer.matches)return;
  const box=hero.getBoundingClientRect();
  root.style.setProperty('--pointer-x',(event.clientX-box.left)/box.width-.5);
  root.style.setProperty('--pointer-y',(event.clientY-box.top)/box.height-.5);
});
hero.addEventListener('pointerleave',()=>{root.style.setProperty('--pointer-x',0);root.style.setProperty('--pointer-y',0);});
document.querySelectorAll('.magnetic').forEach(el=>{
  el.addEventListener('pointermove',event=>{
    if(reduced.matches||motionPaused||!finePointer.matches)return;
    const box=el.getBoundingClientRect();
    el.style.transform=`translate(${(event.clientX-box.left-box.width/2)*.13}px,${(event.clientY-box.top-box.height/2)*.18}px)`;
  });
  el.addEventListener('pointerleave',()=>{el.style.transform='';});
});
document.querySelectorAll('.tilt').forEach(el=>{
  el.addEventListener('pointermove',event=>{
    if(reduced.matches||motionPaused||!finePointer.matches)return;
    const box=el.getBoundingClientRect(),x=(event.clientX-box.left)/box.width-.5,y=(event.clientY-box.top)/box.height-.5;
    el.style.transform=`rotateX(${-y*9}deg) rotateY(${x*15}deg) rotateZ(2deg)`;
  });
  el.addEventListener('pointerleave',()=>{el.style.transform='';});
});
const steps=[
  ['01 / GATEWAY','Confirms the payment and its settlement ID.'],
  ['02 / LEDGER','Shows the fees and the amount payable.'],
  ['03 / BANK','Checks bank credits and failed attempts. Missing outcomes stay unknown.']
];
document.querySelectorAll('.source-node').forEach(button=>{
  button.setAttribute('aria-pressed',String(button.classList.contains('active')));
  button.addEventListener('click',()=>{
    document.querySelectorAll('.source-node').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));});
    const step=steps[Number(button.dataset.step)];
    document.getElementById('trace-number').textContent=step[0];
    document.getElementById('trace-copy').textContent=step[1];
  });
});
document.querySelector('.trace-detail').setAttribute('aria-live','polite');
const menu=document.querySelector('.menu');
const mobileNav=document.querySelector('.nav-wrap nav');
function closeMenu(){menu.setAttribute('aria-expanded','false');menu.setAttribute('aria-label','Open navigation');mobileNav.classList.remove('open');}
menu.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));menu.setAttribute('aria-label',open?'Close navigation':'Open navigation');mobileNav.classList.toggle('open',open);});
mobileNav.querySelectorAll('a').forEach(a=>a.addEventListener('click',closeMenu));
window.addEventListener('keydown',e=>{if(e.key==='Escape')closeMenu();});
const modal=document.querySelector('.story-modal');
let previousFocus;
document.querySelector('.watch-story').addEventListener('click',()=>{previousFocus=document.activeElement;modal.showModal();document.querySelector('.modal-close').focus();});
function closeModal(){modal.close();previousFocus?.focus();}
document.querySelector('.modal-close').addEventListener('click',closeModal);
modal.addEventListener('click',event=>{if(event.target===modal){const box=modal.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)closeModal();}});
// Pause ambient animations when the tab is not visible.
document.addEventListener('visibilitychange',()=>{root.style.setProperty('--ambient-play',document.hidden?'paused':'running');});
const narrative=[
  ['01 / G-1042-01','The payment was captured.','The gateway confirms a ₹2,500 payment from the customer on 03 September 2026. Capture tells us the payment succeeded; it does not prove the merchant’s bank account was credited.'],
  ['02 / L-1042-01 + L-1042-02','The payable amount is ₹2,450.','The ledger records the ₹2,500 captured amount and a ₹50 fee deduction. Those entries explain the ₹2,450 expected settlement. These are synthetic sample amounts.'],
  ['03 / B-1042-01','The bank rejected the payout.','The bank record reports INVALID_BENEFICIARY for this settlement attempt. That record supports the failure explanation: the beneficiary details were invalid.'],
  ['04 / OPEN EXCEPTION','The retry is still unknown.','No subsequent attempt is present in the loaded records. The next step is to verify the beneficiary details and ask the payments team whether a retry is scheduled. A new payout date cannot be promised.']
];
const storyStatus=document.createElement('div');storyStatus.className='story-status';
const storyTitle=modal.querySelector('h2');storyTitle.id='story-title';modal.setAttribute('aria-labelledby','story-title');
storyTitle.before(storyStatus);
const storyControls=document.createElement('div');storyControls.className='story-controls';storyControls.setAttribute('role','group');storyControls.setAttribute('aria-label','Settlement trace steps');
modal.querySelector('.primary').before(storyControls);
function storyStep(index){
  const step=narrative[index];storyStatus.textContent=step[0];storyTitle.textContent=step[1];modal.querySelector('p').textContent=step[2];
  storyControls.querySelectorAll('button').forEach((b,i)=>{b.classList.toggle('active',i===index);b.setAttribute('aria-pressed',String(i===index));});
  if(!reduced.matches&&!motionPaused)storyTitle.animate([{opacity:0,transform:'translateY(7px)'},{opacity:1,transform:'translateY(0)'}],{duration:350,easing:'ease-out'});
}
narrative.forEach((_,index)=>{const b=document.createElement('button');b.textContent=String(index+1).padStart(2,'0');b.setAttribute('aria-label',`Read trace step ${index+1}`);b.addEventListener('click',()=>storyStep(index));storyControls.append(b);});
storyStep(0);
document.querySelector('.watch-story').addEventListener('click',()=>storyStep(0));

// This money-flow illustration uses the existing TXN-1041 synthetic fixture.
// Amounts are integer paise; animation never invents intermediate balances.
const moneyScene=document.querySelector('.money-scene');
const moneyVisual=document.querySelector('.money-visual');
const moneySteps=[
  {label:'PAYMENT CAPTURED',amount:849900,description:'Customer payment confirmed by the gateway.',status:'01 / Gateway record verified',symbol:'↗',bank:'Awaiting credit'},
  {label:'NET PAYABLE',amount:832902,description:'₹8,499.00 captured − ₹169.98 recorded fee.',status:'02 / Ledger amount explained',symbol:'=',bank:'₹8,329.02 expected'},
  {label:'SETTLEMENT CREDITED',amount:832902,description:'Successful retry confirmed by the bank record.',status:'03 / Bank and ledger matched',symbol:'✓',bank:'₹8,329.02 credited'}
];
let currentMoneyStep=0;
let lastMoneyChange=performance.now();
function showMoneyStep(index){
  currentMoneyStep=index;lastMoneyChange=performance.now();
  const step=moneySteps[index];moneyScene.dataset.moneyPhase=String(index);
  const amount=(step.amount/100).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
  const [whole,fraction]=amount.split('.');
  document.getElementById('money-label').textContent=step.label;
  document.getElementById('money-amount').innerHTML=`₹${whole}<span>.${fraction}</span>`;
  document.getElementById('money-description').textContent=step.description;
  document.getElementById('money-status').textContent=step.status;
  document.getElementById('money-symbol').textContent=step.symbol;
  document.getElementById('bank-result').textContent=step.bank;
  document.getElementById('bank-symbol').textContent=index===2?'✓':'↗';
  document.querySelectorAll('[data-money-stage]').forEach((button,i)=>{button.classList.toggle('active',i===index);button.setAttribute('aria-pressed',String(i===index));});
  if(!reduced.matches&&!motionPaused)document.getElementById('money-amount').animate([{opacity:.2,transform:'translateY(5px)'},{opacity:1,transform:'translateY(0)'}],{duration:400,easing:'ease-out'});
}
document.querySelectorAll('[data-money-stage]').forEach(button=>button.addEventListener('click',()=>showMoneyStep(Number(button.dataset.moneyStage))));
const resizeMoneyScene=()=>moneyVisual.style.setProperty('--scene-scale',moneyVisual.clientWidth/600);
new ResizeObserver(resizeMoneyScene).observe(moneyVisual);resizeMoneyScene();
setInterval(()=>{
  if(reduced.matches||motionPaused||document.hidden||performance.now()-lastMoneyChange<4500)return;
  const bounds=moneyVisual.getBoundingClientRect();
  if(bounds.bottom>0&&bounds.top<innerHeight)showMoneyStep((currentMoneyStep+1)%moneySteps.length);
},500);
