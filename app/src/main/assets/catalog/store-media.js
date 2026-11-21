"use strict";
const storeDetails=new Map();
let idleTimer=0,mediaEpoch=0,player=null,optionFocus=null,cinemaOrigin=null,ducked=false;
function trustedMedia(value){
 try{const u=new URL(value);return u.protocol==="https:"&&u.hostname.endsWith(".steamstatic.com")?u.href:""}catch(e){return ""}
}
let pcMedia={};
function receiveMedia(rows){pcMedia=rows;if(atlasHost)try{localStorage.setItem("dolos.media."+atlasHost,JSON.stringify(rows))}catch(e){}}
function detailsFor(g){
 const id=/^\d{1,10}$/.test(g?.steamId||"")?g.steamId:controlData.storeLinks?.[g?.name];if(!/^\d{1,10}$/.test(id||""))return Promise.resolve(null);
 if(pcMedia[id])return Promise.resolve(pcMedia[id]);
 if(!storeDetails.has(id)){
  const result=fetch("/metadata/"+id).then(r=>r.json()).then(raw=>{
   const d=raw[id]?.data;if(!d){storeDetails.delete(id);return null;}
   const movies=d.movies||[];const movie=[...movies.filter(m=>m.highlight),...movies].find(m=>trustedMedia(m.hls_h264)||trustedMedia(m.mp4?.["480"]));
   const text=new DOMParser().parseFromString(d.short_description||"","text/html").body.textContent;
   return {header:trustedMedia(d.header_image),backdrop:trustedMedia(d.background_raw)||trustedMedia(d.background),description:text,genre:(d.genres||[]).slice(0,2).map(r=>r.description).join(" · "),movie:trustedMedia(movie?.hls_h264)||trustedMedia(movie?.mp4?.["480"]),shots:(d.screenshots||[]).slice(0,4).map(s=>({thumb:trustedMedia(s.path_thumbnail),full:trustedMedia(s.path_full)})).filter(s=>s.thumb&&s.full)}
  }).catch(()=>{storeDetails.delete(id);return null});
  storeDetails.set(id,result)
 }
 return storeDetails.get(id)
}
function stopMedia(){
 if(ducked){ducked=false;native("menuaudio")}clearTimeout(idleTimer);mediaEpoch++;if(player){player.destroy();player=null}
 for(const id of ["ambientTrailer","featureTrailer"]){const v=document.getElementById(id);if(!v)continue;v.onplaying=v.onended=v.onerror=null;v.pause();if(v.hasAttribute("src")){v.removeAttribute("src");v.load()}v.classList.remove("playing")}
}
let hlsScript;
function playFilm(video,url,silent){
 if(!window.Hls&&url.includes(".m3u8")&&!video.canPlayType("application/vnd.apple.mpegurl")&&!window.remoteArt&&!video.dataset.nativeFallback){
   const epoch=mediaEpoch;
   if(!hlsScript)hlsScript=new Promise(resolve=>{const script=document.createElement("script");script.src="hls-light.js";script.onload=()=>resolve(!!window.Hls);script.onerror=()=>resolve(false);document.head.append(script)});
   hlsScript.then(ok=>{if(!ok){hlsScript=null;video.dataset.nativeFallback="1"}if(epoch===mediaEpoch)playFilm(video,url,silent)});return;
 }
 if(!silent){ducked=true;native("filmaudio")}const epoch=mediaEpoch;const homeAudio=silent&&page==="home"&&window.tvTrailerAudio;video.muted=silent&&!homeAudio;video.loop=false;
 function fail(){if(epoch!==mediaEpoch)return;stopMedia();if(!silent){document.getElementById("cinema").hidden=true;const label=document.getElementById("synopsis");label.textContent="Trailer derzeit nicht abspielbar. "+label.textContent;document.getElementById("watchTrailer").focus()}}
 video.onplaying=()=>{if(homeAudio&&!ducked){ducked=true;native("filmaudio")}const reveal=()=>{if(epoch===mediaEpoch)video.classList.add("playing")};if(video.requestVideoFrameCallback)video.requestVideoFrameCallback(reveal);else reveal()};
 video.onended=()=>{if(!silent){closeCinema();return}video.classList.remove("playing");setTimeout(()=>{if(epoch===mediaEpoch)stopMedia()},1200)};video.onerror=fail;
 const start=()=>{if(epoch===mediaEpoch)video.play().catch(fail)};
 if(url.includes(".m3u8")&&window.Hls?.isSupported()){
  player=new Hls({enableWorker:false,capLevelToPlayerSize:true,startLevel:-1,autoStartLoad:true,...(window.remoteArt?{abrEwmaDefaultEstimate:700000,maxBufferLength:12}: {})});
  let retriedNetwork=false,retriedMedia=false;
  player.on(Hls.Events.ERROR,(_e,data)=>{if(!data.fatal||epoch!==mediaEpoch)return;
    if(window.remoteArt&&!retriedNetwork&&data.type===Hls.ErrorTypes.NETWORK_ERROR){retriedNetwork=true;player.startLoad();return}
    if(window.remoteArt&&!retriedMedia&&data.type===Hls.ErrorTypes.MEDIA_ERROR){retriedMedia=true;player.recoverMediaError();return}
    fail()});
  player.on(Hls.Events.MANIFEST_PARSED,start);player.loadSource(url);player.attachMedia(video)
 }else{video.src=url;start()}
}
function resumeAmbient(){if(page==="home")scheduleTrailer(current());else if(page==="product")scheduleTrailer(product,"product")}
function scheduleTrailer(g,where="home"){
 stopMedia();const epoch=mediaEpoch;if(!g?.id)return;
 setTimeout(()=>{if(epoch===mediaEpoch)detailsFor(g)},400);
 idleTimer=setTimeout(async()=>{
  let d=await detailsFor(g);if(!d&&window.remoteArt&&epoch===mediaEpoch){await new Promise(resolve=>setTimeout(resolve,2500));if(epoch===mediaEpoch)d=await detailsFor(g)}if(epoch!==mediaEpoch||document.hidden||page!==where||(where==="home"?selection:product?.id)!==g.id||!$("#cinema").hidden||!d?.movie||!$("#center").hidden||!$("#gameOptions").hidden)return;
  playFilm($("#ambientTrailer"),d.movie,true)
 },where==="home"?8500:10000)
}
function loadProduct(g){
 const desc=$("#synopsis"),shots=$("#shots"),watch=$("#watchTrailer");
 desc.textContent="";shots.replaceChildren();watch.hidden=true;
 detailsFor(g).then(d=>{
  if(page!=="product"||product!==g)return;
  desc.textContent=d?[d.genre,d.description].filter(Boolean).join("  ·  "):"Für diesen Titel sind keine weiteren Store-Informationen verfügbar.";
  if(!window.remoteWall&&d?.shots?.length&&!g.hero&&!document.body.classList.contains("art")){
   g.hero=d.shots[0].full;lastWall=null;background(g)
  }
  for(const shot of d?.shots||[]){
   const thumb=document.createElement("button"),im=new Image();im.alt="Spielansicht "+(shots.children.length+1);im.src=shot.thumb;im.onerror=()=>thumb.remove();
   thumb.append(im);shots.append(thumb);thumb.onclick=()=>{stopMedia();cinemaOrigin=thumb;$("#largeShot").src=shot.full;$("#largeShot").hidden=false;$("#featureTrailer").hidden=true;$("#cinema").hidden=false;$("#leaveCinema").focus()}
  }
  if(d?.movie){watch.hidden=false;watch.onclick=()=>{stopMedia();cinemaOrigin=watch;$("#largeShot").hidden=true;$("#featureTrailer").hidden=false;$("#cinema").hidden=false;$("#leaveCinema").focus();playFilm($("#featureTrailer"),d.movie,false)}}
 })
}
function closeCinema(){stopMedia();$("#cinema").hidden=true;$("#largeShot").hidden=true;(cinemaOrigin||$("#launch")).focus();resumeAmbient()}
function closeOptions(){const saved=optionFocus;$("#gameOptions").hidden=true;if(saved?.isConnected)saved.focus();resumeAmbient()}
function gameOptionsForFocus(){if(!$("#gameOptions").hidden){closeOptions();return}if(!$("#center").hidden||!$("#cinema").hidden)return;const id=document.activeElement?.closest("[data-id]")?.dataset.id;const g=items.find(x=>x.id===id)||(page==="product"?product:null);if(g?.id)openGameOptions(g)}
function openGameOptions(g){
 if(!$("#cinema").hidden||!$("#center").hidden)return;
 stopMedia();optionFocus=document.activeElement;const box=$(".gameSheet");box.replaceChildren();
 const h=document.createElement("h2");h.textContent=g.name;box.append(h);
 function add(text,fn){button(box,text,()=>{closeOptions();fn()})}
 add("Spielseite öffnen",()=>detail(g));add(download(g)?"Installieren":"Spielen",()=>playGame(g));
 add(g.pinned?"Aus Spielen entfernen":"Zu Spielen hinzufügen",()=>{g.pinned=!g.pinned;native(g.pinned?"pin":"unpin",g.id);if(page==="home")showHome()});
 if(g.steamId)add("Speicherpfad für dieses Profil",()=>native("savepath",g.id));
 if(g.removable)add("Deinstallieren",()=>native("remove",g.id));
 add("Schließen",()=>{});$("#gameOptions").hidden=false;box.querySelector("button").focus()
}
document.getElementById("leaveCinema").onclick=closeCinema;
document.addEventListener("visibilitychange",()=>{if(document.hidden){stopMedia();document.getElementById("cinema").hidden=true}else resumeAmbient()});
document.addEventListener("keydown",e=>{if(e.key.toLowerCase()==="y"&&e.target.tagName!=="INPUT"){e.preventDefault();gameOptionsForFocus()}});

document.addEventListener("focusin",e=>{if(page==="home"&&!e.target.closest("#rail,#hub")&&$("#gameOptions").hidden)stopMedia()});
