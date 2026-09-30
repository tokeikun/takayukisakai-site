/* takayukisakai.com — shared behaviour (no dependencies) */
(function(){
  var d=document, html=d.documentElement, body=d.body;
  html.classList.add('js');
  var fine = matchMedia('(hover:hover) and (pointer:fine)').matches;
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* language toggle with a short crossfade */
  var lang=d.getElementById('lang');
  function setLang(l, animate){
    var apply=function(){ body.dataset.lang=l; html.lang=l; if(lang) lang.textContent = l==='ja' ? 'EN' : '日本語';
      try{ localStorage.setItem('lang', l); }catch(e){} body.classList.remove('fading'); };
    if(animate && !reduce){ body.classList.add('fading'); setTimeout(apply,170); } else apply();
  }
  var saved=null; try{ saved=localStorage.getItem('lang'); }catch(e){}
  setLang(saved==='en' ? 'en' : 'ja', false);
  if(lang) lang.addEventListener('click', function(){ setLang(body.dataset.lang==='ja'?'en':'ja', true); });

  /* open a <details> that is the hash target */
  function revealHash(){
    var id; try{ id=decodeURIComponent(location.hash.slice(1)); }catch(e){ return; }
    if(!id) return; var t=d.getElementById(id); if(t && t.tagName==='DETAILS') t.open=true;
  }
  addEventListener('hashchange', revealHash); revealHash();
  /* jumping by anchor: show everything at once so the target is never blank */
  function revealAll(){ d.querySelectorAll('.rv').forEach(function(el){ el.classList.add('in'); }); }
  d.querySelectorAll('a[href^="#"]').forEach(function(a){ a.addEventListener('click', revealAll); });
  addEventListener('hashchange', revealAll); if(location.hash) revealAll();

  /* sticky bar state */
  var top=d.querySelector('.top'), name=d.getElementById('name');
  function barState(){ top && top.classList.toggle('scrolled', scrollY > (name ? name.getBoundingClientRect().bottom + scrollY - 20 : 24)); }
  addEventListener('scroll', barState, {passive:true}); barState();

  /* scroll reveal — elements stay visible without JS */
  var rv=[].slice.call(d.querySelectorAll('.rv'));
  if('IntersectionObserver' in window && !reduce){
    var io=new IntersectionObserver(function(es){ es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } }); },{rootMargin:'0px 0px -8% 0px',threshold:.06});
    rv.forEach(function(el){ if(el.getBoundingClientRect().top < innerHeight) el.classList.add('in'); else io.observe(el); });
  } else rv.forEach(function(el){ el.classList.add('in'); });

  /* the name casts a shadow away from the cursor (light source = pointer) */
  if(name && fine && !reduce){
    var tx=10, ty=14, cx=10, cy=14, raf=0;
    function tick(){ cx+=(tx-cx)*.08; cy+=(ty-cy)*.08;
      var b=14+Math.hypot(cx,cy)*.35;
      name.style.setProperty('--sx',cx.toFixed(1)+'px'); name.style.setProperty('--sy',cy.toFixed(1)+'px'); name.style.setProperty('--sb',b.toFixed(1)+'px');
      if(Math.abs(tx-cx)>.05||Math.abs(ty-cy)>.05) raf=requestAnimationFrame(tick); else raf=0; }
    addEventListener('pointermove', function(e){
      var r=name.getBoundingClientRect(); if(r.bottom<0) return;
      var mx=r.left+r.width/2, my=r.top+r.height/2;
      var dx=(mx-e.clientX)/innerWidth, dy=(my-e.clientY)/innerHeight;   /* −1..1 */
      tx=Math.max(-34,Math.min(34,dx*70)); ty=Math.max(-26,Math.min(30,8+dy*54));
      if(!raf) raf=requestAnimationFrame(tick);
    },{passive:true});
  }

  /* hover peek — a floating image follows the cursor over the works index */
  var rows=d.querySelectorAll('.windex a[data-img], .wside a[data-img], .pn a[data-img]');
  if(rows.length && fine && !reduce){
    var peek=d.createElement('div'); peek.id='peek'; var pimg=d.createElement('img'); pimg.alt=''; peek.appendChild(pimg); body.appendChild(peek);
    var px=0,py=0,gx=0,gy=0,praf=0,on=false;
    function ptick(){ px+=(gx-px)*.14; py+=(gy-py)*.14; peek.style.left=px+'px'; peek.style.top=py+'px';
      if(on||Math.abs(gx-px)>.5||Math.abs(gy-py)>.5) praf=requestAnimationFrame(ptick); else praf=0; }
    rows.forEach(function(a){
      a.addEventListener('mouseenter', function(e){ pimg.src=a.getAttribute('data-img'); on=true; peek.classList.add('on'); gx=px=e.clientX+190; gy=py=e.clientY; if(!praf) praf=requestAnimationFrame(ptick); });
      a.addEventListener('mousemove', function(e){ gx=Math.min(innerWidth-160,e.clientX+190); gy=e.clientY; });
      a.addEventListener('mouseleave', function(){ on=false; peek.classList.remove('on'); });
    });
  }

  /* ambient loops: play only while on screen */
  var loops=d.querySelectorAll('video[data-autoplay]');
  if(loops.length && 'IntersectionObserver' in window){
    var vio=new IntersectionObserver(function(es){ es.forEach(function(e){ var v=e.target;
      if(e.isIntersecting){ if(!reduce){ v.play().catch(function(){}); } } else v.pause(); }); },{threshold:.2});
    loops.forEach(function(v){ vio.observe(v); });
  }

  /* video facade — load the player only when asked */
  d.querySelectorAll('.video.yt').forEach(function(v){
    v.querySelector('.play').addEventListener('click', function(){
      var f=d.createElement('iframe'); f.src=v.getAttribute('data-src'); f.allow='autoplay; fullscreen; picture-in-picture'; f.allowFullscreen=true; f.title=v.getAttribute('data-title')||'film';
      v.innerHTML=''; v.appendChild(f); v.classList.remove('yt');
    });
  });
})();
