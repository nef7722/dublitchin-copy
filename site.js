document.querySelectorAll('.amounts button').forEach(function(b){b.addEventListener('click',function(){document.querySelectorAll('.amounts button').forEach(function(x){x.classList.remove('on')});b.classList.add('on');});});

/* language toggle (Yiddish default, English via i18n.js) */
(function(){
  var EN=window.DUB_EN||{},YI=window.DUB_YI||{},root=document.documentElement;
  var els=[].slice.call(document.querySelectorAll('[data-i]')),alts=[].slice.call(document.querySelectorAll('[data-i-alt]'));
  els.forEach(function(e){e.setAttribute('data-yi',e.innerHTML);});
  alts.forEach(function(e){e.setAttribute('data-yi-alt',e.getAttribute('alt')||'');});
  var cur='yi';
  window.dubLang=function(){return cur;};
  window.dubT=function(k){return cur==='en'?EN[k]:YI[k];};
  function apply(l){
    cur=l==='en'?'en':'yi';var en=cur==='en';
    root.lang=en?'en':'yi';root.dir=en?'ltr':'rtl';
    els.forEach(function(e){var k=e.getAttribute('data-i');e.innerHTML=en&&EN[k]!=null?EN[k]:e.getAttribute('data-yi');});
    alts.forEach(function(e){var k=e.getAttribute('data-i-alt');e.setAttribute('alt',en&&EN[k]!=null?EN[k]:e.getAttribute('data-yi-alt'));});
    document.title=en?EN.title:YI.title;
    var b=document.getElementById('langBtn');if(b){b.setAttribute('aria-pressed',en?'true':'false');}
    try{localStorage.setItem('dub-lang',cur);}catch(e){}
    if(window.dubLbSync)window.dubLbSync();
    if(window.dubZmSync)window.dubZmSync();
    if(window.dubAfterApply)window.dubAfterApply(cur);
  }
  window.dubApply=apply;
  var saved='yi';try{saved=localStorage.getItem('dub-lang')||'yi';}catch(e){}
  apply(saved);
  var btn=document.getElementById('langBtn');
  if(btn)btn.addEventListener('click',function(){apply(cur==='en'?'yi':'en');});
})();

/* gallery lightbox */
(function(){
  var lb=document.getElementById('lb');if(!lb)return;
  var items=[].slice.call(document.querySelectorAll('.g-open')),img=document.getElementById('lbImg'),cap=document.getElementById('lbCap'),idx=0;
  var prev=lb.querySelector('.lb-prev'),next=lb.querySelector('.lb-next');
  function rtl(){return document.documentElement.dir==='rtl';}
  window.dubLbSync=function(){prev.textContent=rtl()?'›':'‹';next.textContent=rtl()?'‹':'›';if(!lb.hidden)show(idx);};
  function show(i){idx=(i+items.length)%items.length;var b=items[idx],t=b.querySelector('img'),fc=b.parentNode.querySelector('figcaption');
    img.src=b.getAttribute('data-full');img.alt=t.alt;cap.textContent=fc?fc.textContent:'';}
  function open(i){show(i);lb.hidden=false;document.body.style.overflow='hidden';}
  function close(){lb.hidden=true;document.body.style.overflow='';}
  items.forEach(function(b,i){b.addEventListener('click',function(){open(i);});});
  prev.addEventListener('click',function(e){e.stopPropagation();show(idx-1);});
  next.addEventListener('click',function(e){e.stopPropagation();show(idx+1);});
  lb.querySelector('.lb-x').addEventListener('click',close);
  lb.addEventListener('click',function(e){if(e.target===lb||e.target.classList.contains('lb-fig'))close();});
  document.addEventListener('keydown',function(e){if(lb.hidden)return;
    if(e.key==='Escape')close();
    else if(e.key==='ArrowRight')show(idx+(rtl()?-1:1));
    else if(e.key==='ArrowLeft')show(idx+(rtl()?1:-1));});
  var sx=null;
  lb.addEventListener('touchstart',function(e){sx=e.touches[0].clientX;},{passive:true});
  lb.addEventListener('touchend',function(e){if(sx==null)return;var dx=e.changedTouches[0].clientX-sx;sx=null;
    if(Math.abs(dx)>45){var fwd=dx<0;if(rtl())fwd=!fwd;show(idx+(fwd?1:-1));}});
  window.dubLbSync();
})();

/* ask-the-rebbe thank-you (FormSubmit redirects to #ask-thanks) */
(function(){
  var t=document.getElementById('ask-thanks');if(!t)return;
  function chk(){if(location.hash==='#ask-thanks'){t.hidden=false;setTimeout(function(){t.scrollIntoView({block:'center'});},60);}}
  chk();window.addEventListener('hashchange',chk);
})();
