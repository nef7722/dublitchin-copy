/* Dublitchin admin mode: saved text overrides + on-page editing */
(function(){
  var d=document,root=d.documentElement,EN=window.DUB_EN||(window.DUB_EN={}),YI=window.DUB_YI||(window.DUB_YI={});
  var m=d.querySelector('meta[name="dub-api"]');
  var API=/\.sites\.tab\.bot$/.test(location.hostname)?location.origin:(m&&m.content)||'https://dublitchin.sites.tab.bot';
  var LS_C='dub-ov:'+API,LS_K='dub-admin';
  function ls(k,v){try{if(v===undefined)return localStorage.getItem(k);if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v);}catch(e){}}
  function lang(){return window.dubLang?window.dubLang():'yi';}
  function reveal(){root.classList.remove('dub-ld');}

  /* ---- sanitizer: plain text + a few safe tags ---- */
  var OK={BR:1,B:1,I:1,SMALL:1,STRONG:1,EM:1,SPAN:1,BDI:1,A:1},DROP={SCRIPT:1,STYLE:1,IFRAME:1,OBJECT:1,EMBED:1,svg:1,SVG:1,MATH:1,TEMPLATE:1,IMG:1,VIDEO:1,AUDIO:1,LINK:1,META:1,FORM:1,INPUT:1,TEXTAREA:1,SELECT:1,BUTTON:1};
  function clean(html){
    var t=d.createElement('template');t.innerHTML=String(html==null?'':html);
    (function walk(n){[].slice.call(n.childNodes).forEach(function(c){
      if(c.nodeType===3)return;
      if(c.nodeType!==1){n.removeChild(c);return;}
      var tag=c.tagName;
      if(DROP[tag]){n.removeChild(c);return;}
      walk(c);
      if(tag==='DIV'||tag==='P'||tag==='LI'){
        var f=d.createDocumentFragment();if(c.previousSibling&&!(c.previousSibling.nodeType===1&&c.previousSibling.tagName==='BR'))f.appendChild(d.createElement('br'));
        while(c.firstChild)f.appendChild(c.firstChild);n.replaceChild(f,c);return;}
      if(!OK[tag]){var g=d.createDocumentFragment();while(c.firstChild)g.appendChild(c.firstChild);n.replaceChild(g,c);return;}
      [].slice.call(c.attributes).forEach(function(a){var k=a.name.toLowerCase(),v=a.value.trim();
        var keep=k==='dir'||(k==='class'&&tag==='SPAN'&&/^[\w -]{0,40}$/.test(v))||(tag==='A'&&k==='href'&&/^(https?:|mailto:|tel:|#)/i.test(v))||(tag==='A'&&k==='target'&&v==='_blank')||(tag==='A'&&k==='rel');
        if(!keep)c.removeAttribute(a.name);});
    });})(t.content);
    var x=d.createElement('div');x.appendChild(t.content);
    return x.innerHTML.replace(/\u00a0|&nbsp;/g,' ').replace(/(<br>\s*)+$/,'').replace(/^\s+|\s+$/g,'');
  }
  window.dubClean=clean;

  /* ---- defaults (as shipped in the page) and overrides ---- */
  var els=[].slice.call(d.querySelectorAll('[data-i]')),DEF={},ov={};
  els.forEach(function(e){var k=e.getAttribute('data-i');if(!DEF[k])DEF[k]={yi:e.getAttribute('data-yi')!=null?e.getAttribute('data-yi'):e.innerHTML,en:EN[k],yd:YI[k]};});
  function eff(k,l){var o=ov[k];if(o&&o[l]!=null)return o[l];var df=DEF[k]||{};return l==='en'?(df.en!=null?df.en:df.yi):df.yi;}
  function applyAll(map){
    ov=map||{};
    Object.keys(DEF).forEach(function(k){var o=ov[k]||{},df=DEF[k];
      var yi=o.yi!=null?clean(o.yi):df.yi;
      d.querySelectorAll('[data-i="'+k+'"]').forEach(function(e){e.setAttribute('data-yi',yi);});
      if(o.en!=null)EN[k]=clean(o.en);else if(df.en!=null)EN[k]=df.en;else delete EN[k];
      if(df.yd!=null)YI[k]=o.yi!=null?clean(o.yi).replace(/<[^>]+>/g,''):df.yd;
    });
    if(window.dubApply)window.dubApply(lang());
  }
  function load(){
    var cached=ls(LS_C),had=false;
    if(cached){try{applyAll(JSON.parse(cached));had=true;}catch(e){}}
    if(had)reveal();
    if(!window.fetch){reveal();return;}
    var ctl=window.AbortController?new AbortController():null,tm=setTimeout(function(){if(ctl)ctl.abort();reveal();},4000);
    fetch(API+'/api/content',{cache:'no-store',signal:ctl?ctl.signal:undefined}).then(function(r){if(!r.ok)throw 0;return r.json();})
      .then(function(j){clearTimeout(tm);var s=JSON.stringify(j||{});
        if(s!==cached&&!editing){applyAll(j||{});}else if(s!==cached){ov=j||{};}
        ls(LS_C,s);reveal();})
      .catch(function(){clearTimeout(tm);reveal();});
  }

  /* ---- admin UI ---- */
  var L={
    yi:{t:'אדמין',p:'לייגט אריין אייער קאד',go:'אריין',back:'צוריק',bad:'פאלשער קאד',many:'צופיל פרואוון. פרובירט שפעטער.',net:'קיין פארבינדונג. פרובירט נאכאמאל.',
        save:'היטן',cancel:'אפזאגן',out:'ארויס',ed:'איר טוישט: ייִדיש',hint:'טאפט אויף א טעקסט צו טוישן',saved:'געהיט ✅',none:'קיין ענדערונגען',err:'נישט געהיט, פרובירט נאכאמאל',lose:'ענדערונגען וועלן פארלוירן גיין. ווייטער?'},
    en:{t:'Admin',p:'Enter your code',go:'Enter',back:'Back',bad:'Wrong code',many:'Too many tries. Try again later.',net:'No connection. Try again.',
        save:'Save',cancel:'Cancel',out:'Log out',ed:'Editing: English',hint:'Tap any text to change it',saved:'Saved ✅',none:'No changes',err:'Not saved, try again',lose:'Unsaved changes will be lost. Continue?'}};
  function S(k){return (L[lang()]||L.yi)[k];}
  var editing=false,pending={},bar,modal,toastEl;
  function post(path,body){
    return fetch(API+path,{method:'POST',headers:{'Content-Type':'text/plain;charset=UTF-8'},body:JSON.stringify(body),cache:'no-store'})
      .then(function(r){return r.json().catch(function(){return {};}).then(function(j){j.status=r.status;return j;});});
  }
  function toast(msg){
    if(!toastEl){toastEl=d.createElement('div');toastEl.className='adm-toast';toastEl.setAttribute('role','status');d.body.appendChild(toastEl);}
    toastEl.textContent=msg;toastEl.classList.add('on');clearTimeout(toastEl._t);toastEl._t=setTimeout(function(){toastEl.classList.remove('on');},2200);
  }
  function el(tag,cls,txt){var e=d.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e;}

  function openLogin(){
    var saved=ls(LS_K);
    if(saved){enterEdit();post('/api/check',{code:saved}).then(function(j){if(!j.ok&&j.status===401){ls(LS_K,null);exitEdit(true);openLogin();}}).catch(function(){});return;}
    if(!modal){
      modal=el('div','adm-modal');modal.setAttribute('role','dialog');modal.setAttribute('aria-modal','true');
      var box=el('form','adm-box');box.setAttribute('novalidate','');
      var h=el('h3','adm-h'),lab=el('label','adm-lab'),inp=el('input','adm-in'),msg=el('p','adm-msg'),row=el('div','adm-row'),go=el('button','adm-btn gold'),bk=el('button','adm-btn ghost');
      inp.type='text';inp.setAttribute('inputmode','numeric');inp.setAttribute('pattern','[0-9]*');inp.setAttribute('autocomplete','one-time-code');inp.setAttribute('autocapitalize','off');inp.setAttribute('autocorrect','off');inp.setAttribute('spellcheck','false');inp.maxLength=32;inp.dir='ltr';inp.id='admCode';
      go.type='submit';bk.type='button';lab.htmlFor='admCode';
      box.appendChild(el('div','adm-lock','🔒'));box.appendChild(h);box.appendChild(lab);box.appendChild(inp);box.appendChild(msg);row.appendChild(go);row.appendChild(bk);box.appendChild(row);modal.appendChild(box);d.body.appendChild(modal);
      modal._t=function(){h.textContent=S('t');lab.textContent=S('p');go.textContent=S('go');bk.textContent=S('back');box.dir=lang()==='en'?'ltr':'rtl';};
      bk.addEventListener('click',closeLogin);
      inp.addEventListener('input',function(){msg.textContent='';});
      modal.addEventListener('click',function(e){if(e.target===modal)closeLogin();});
      box.addEventListener('submit',function(e){e.preventDefault();var c=inp.value.trim();if(!c)return;go.disabled=true;msg.textContent='';
        post('/api/check',{code:c}).then(function(j){go.disabled=false;
          if(j.ok){ls(LS_K,c);inp.value='';closeLogin();enterEdit();}
          else{msg.textContent=j.status===429?S('many'):S('bad');inp.select();modal.querySelector('.adm-box').classList.remove('shake');void box.offsetWidth;box.classList.add('shake');}
        }).catch(function(){go.disabled=false;msg.textContent=S('net');});});
      modal._inp=inp;modal._msg=msg;
    }
    modal._t();modal._msg.textContent='';modal.classList.add('on');
    setTimeout(function(){modal._inp.focus();},60);
  }
  function closeLogin(){if(modal){modal.classList.remove('on');modal._inp.blur();}if(location.hash==='#admin')history.replaceState(null,'',location.pathname+location.search);}

  function editable(e){return !e.closest('.adm-bar,.adm-modal');}
  function count(){return Object.keys(pending).reduce(function(n,k){return n+Object.keys(pending[k]).length;},0);}
  function paintBar(){
    if(!bar)return;var n=count();
    bar._ed.textContent=S('ed');bar._hint.textContent=n?('✎ '+n):S('hint');
    bar._save.textContent=S('save')+(n?' ('+n+')':'');bar._cancel.textContent=S('cancel');bar._out.textContent=S('out');
    bar._save.disabled=!n;bar._cancel.disabled=!n;bar.dir=lang()==='en'?'ltr':'rtl';
  }
  function makeBar(){
    bar=el('div','adm-bar');bar.setAttribute('role','toolbar');
    var info=el('div','adm-info');bar._ed=el('b','adm-ed');bar._hint=el('span','adm-hint');info.appendChild(bar._ed);info.appendChild(bar._hint);
    var btns=el('div','adm-btns');
    bar._save=el('button','adm-btn gold');bar._cancel=el('button','adm-btn ghost');bar._out=el('button','adm-btn ghost');
    [bar._save,bar._cancel,bar._out].forEach(function(b){b.type='button';btns.appendChild(b);});
    bar.appendChild(info);bar.appendChild(btns);d.body.appendChild(bar);
    bar._save.addEventListener('click',save);
    bar._cancel.addEventListener('click',function(){pending={};applyAll(ov);paintBar();});
    bar._out.addEventListener('click',function(){if(count()&&!confirm(S('lose')))return;ls(LS_K,null);exitEdit();});
    bar.addEventListener('mousedown',function(e){if(e.target.tagName==='BUTTON')e.preventDefault();});
  }
  function enterEdit(){
    if(editing)return;editing=true;if(!bar)makeBar();
    root.classList.add('dub-edit');
    els.forEach(function(e){if(!editable(e))return;e.setAttribute('contenteditable','true');e.setAttribute('spellcheck','false');});
    paintBar();bar.classList.add('on');vv();
  }
  function exitEdit(silent){
    editing=false;pending={};root.classList.remove('dub-edit');
    els.forEach(function(e){e.removeAttribute('contenteditable');e.removeAttribute('spellcheck');e.classList.remove('dub-chg');});
    if(bar)bar.classList.remove('on');applyAll(ov);
  }
  function save(){
    var ch={},n=0;
    Object.keys(pending).forEach(function(k){Object.keys(pending[k]).forEach(function(l){var v=clean(pending[k][l]);
      if(v!==clean(eff(k,l))){(ch[k]=ch[k]||{})[l]=v;n++;}});});
    if(!n){pending={};applyAll(ov);paintBar();toast(S('none'));return;}
    var code=ls(LS_K);bar._save.disabled=true;
    post('/api/save',{code:code,changes:ch}).then(function(j){
      if(j.ok&&j.content){pending={};ls(LS_C,JSON.stringify(j.content));applyAll(j.content);paintBar();toast(S('saved'));}
      else if(j.status===401){toast(S('bad'));ls(LS_K,null);paintBar();}
      else{toast(S('err'));paintBar();}
    }).catch(function(){toast(S('err'));paintBar();});
  }
  window.dubAfterApply=function(l){
    if(modal&&modal.classList.contains('on'))modal._t();
    if(!editing)return;
    els.forEach(function(e){e.classList.remove('dub-chg');});
    Object.keys(pending).forEach(function(k){var v=pending[k][l];if(v==null)return;
      d.querySelectorAll('[data-i="'+k+'"]').forEach(function(e){e.innerHTML=v;e.classList.add('dub-chg');});});
    paintBar();
  };
  /* keep the bar above the iPhone keyboard */
  function vv(){if(!bar||!window.visualViewport)return;var v=window.visualViewport;var off=window.innerHeight-(v.height+v.offsetTop);bar.style.transform=off>1?'translateY('+(-off)+'px)':'';}
  if(window.visualViewport){window.visualViewport.addEventListener('resize',vv);window.visualViewport.addEventListener('scroll',vv);}

  d.addEventListener('input',function(e){if(!editing)return;var t=e.target.closest&&e.target.closest('[data-i][contenteditable]');if(!t)return;
    var k=t.getAttribute('data-i');(pending[k]=pending[k]||{})[lang()]=t.innerHTML;t.classList.add('dub-chg');
    d.querySelectorAll('[data-i="'+k+'"]').forEach(function(o){if(o!==t){o.innerHTML=t.innerHTML;o.classList.add('dub-chg');}});paintBar();},true);
  d.addEventListener('click',function(e){if(!editing)return;var a=e.target.closest&&e.target.closest('a,button,label,summary');
    if(!a||a.closest('.adm-bar,.adm-modal')||a.id==='langBtn'||a.closest('#langBtn'))return;e.preventDefault();e.stopPropagation();},true);
  d.addEventListener('submit',function(e){if(editing&&!e.target.closest('.adm-modal')){e.preventDefault();e.stopPropagation();}},true);
  d.addEventListener('keydown',function(e){if(!editing||e.key!=='Enter')return;var t=e.target.closest&&e.target.closest('[contenteditable]');if(!t)return;
    e.preventDefault();if(!d.execCommand('insertLineBreak'))d.execCommand('insertHTML',false,'<br>');},true);
  d.addEventListener('paste',function(e){if(!editing)return;var t=e.target.closest&&e.target.closest('[contenteditable]');if(!t)return;
    e.preventDefault();var s=(e.clipboardData||window.clipboardData).getData('text/plain')||'';d.execCommand('insertText',false,s);},true);
  window.addEventListener('beforeunload',function(e){if(editing&&count()){e.preventDefault();e.returnValue='';}});

  /* entry points: the footer lock and #admin */
  [].forEach.call(d.querySelectorAll('.adm-open'),function(a){a.addEventListener('click',function(e){e.preventDefault();openLogin();});});
  function hash(){if(location.hash==='#admin')openLogin();}
  window.addEventListener('hashchange',hash);
  load();hash();
})();
