"use strict";
const $=s=>document.querySelector(s);
const icons={search:'<circle cx="10" cy="10" r="6.5"/><path d="m15 15 6 6"/>',settings:'<path d="m9 3 1-2h4l1 2 3 2 2 .2 2 3.5-1.2 1.8v3l1.2 1.8-2 3.5-2 .2-3 2-1 2h-4l-1-2-3-2-2-.2-2-3.5 1.2-1.8v-3L2 8.7l2-3.5 2-.2Z"/><circle cx="12" cy="12" r="3.5"/>',bag:'<path d="M5 8.5h14l1.2 13H3.8z"/><path d="M8.5 10V6.1a3.5 3.5 0 0 1 7 0V10"/><path d="m10 16 2-3 2 3z"/>',home:'<path d="m2 11 10-8 10 8M5 10v11h5v-7h4v7h5V10"/>',user:'<circle cx="12" cy="8" r="4"/><path d="M4 22a8 8 0 0 1 16 0"/>',power:'<path d="M12 2v10M7 5a9 9 0 1 0 10 0"/>',quit:'<rect x="4" y="4" width="16" height="16" rx="3"/>'};
function svg(id){return '<svg aria-hidden="true" viewBox="0 0 24 24">'+icons[id]+'</svg>'}
document.querySelectorAll("[data-icon]").forEach(b=>b.innerHTML=svg(b.dataset.icon));
let familyLink=null,items=[],page="home",selection="",product=null,filter=0,username="",sound=true,initialized=false;
let wallIndex=0,wallToken=0,lastWall=null,context=null,lastTone=0,returnFocus=null;
const filters=["Alle Spiele","Installiert","Zum Download","Eigene Spiele","Hinzugefügt"];
let shelfScope="",rememberedTile=null,renderingShelf=false;
function shelfIdentity(g){return g.steamId?"steam."+g.steamId:String(g.id)}
const storeTile={id:"",name:"Dolos Store"};
function native(name,id){location.href="aster://"+name+"/"+(id||0)}
function tone(ok=false){
 if(!sound||!navigator.userActivation?.hasBeenActive)return;
 try{const now=performance.now();if(now-lastTone<65)return;lastTone=now;
 context=context||new AudioContext();if(context.state==="suspended")context.resume();
 const t=context.currentTime,o=context.createOscillator(),g=context.createGain();o.type="sine";o.frequency.setValueAtTime(ok?587:783,t);o.frequency.exponentialRampToValueAtTime(ok?880:622,t+.095);g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(.037,t+.009);g.gain.exponentialRampToValueAtTime(.0001,t+.16);o.connect(g);g.connect(context.destination);o.start();o.stop(t+.18)}catch(e){}
}
function systemBar(label,bars,pad){
 const wifi=$("#wifiStatus"),bt=$("#btStatus");wifi.title=label;wifi.setAttribute("aria-label",label+" · Netzwerkeinstellungen");
 wifi.querySelectorAll("path,circle").forEach((path,i)=>path.style.opacity=bars<0?.45:bars>=4-i?1:.23);
 bt.title=pad?"Bluetooth · Controller erkannt":"Bluetooth-Geräte";bt.setAttribute("aria-label",bt.title);bt.style.opacity=pad?"1":".66";
 if(label==="LAN"){wifi.dataset.lan="1";wifi.style.opacity="1"}else delete wifi.dataset.lan;
}
function refreshClock(){const date=new Date();$("time").textContent=date.toLocaleTimeString("de-DE",{hour:"2-digit",minute:"2-digit"})}
refreshClock();setInterval(refreshClock,15000);
let sortFrame=0;
function classifyCover(g,im){
 if(im)im.classList.toggle("wideCover",im.naturalWidth>=im.naturalHeight);
 if(!window.remoteArt && g.hasCover!=null && !g.id.startsWith("s"))return;
 let real=!!im;
 if(im){try{
  const c=document.createElement("canvas");c.width=8;c.height=8;const ctx=c.getContext("2d");ctx.drawImage(im,0,0,8,8);
  const px=ctx.getImageData(0,0,8,8).data;
  const a=0,b=28,dark=252;
  real=!(px[a+2]>px[a] && px[b+2]>px[b] && px[dark]<26 && px[dark+1]<34 && px[dark+2]<58 &&
    px[a+1]>=38&&px[a+1]<=51&&px[dark+2]>px[dark+1]&&Math.abs(px[dark+1]-px[dark])<13);
 }catch(e){}}
 if(real===coverFlags.get(g.id))return;coverFlags.set(g.id,real);
 if(page==="store"&&missingLast&&!sortFrame)sortFrame=requestAnimationFrame(()=>{sortFrame=0;sortStoreCards()})
}
function sortStoreCards(){
 if(page!=="store")return;
 const grid=$(".grid"),active=document.activeElement,top=grid.scrollTop;
 const cards=[...grid.children],map=new Map(items.map(i=>[i.id,i]));
 const sorted=cards.sort((a,b)=>rankGames(map.get(a.dataset.id),map.get(b.dataset.id)));
 for(let i=0;i<sorted.length;i++)if(grid.children[i]!==sorted[i])grid.insertBefore(sorted[i],grid.children[i]);
 if(active!==document.activeElement&&grid.contains(active))active.focus({preventScroll:true});
 if(grid.scrollTop!==top)grid.scrollTop=top;
}
function pcArt(g,kind){
 const rev=typeof controlData!=="undefined"&&controlData.pcArtwork?.[g?.steamId]?.[kind];
 return rev?"/artwork/"+g.steamId+"/"+kind+"/"+rev:"";
}
let atlasHost="",atlasRev="",atlasCells=new Map(),atlasPages=new Map();
function restoreArtwork(host){
 if(atlasHost!==host){atlasRev="";atlasCells.clear();atlasPages.clear();controlData.pcArtwork={}}
 atlasHost=host;
 try{pcMedia=JSON.parse(localStorage.getItem("dolos.media."+host))||{}}catch(e){}
 try{const saved=JSON.parse(localStorage.getItem("dolos.artwork."+host));if(saved){controlData.pcArtwork=saved.art;applyAtlas(saved.atlas)}}catch(e){}
}
function applyAtlas(def){
 if(!atlasHost||!def?.rev||atlasRev===def.rev||!Array.isArray(def.ids))return;
 atlasRev=def.rev;atlasCells=new Map(def.ids.map((id,i)=>[id,i]));atlasPages.clear();
}
function atlasPage(page,url){
 let cached=atlasPages.get(page);
 if(cached&&(!cached.retryAt||Date.now()<cached.retryAt))return cached.result;
 cached={retryAt:0,settled:false};
 cached.result=new Promise(resolve=>{
   const image=new Image();
   image.onload=()=>{cached.settled=true;resolve(true);schedulePosters()};
   image.onerror=()=>{cached.settled=true;cached.retryAt=Date.now()+4000;resolve(false);schedulePosters()};
   image.src=url;
 });
 atlasPages.set(page,cached);return cached.result;
}
const visiblePosters=new Set(),finePosters=new Set();
let posterObserver=null,posterTimer=0,posterLoads=0;
function resetPosterObserver(){
 posterObserver?.disconnect();posterObserver=null;visiblePosters.clear();
 for(const cell of finePosters)if(!cell.isConnected)finePosters.delete(cell);
}
function schedulePosters(delay=240){
 clearTimeout(posterTimer);posterTimer=setTimeout(refinePosters,delay);
}
function watchPoster(cell){
 if(!cell.dataset.original)return;
 if(cell.parentElement.classList.contains("art")&&window.IntersectionObserver){
   if(!posterObserver)posterObserver=new IntersectionObserver((entries,observer)=>{
     if(observer!==posterObserver)return;
     for(const item of entries){
       if(item.isIntersecting&&item.intersectionRatio>=.12)visiblePosters.add(item.target);else visiblePosters.delete(item.target);
     }
     schedulePosters();
   },{root:$(".grid"),threshold:.12});
   posterObserver.observe(cell);
 }
 schedulePosters();
}
function refinePosters(){
 posterTimer=0;
 if(document.hidden||!["home","store"].includes(page)||navigator.connection?.saveData)return;
 for(const sheet of atlasPages.values())if(!sheet.settled)return;
 const focus=page==="home"?$("#rail .current .atlasCover"):$(".card:focus .atlasCover");
 const candidates=new Set([focus]);
 if(page==="store"&&!window.remoteArt)for(const cell of visiblePosters)candidates.add(cell);
 for(const cell of candidates){
   if(posterLoads>=2)break;
   if(!cell?.isConnected||!cell.dataset.original||cell.dataset.refinement||Number(cell.dataset.retryAt||0)>Date.now()||cell.clientWidth*(window.devicePixelRatio||1)<170)continue;
   const image=new Image();image.alt="";image.decoding="async";image.fetchPriority="low";
   cell.dataset.refinement="loading";posterLoads++;
   image.onload=()=>{
     posterLoads--;
     if(cell.isConnected){
       // Keep the natural proportions and the same framing as the preview sheet.
       image.classList.toggle("wideCover",image.naturalWidth>=image.naturalHeight);
       cell.append(image);cell.dataset.refinement="ready";finePosters.add(cell);
       requestAnimationFrame(()=>image.classList.add("ready"));
       for(const old of finePosters){
         if(finePosters.size<=24)break;
         if(old===focus||visiblePosters.has(old))continue;
         old.replaceChildren();delete old.dataset.refinement;finePosters.delete(old);
       }
     }
     if(!posterTimer)schedulePosters(80);
   };
   image.onerror=()=>{posterLoads--;delete cell.dataset.refinement;cell.dataset.retryAt=String(Date.now()+15000);if(!posterTimer)schedulePosters(80)};
   image.src=cell.dataset.original;
 }
}
document.addEventListener("focusin",()=>schedulePosters());
$(".grid").addEventListener("scroll",()=>schedulePosters(),{passive:true});
window.addEventListener("resize",()=>schedulePosters(),{passive:true});
function paintAtlas(box,g){
 const n=atlasCells.get(g.steamId);if(n==null)return false;
 const rev=atlasRev,page=Math.floor(n/64),url="/artwork/"+page+"/atlas/"+rev;
 box.replaceChildren();const cell=document.createElement("span");cell.textContent=g.name;cell.className="placeholder";box.append(cell);
 atlasPage(page,url).then(ok=>{
    if(!box.isConnected||cell.parentNode!==box||rev!==atlasRev)return;
    if(!ok){art(box,g,true);return}
    cell.className="atlasCover";cell.textContent="";cell.style.backgroundImage="url("+url+")";
    cell.style.backgroundPosition=(n%8*100/7)+"% "+(Math.floor(n/8)%8*100/7)+"%";
    cell.dataset.original=pcArt(g,"cover");watchPoster(cell);
 });return true;
}
function art(box,g,skipAtlas=false){
 const old=box.querySelector(".atlasCover");
 if(old){posterObserver?.unobserve(old);visiblePosters.delete(old);finePosters.delete(old)}
 if(!skipAtlas&&paintAtlas(box,g))return;if(window.remoteArt){remoteArt(box,g);return;}box.replaceChildren();const label=document.createElement("span");label.className="placeholder";label.textContent=g.name;box.append(label);
 const urls=[...new Set([pcArt(g,"cover"),g.art,/^\d{1,10}$/.test(g.steamId||"")&&"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/"+g.steamId+"/library_600x900.jpg"].filter(Boolean))];
 if(!urls.length)return;
 const im=new Image();im.alt="";im.loading=box.className==="art"?"lazy":"eager";im.decoding="async";
 im.onload=()=>{label.remove();classifyCover(g,im)};
 im.onerror=()=>{if(urls.length){im.src=urls.shift();return}im.remove();classifyCover(g,null)};
 im.src=urls.shift();box.prepend(im);
}
function background(g){
 if(window.remoteWall){remoteWall(g);return;}
 const key=g?.id||"";if(key===lastWall)return;lastWall=key;const token=++wallToken,walls=document.querySelectorAll(".wall");
 if(!g||(!g.art&&!g.hero&&!g.steamId)){walls.forEach(w=>w.classList.remove("lit"));document.body.classList.remove("art");return}
 const im=new Image();im.onload=()=>{if(token!==wallToken)return;const next=1-wallIndex;walls[next].style.backgroundImage='url("'+im.src+'")';walls[next].classList.add("lit");walls[wallIndex].classList.remove("lit");wallIndex=next;document.body.classList.add("art")};
 im.onerror=()=>{if(token!==wallToken)return;if(g.art&&im.src!==new URL(g.art,location.href).href){im.src=g.art}else{walls.forEach(w=>w.classList.remove("lit"));document.body.classList.remove("art")}};
 im.src=pcArt(g,"hero")||g.hero||(/^\d{1,10}$/.test(g.steamId||"")?"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/"+g.steamId+"/library_hero.jpg":g.art)
}
function screen(next){if(next!=="home")$("#hint").textContent="✕　Auswählen";stopMedia();if(next!=="store")toggleOrder(false,false);page=next;document.body.dataset.page=page;for(const s of ["home","store","product","manage"])$("#"+s).hidden=s!==page;
 $("#games").classList.toggle("active",page==="home");$("#shop").classList.toggle("active",page!=="home");$("#center").hidden=true}
function animate(el){el.classList.remove("enter");void el.offsetWidth;el.classList.add("enter")}
function current(){return items.find(g=>g.id===selection && g.pinned)||storeTile}
let homeDetails={};
function setHomeDetails(settings){homeDetails=settings;refreshHomeDetails()}
function refreshHomeDetails(){
 const g=current(),fields=[];
 if(g.id&&homeDetails.status)fields.push(g.running?"Sitzung läuft":download(g)?"Zum Download":g.state==="installed"?"Installiert":"Eigenes Spiel");
 if(g.id&&homeDetails.recent&&g.lastPlayed)fields.push("Zuletzt gespielt "+new Date(g.lastPlayed).toLocaleDateString("de-DE"));
 $("#hub p").textContent=fields.join("  ·  ");$("#hub p").hidden=!fields.length;
 if(typeof renderSaveInfo==="function")renderSaveInfo();
}
function selectGame(g,button){
 const changed=selection!==g.id;
 if(changed)tone();selection=g.id;
 if(!renderingShelf&&shelfScope){rememberedTile=null;try{localStorage.setItem("dolos.shelf."+shelfScope,shelfIdentity(g))}catch(e){}}

 if(changed||!button?.classList.contains("current"))scheduleTrailer(g);
 $("#hint").textContent=g.id?"✕　Starten　　☰　Optionen":"✕　Auswählen";
 const old=$("#rail .current");if(old!==button){old?.classList.remove("current");button?.classList.add("current")}
 background(g.id?g:null);$("#gameLogo").hidden=true;$("#hub .brand").hidden=true;
 $("#hub h1").textContent=g.name;$("#hub h1").hidden=false;
 refreshHomeDetails();
}
function showHome(){
 renderingShelf=true;screen("home");const rail=$("#rail");rail.replaceChildren();let focus;
 for(const g of [storeTile,...items.filter(x=>x.pinned)]){
   const b=document.createElement("button");b.className="tile";b.setAttribute("aria-label",g.name);
   if(g.id)art(b,g);else{b.classList.add("bag");b.innerHTML=svg("bag")}
   b.dataset.id=g.id;b.oncontextmenu=e=>{e.preventDefault();if(g.id)openGameOptions(items.find(i=>i.id===g.id)||g)};b.onfocus=()=>selectGame(g,b);b.onclick=()=>{selectGame(g,b);playCurrent()};rail.append(b);if(String(g.id)===String(selection))focus=b
 }
 focus=focus||rail.firstChild;focus.focus({preventScroll:true});if(focus!==rail.firstChild)focus.scrollIntoView({block:"nearest",inline:"nearest"});else{rail.scrollLeft=0;rail.scrollTop=0;}if(!focus.classList.contains("current"))selectGame(current(),focus);renderingShelf=false
}
function download(g){return ["cached","owned","family"].includes(g.state)}
function transferLabel(g){const x=g.transfer;if(!x)return "";return x.total?Math.min(99,Math.floor(100*x.done/x.total))+" %":"Wartet"}
function refreshStoreCards(){
 const grid=$(".grid");if(!grid)return;
 const byId=new Map(items.map(g=>[g.id,g]));
 for(const card of grid.children){const g=byId.get(card.dataset.id);if(!g)continue;
   card.hidden=filter===1&&g.state!=="installed"||filter===2&&!download(g);
   const label=card.querySelector("strong");if(label){const text=g.name+(g.transfer?" · "+transferLabel(g):"");if(text!==label.textContent)label.textContent=text}
 }
}
function playGame(g){
 if(g.transfer){manage("Downloads");return}
 if(download(g)){selectInstallDrive(g)}else native("play",g.id)
}
function selectInstallDrive(g){
 stopMedia();optionFocus=document.activeElement;
 const box=$(".gameSheet");box.replaceChildren();const h=document.createElement("h2");h.textContent="Installationsort";box.append(h);
 const disks=(controlData.disks||[]).filter(d=>d.drive);
 const required=(controlData.catalog||[]).find(row=>row.id===g.steamId)?.required||0;
 for(const disk of disks){const full=required>disk.free;const b=button(box,disk.drive+"　"+bytes(disk.free)+" frei"+(full?" · Zu wenig Speicher":""),()=>{closeOptions();manage("Downloads");native("install",g.id+"?drive="+encodeURIComponent(disk.drive))});b.disabled=full}
 if(required){const p=document.createElement("p");p.textContent="Benötigt mindestens "+bytes(required);box.append(p)}
 if(!disks.length){const note=document.createElement("p");note.textContent="Dolos-PC aktualisieren und die PC-Verbindung prüfen.";box.append(note);button(box,"Verbindung prüfen",()=>{closeOptions();manage("Verbindung")})}
 button(box,"Abbrechen",closeOptions);$("#gameOptions").hidden=false;box.querySelector("button").focus()
}
function playCurrent(){const g=current();if(g.id)playGame(g);else showStore()}
const orderNames=["Name A–Z","Name Z–A","Installierte zuerst","Hinzugefügte zuerst","Zuletzt gespielt"];
let order=0,missingLast=true;
try{order=Number(localStorage.getItem("dolos.order"))||0;missingLast=localStorage.getItem("dolos.missingLast")!=="false"}catch(e){}
const coverFlags=new Map(),byName=new Intl.Collator("de",{numeric:true,sensitivity:"base"});
function rankGames(a,b){
 if(missingLast){const covers=Number(hasCover(b))-Number(hasCover(a));if(covers)return covers}
 if(order===4 && (a.lastPlayed||0)!==(b.lastPlayed||0))return (b.lastPlayed||0)-(a.lastPlayed||0);
 if(order===2 && (a.state==="installed")!==(b.state==="installed"))return a.state==="installed"?-1:1;
 if(order===3 && !!a.pinned!==!!b.pinned)return a.pinned?-1:1;
 return (order===1?-1:1)*byName.compare(a.name,b.name)||a.id.localeCompare(b.id)
}
function hasCover(g){if(window.remoteArt&&coverFlags.has(g.id))return coverFlags.get(g.id);return g.id.startsWith("s")?(coverFlags.get(g.id)??g.hasCover??false):(g.hasCover??coverFlags.get(g.id)??false)}
function toggleOrder(open,focus=true){
 const panel=$("#orderPanel");panel.hidden=!open;$("#order").setAttribute("aria-expanded",String(open));
 if(!open){if(focus)$("#order").focus();return}
 panel.replaceChildren();
 function persist(){try{localStorage.setItem("dolos.order",String(order));localStorage.setItem("dolos.missingLast",String(missingLast))}catch(e){}toggleOrder(false);showStore(false)}
 orderNames.forEach((n,i)=>{const b=button(panel,n,()=>{order=i;persist()});b.setAttribute("aria-pressed",String(i===order))});
 const b=button(panel,missingLast?"Ohne Cover: am Ende":"Ohne Cover: einsortiert",()=>{missingLast=!missingLast;persist()});b.setAttribute("aria-pressed",String(missingLast));panel.children[order]?.focus()
}
$("#order").onclick=()=>toggleOrder($("#orderPanel").hidden);
function shoulder(key){
 if(window.closeTvKeyboard?.())return;
 if(!$("#cinema").hidden||!$("#gameOptions").hidden||!$("#center").hidden){back();return}
 if(key==="home"){showHome();return}if(key==="store"){showStore();return}
 if(page==="store"){filter=(filter+(key==="next"?1:-1)+filters.length)%filters.length;showStore()}else if(key==="next")showStore();else showHome();
}
function showStore(focusId){if(page!=="store")native("status");
 screen("store");background(null);const q=$("#search").value.trim().toLocaleLowerCase();
 const list=items.filter(g=>g.name.toLocaleLowerCase().includes(q)&&[true,g.state==="installed",download(g),["host","shortcut"].includes(g.state),g.pinned][filter]).sort(rankGames);
 document.querySelectorAll("#filters button").forEach((b,i)=>b.classList.toggle("active",i===filter));
 const grid=$(".grid");grid.replaceChildren();resetPosterObserver();$("#empty").hidden=!!list.length;
 for(const g of list){const b=document.createElement("button");b.className="card";b.dataset.id=g.id;b.oncontextmenu=e=>{e.preventDefault();openGameOptions(g)};const cover=document.createElement("span");cover.className="art";art(cover,g);
 const name=document.createElement("strong");name.textContent=g.name+(g.transfer?" · "+transferLabel(g):"");b.append(cover,name);b.onclick=()=>detail(g);grid.append(b)}
 
 if(focusId!==false){const button=[...grid.children].find(b=>b.dataset.id===focusId)||grid.firstChild||$("#search");button.focus({preventScroll:true});button.scrollIntoView({block:"nearest",inline:"nearest"})}
}
function detail(g){product=g;screen("product");background(g);scheduleTrailer(g,"product");loadProduct(g);renderSaveInfo();$(".productInfo h1").textContent=g.name;
 $(".productInfo p").textContent=({installed:"Auf dem PC installiert",cached:"Verfügbarkeit beim Installieren prüfen",owned:"In deiner Bibliothek",family:"Familienbibliothek",shortcut:"Eigenes Spiel",host:"Eigenes Spiel"})[g.state]||"";
 $("#trophies").hidden=!/^\d{1,10}$/.test(g.steamId||"");$("#pin").textContent=g.pinned?"Aus Spielen entfernen":"Zu Spielen hinzufügen";$("#launch").textContent=download(g)?"Installieren":"Spielen";$("#remove").hidden=!g.removable;$("#launch").focus();animate($(".productInfo"))
}
function closeCenter(){const previous=returnFocus;$("#center").hidden=true;if(previous?.isConnected)previous.focus();resumeAmbient()}
function controls(){stopMedia();if(!$("#gameOptions").hidden){closeOptions();return}if(!$("#center").hidden){closeCenter();return}returnFocus=document.activeElement;const list=$("#switcher");list.replaceChildren();
 for(const g of items.filter(g=>g.pinned).slice(0,4)){
   const b=button(list,g.name,()=>{closeCenter();selection=g.id;showHome()});const im=new Image();im.alt="";im.src=g.art;b.prepend(im)
 }
 $("#center").hidden=false;$("#dock button").focus()}
function back(){if(window.closeTvKeyboard?.())return;if(!$("#cinema").hidden){closeCinema();return}if(!$("#gameOptions").hidden){closeOptions();return}if(!$("#orderPanel").hidden){toggleOrder(false);return}if(!$("#center").hidden)closeCenter();else if(page==="product")showStore(product.id);else if(page==="store"||page==="manage")showHome();else controls()}
function button(parent,name,callback,icon){const b=document.createElement("button");if(icon)b.innerHTML=svg(icon);b.append(document.createTextNode(name));b.onclick=callback;parent.append(b);return b}
filters.forEach((f,i)=>button($("#filters"),f,()=>{filter=i;showStore(false)}));
for(const [label,icon,run] of [["Startseite","home",showHome],["Store","bag",showStore],["Profil","user",()=>native("profile")],["Downloads","bag",()=>manage("Downloads")],["Einstellungen","settings",()=>native("studio","appearance")],["Sitzung beenden","quit",()=>native("quit")],["Energie","power",()=>native("power")]])button($("#dock"),label,()=>{closeCenter();run()},icon);
$("#games").onclick=showHome;$("#shop").onclick=()=>showStore();
$("#searchBtn").onclick=()=>{showStore(false);$("#search").focus()};$("#search").oninput=()=>showStore(false);
$("#settings").onclick=()=>native("studio","appearance");$("#profile").onclick=()=>native("profile");
$("#trophies").onclick=()=>{trophyData=null;manage("Trophäen");native("trophies",product.id)};
$("#launch").onclick=()=>playGame(product);$("#remove").onclick=()=>{const g=product;manage("Downloads");native("remove",g.id)};
$("#pin").onclick=()=>{product.pinned=!product.pinned;if(product.pinned)selection=product.id;native(product.pinned?"pin":"unpin",product.id);detail(product)};
window.loadCatalog=(rows,profile,enableSound,scope="",slotKey=profile)=>{
 saveScope=scope;
 const changed=slotKey!==shelfScope;
 if(changed){
  shelfScope=slotKey;selection="";rememberedTile=null;
  try{rememberedTile=localStorage.getItem("dolos.shelf."+slotKey)}catch(e){}
 }
 username=profile;sound=enableSound;$("#profile b").textContent=(profile||"D").slice(0,1).toUpperCase();$("#profile").setAttribute("aria-label","Profil: "+profile);
 familyLink=rows.find(g=>g.name==="Steam Big Picture"&&g.state==="host");

 for(const g of rows){const cover=typeof controlData!=="undefined"?controlData.covers?.[g.steamId||g.name]:undefined;if(typeof cover==="boolean")g.hasCover=cover}
 const priorGame=items.find(x=>x.id===selection);
 items=rows.filter(g=>!(g.state==="host"&&["Steam Big Picture","Desktop","Virtual Display"].includes(g.name)));
 if(!changed&&priorGame?.steamId&&!items.some(x=>x.id===selection&&x.pinned))selection=items.find(x=>x.pinned&&x.steamId===priorGame.steamId)?.id||"";
 if(rememberedTile){const saved=items.find(x=>x.pinned&&shelfIdentity(x)===rememberedTile);if(saved){selection=saved.id;rememberedTile=null}}
 const shelf=[storeTile,...items.filter(g=>g.pinned)];
 const tiles=[...$("#rail").children];
 if(initialized&&!changed&&page==="home"&&shelf.length===tiles.length&&shelf.every((g,i)=>g.id===tiles[i].dataset.id&&g.name===tiles[i].getAttribute("aria-label"))){
    refreshHomeDetails();return;
 }
 if(!initialized||changed||page==="home"){initialized=true;showHome()}
 else if(page==="store")showStore(document.activeElement?.dataset.id);else if(page==="product"){const game=items.find(x=>x.id===product?.id);game?detail(game):showStore()}
};
document.addEventListener("click",()=>tone(true));document.addEventListener("focusin",()=>tone());
document.addEventListener("keydown",e=>{
 if(e.key==="Backspace"&&e.target===$("#search"))return;
 if(["Escape","BrowserBack","Backspace"].includes(e.key)){e.preventDefault();back();return}
 if(e.key==="ContextMenu"){e.preventDefault();gameOptionsForFocus();return}
 const dir={ArrowRight:[1,0],ArrowLeft:[-1,0],ArrowDown:[0,1],ArrowUp:[0,-1]}[e.key];if(!dir||e.target===$("#search")&&dir[0])return;
 const active=document.activeElement;
 if(page==="home"&&$("#center").hidden&&$("#gameOptions").hidden){
  const buttons=[...document.querySelectorAll("header button")].filter(b=>b.offsetWidth);
  const idx=buttons.indexOf(active);
  if(idx>=0){
   e.preventDefault();
   if(dir[0]) buttons[Math.max(0,Math.min(buttons.length-1,idx+dir[0]))].focus({preventScroll:true});
   else if(dir[1]>0) ($("#rail .current")||$("#rail button"))?.focus({preventScroll:true});
   return;
  }
  if(active.parentElement===$("#rail")&&dir[1]<0&&(!document.body.classList.contains("enhanced")||!active.previousElementSibling||innerWidth<innerHeight)){
   e.preventDefault();buttons[0]?.focus({preventScroll:true});return;
  }
 }
 if(page==="manage"&&managePage==="Downloads"&&$("#gameOptions").hidden&&$("#center").hidden&&dir[1]){
  const row=active.closest("#manager section");
  if(row){let target=dir[1]>0?row.nextElementSibling:row.previousElementSibling;
   while(target){const b=target.matches("button")?target:target.querySelector("button");if(b){e.preventDefault();b.focus({preventScroll:true});b.scrollIntoView({block:"nearest"});return}target=dir[1]>0?target.nextElementSibling:target.previousElementSibling}
  }
 }
 if(page==="home"&&active.parentElement===$("#rail")&&$("#gameOptions").hidden&&$("#center").hidden){
    const vertical=document.body.classList.contains("enhanced")&&innerWidth>=innerHeight;
    const step=vertical?dir[1]:dir[0];
    if(step){e.preventDefault();const next=step>0?active.nextElementSibling:active.previousElementSibling;if(next){e.preventDefault();next.focus({preventScroll:true});const rail=next.parentElement,r=rail.getBoundingClientRect(),n=next.getBoundingClientRect(),margin=10;
       const delta=vertical?(n.bottom>r.bottom-margin?n.bottom-r.bottom+margin:Math.min(0,n.top-r.top-margin)):(n.right>r.right-margin?n.right-r.right+margin:Math.min(0,n.left-r.left-margin));
       if(delta)rail.scrollBy({left:vertical?0:delta,top:vertical?delta:0,behavior:"smooth"});}return}
 }
 if(page==="store"&&active.classList.contains("card")&&$("#gameOptions").hidden&&$("#orderPanel").hidden){
   const grid=active.parentElement,columns=getComputedStyle(grid).gridTemplateColumns.split(" ").length;
   const idx=Array.prototype.indexOf.call(grid.children,active),target=grid.children[idx+dir[0]+dir[1]*columns];
   if(target){e.preventDefault();target.focus({preventScroll:true});target.scrollIntoView({block:"nearest",inline:"nearest"});return}
 }
 const box=active.getBoundingClientRect();let best,score=Infinity;
 const scope=!$("#cinema").hidden?$("#cinema"):!$("#gameOptions").hidden?$("#gameOptions"):!$("#orderPanel").hidden?$("#orderPanel"):$("#center").hidden?document:$("#center");
 scope.querySelectorAll("button,input,[tabindex]").forEach(b=>{if(b===active||!b.offsetWidth)return;const r=b.getBoundingClientRect(),dx=r.x+r.width/2-box.x-box.width/2,dy=r.y+r.height/2-box.y-box.height/2;
 const along=dx*dir[0]+dy*dir[1],cross=Math.abs(dx*dir[1]-dy*dir[0]);if(along<=2||cross>along*2.4)return;const cost=along+cross*5;if(cost<score){best=b;score=cost}});
 if(best){e.preventDefault();best.focus()}
});
showHome();
