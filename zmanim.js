/* זמני היום — live Hebrew date, parsha and zmanim for Monsey (Hebcal, client-side) */
(function(){
  var box=document.getElementById('zmanim');if(!box||!window.fetch)return;
  var ZIP='10952',TZ='America/New_York',H='https://www.hebcal.com/';
  var data=null;
  function t(k){return window.dubT?window.dubT(k):k;}
  function lang(){return window.dubLang?window.dubLang():'yi';}
  function nyParts(d){
    var o={};new Intl.DateTimeFormat('en-US',{timeZone:TZ,year:'numeric',month:'2-digit',day:'2-digit',weekday:'short'})
      .formatToParts(d).forEach(function(p){o[p.type]=p.value;});
    return {ymd:o.year+'-'+o.month+'-'+o.day,y:+o.year,m:+o.month,d:+o.day,
      wd:['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].indexOf(o.weekday)};
  }
  function get(url){
    var ctl=window.AbortController?new AbortController():null,tm=setTimeout(function(){if(ctl)ctl.abort();},9000);
    return fetch(url,ctl?{signal:ctl.signal}:{}).then(function(r){clearTimeout(tm);if(!r.ok)throw new Error(r.status);return r.json();});
  }
  /* "2026-10-20T05:52:00-04:00" -> "5:52" (the clock time as Hebcal states it for Monsey) */
  function hm(iso){var m=/T(\d\d):(\d\d)/.exec(iso||'');if(!m)return '';var h=+m[1]%12;return (h||12)+':'+m[2];}
  function minus(iso,min){var d=new Date(Date.parse(iso)-min*60000),m=/T\d\d:\d\d:\d\d([+-]\d\d:\d\d)$/.exec(iso);
    var off=m?m[1]:'-05:00',sign=off[0]==='-'?-1:1,mins=sign*(+off.substr(1,2)*60+ +off.substr(4,2));
    var l=new Date(d.getTime()+mins*60000);
    function p(n){return (n<10?'0':'')+n;}
    return l.getUTCFullYear()+'-'+p(l.getUTCMonth()+1)+'-'+p(l.getUTCDate())+'T'+p(l.getUTCHours())+':'+p(l.getUTCMinutes())+':00'+off;}

  function render(){
    if(!data)return;var en=lang()==='en';
    document.getElementById('zmDay').textContent=t(data.wd===6?'zm_shabbos':'zm_d'+data.wd);
    var c=data.conv,heb='';
    if(en)heb=c.hd+' '+c.hm+' '+c.hy;
    else{var p=c.heDateParts||{},mo=p.m==='חשון'?'מרחשון':p.m;heb=(p.d&&mo&&p.y)?p.d+' '+mo+' '+p.y:c.hebrew;}
    document.getElementById('zmHeb').textContent=heb;
    var par=data.parsha,pe=document.getElementById('zmParsha');
    pe.textContent=par?(en?par.title.replace(/^Parashat /,'Parshas '):par.hebrew):'';
    box.classList.toggle('no-parsha',!par);
  }
  function mark(){
    if(!data)return;var now=Date.now(),next=null;
    [].forEach.call(box.querySelectorAll('.zm-list li'),function(li){
      li.classList.remove('next');var iso=li.getAttribute('data-iso');
      if(li.hidden||!iso)return;var ts=Date.parse(iso);
      li.classList.toggle('past',ts<now);
      if(ts>=now&&(!next||ts<Date.parse(next.getAttribute('data-iso'))))next=li;
    });
    if(next)next.classList.add('next');
    return next;
  }
  function setZ(k,iso){var li=box.querySelector('li[data-z="'+k+'"]');if(!li)return false;
    if(!iso){li.hidden=true;return false;}
    li.setAttribute('data-iso',iso);li.querySelector('.zt').textContent=hm(iso);li.hidden=false;return true;}

  var today=nyParts(new Date());
  Promise.all([
    get(H+'zmanim?cfg=json&zip='+ZIP+'&date='+today.ymd),
    get(H+'shabbat?cfg=json&zip='+ZIP+'&M=on&gy='+today.y+'&gm='+today.m+'&gd='+today.d).catch(function(){return {items:[]};})
  ]).then(function(r){
    var z=r[0]&&r[0].times;if(!z||!z.sunrise||!z.sunset)throw new Error('no zmanim');
    var items=(r[1]&&r[1].items)||[],gs='';
    return get(H+'converter?cfg=json&gy='+today.y+'&gm='+today.m+'&gd='+today.d+'&g2h=1'+gs).then(function(conv){
      if(!conv||!conv.hy)throw new Error('no date');
      var par=null,cand=null,havd=null;
      items.forEach(function(it){
        if(it.category==='parashat'&&!par)par=it;
        if(it.category==='candles'&&(it.date||'').indexOf(today.ymd)===0)cand=it.date;
        if(it.category==='havdalah'&&(it.date||'').indexOf(today.ymd)===0)havd=it.date;
      });
      setZ('alos',minus(z.sunrise,72));setZ('netz',z.sunrise);
      setZ('shmaMga',z.sofZmanShmaMGA);setZ('shmaGra',z.sofZmanShma);var _o=(/([+-]\d\d:\d\d)$/.exec(z.sunset)||['','-05:00'])[1],_d=z.sunset.slice(0,10);setZ('tfila',_d+'T11:00:00'+_o);
      setZ('chatzos',_d+'T13:00:00'+_o);setZ('shkia',z.sunset);setZ('tzeis',today.wd===6?null:z.tzeit72min);
      setZ('candles',today.wd===5?(cand||minus(z.sunset,18)):null);
      setZ('motzei',today.wd===6?z.tzeit72min:null);
      setZ('rt',null);
      data={wd:today.wd,conv:conv,parsha:par};
      render();var nx=mark();box.hidden=false;
      requestAnimationFrame(function(){box.classList.add('in');
        var ul=document.getElementById('zmList');
        if(nx&&ul.scrollWidth>ul.clientWidth+2){var a=nx.getBoundingClientRect(),b=ul.getBoundingClientRect();
          try{ul.scrollBy({left:(a.left+a.width/2)-(b.left+b.width/2)});}catch(e){}}
      });
      setInterval(function(){if(nyParts(new Date()).ymd!==today.ymd){location.reload();return;}mark();},30000);
    });
  }).catch(function(){box.hidden=true;});
  window.dubZmSync=render;
})();
