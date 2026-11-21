"use strict";
let controlData={},measurement=null,managePage="",lastRows="";
let trophyData=null;
function trophyResult(key,data){if(page==="manage"&&managePage==="Trophäen"&&product?.steamId===key){trophyData=data;lastRows="";drawManage()}}
function manage(title){
 managePage=title;screen("manage");background(null);$("#manage").hidden=false;$("#manage h1").textContent=title;lastRows="";drawManage();
 if(title!=="Einstellungen" && title!=="Trophäen")native(title==="Downloads"?"transfers":"status");
}
function controlState(data){
 if(data.measurement)measurement=data.measurement;
 const previousAtlas=atlasRev;
 if(atlasHost&&data.pcArtwork){applyAtlas(data.coverAtlas);try{localStorage.setItem("dolos.artwork."+atlasHost,JSON.stringify({art:data.pcArtwork,atlas:data.coverAtlas}))}catch(e){}}
 const newArt=data.pcArtwork&&Object.keys(data.pcArtwork).length&&!controlData.pcArtwork;
 if(data.error&&page==="manage"&&managePage==="Downloads"&&controlData.apps){controlData={...controlData,downloadError:data.error};drawManage();return}
 controlData=data;renderSaveInfo();
 if(newArt||previousAtlas!==atlasRev){
    if(page==="home"){for(const b of $("#rail").children){const g=items.find(i=>i.id===b.dataset.id);if(pcArt(g,"cover"))art(b,g)}lastWall=null;background(current())}
    else if(page==="store")showStore(false);
    else if(page==="product"){lastWall=null;background(product)}
 }
 if(data.covers){let changed=false;for(const g of items){const value=data.covers[g.steamId||g.name];if(typeof value==="boolean"&&g.hasCover!==value){g.hasCover=value;changed=true}}
  if(changed&&page==="store"){const id=document.activeElement?.dataset.id;showStore(id||false)}}

 let stateChanged=false;
 if(data.apps)for(const g of items){
   const before=g.state;
   if(!g.steamId||g.state==="shortcut")continue;
   g.originalState=g.originalState||g.state;
   const row=data.apps[g.steamId];g.state=row?.state==="installed"?"installed":g.originalState==="installed"?"cached":g.originalState;
   g.transfer=row&&["downloading","staging","waiting","paused"].includes(row.state)?row:null;
   if(g.transfer)g.state="cached";
   stateChanged=stateChanged||before!==g.state;g.removable=g.state==="installed";
 }
 if(page==="store"){if(stateChanged&&(filter===1||filter===2))showStore(document.activeElement?.dataset.id||false);else refreshStoreCards()}
 if(page==="manage")drawManage()
}
function bytes(n){return n>=1073741824?(n/1073741824).toFixed(1)+" GB":Math.round((n||0)/1048576)+" MB"}
function drawManage(){
 const live=$("#manager"),downloads=managePage==="Downloads",old=document.activeElement?.dataset.key;
 const serial=JSON.stringify(downloads?[managePage,controlData.queue,controlData.apps,controlData.prompt,controlData.paused,controlData.downloadAction,controlData.downloadError,controlData.error,controlData.paired]:[managePage,controlData,measurement]);
 if(serial===lastRows)return;
 lastRows=serial;
 const block=downloads?document.createElement("div"):live;
 if(!downloads)block.replaceChildren();
 function info(title,text){const box=document.createElement("section"),h=document.createElement("h3"),p=document.createElement("p");h.textContent=title;p.textContent=text;box.append(h,p);block.append(box);return box}
 function act(name,fn,parent=block,key=name){const b=button(parent,name,fn);b.dataset.key=key;return b}
 if(managePage==="Einstellungen"){
  act("Darstellung",()=>native("studio","appearance"));act("Systemupdate",()=>native("studio","updates"));
  act("Speicher",()=>manage("Speicher"));act("Verbindung",()=>manage("Verbindung"));act("Bild und Streaming",()=>native("studio","video"));act("Ton",()=>native("studio","audio"));act("Bluetooth-Geräte",()=>native("bluetooth"));act("Controller und Eingabe",()=>native("studio","controller"));act("Weitere Optionen",()=>native("studio","advanced"));act("PC-Verwaltung koppeln",()=>native("pair"));
  act("Einrichtungsassistent",()=>native("setup"));act("Profil wechseln",()=>native("profile"));act("Energie",()=>native("power"))
 }else{
  if(controlData.error||!controlData.paired){
   info("PC-Verwaltung",controlData.error||"Verbindung wird geprüft …");act("Verbindung aktualisieren",()=>native("status"));act("PC wecken",()=>native("wake"));act("TV koppeln",()=>native("pair"))
  }else if(managePage==="Trophäen"){
   const rows=trophyData?.rows||[];info(product.name,trophyData?.notice||(trophyData?rows.filter(r=>r.done).length+" von "+rows.length+" freigeschaltet":"Wird geladen …"));
   for(const r of rows){const box=info(r.name,r.done?"Freigeschaltet":"Noch gesperrt");box.tabIndex=0}
  }else if(managePage==="Speicher"){
   for(const disk of controlData.disks||[]){const row=info("Laufwerk "+disk.name,bytes(disk.free)+" frei von "+bytes(disk.total));const m=document.createElement("progress");m.max=disk.total;m.value=disk.total-disk.free;row.append(m);
    for(const game of Object.values(controlData.apps||{}).filter(g=>g.drive===disk.drive&&g.state==="installed").sort((a,b)=>b.size-a.size)){
      const line=document.createElement("p");line.textContent=game.name+"　"+bytes(game.size);row.append(line)
    }}
   act("Installierte Spiele verwalten",()=>{showStore();document.querySelectorAll("#filters button")[1]?.click()})
  }else if(managePage==="Verbindung"){
   info("PC erreichbar","Die verschlüsselte Heimnetzverbindung ist aktiv.");
   if(measurement){
    const m=measurement;
    info("Antwortzeit zum PC",m.received?m.mean+" ms im Mittel · "+m.spread+" ms Spannweite · "+m.received+" von 5 Antworten":"Keine Antwort erhalten");
    info("Für dein Spiel",m.received<5||m.spread>35?"Die Antworten schwanken. Verbinde den PC per Netzwerkkabel. Ist der Fernseher im WLAN, versuche 5 GHz in der Nähe des Routers.":"Prüfe im Spiel die Stream-Statistik. Bei sichtbarem Ruckeln zuerst die Bitrate etwas senken und erneut spielen.")
   }
   act("Jetzt messen",()=>native("measure"));act("Streaming einstellen",()=>native("settings"))
  }else{
   const list=controlData.queue||[],apps=controlData.apps||{},ids=new Set(list.map(x=>x.id));
   const extra=Object.values(apps).filter(g=>["downloading","staging","paused","waiting"].includes(g.state)&&!ids.has(g.id));
   const order={downloading:0,staging:0,waiting:1,paused:2};
   extra.sort((a,b)=>order[a.state]-order[b.state]||(a.scheduled||0)-(b.scheduled||0));
   const command=controlData.downloadAction;
   if(controlData.downloadError||command?.error||command?.pending){
    info("Steam",controlData.downloadError||command.error||"Steam verarbeitet den Auftrag …").dataset.key="notice"
   }
   if(!list.length&&!extra.length)info("Keine aktiven Downloads","Installationen aus dem Store erscheinen hier.");
   for(const job of [...list,...extra]){
    const g=apps[job.id]||{},s=job.held?"Angehalten":g.phase||({paused:"Von Steam pausiert",staging:"Dateien werden vorbereitet",downloading:"Wird heruntergeladen",waiting:"Wartet auf Steam"})[g.state]||(job.error||(!job.sent?"In Warteschlange":job.direct?"Installationsauftrag an Steam gesendet":job.confirmed?"Installation bestätigt · Steam startet den Download":"Installationsdialog wird geprüft"));
    const row=info(job.name,s+(g.total>0&&g.state!=="installed"?" · "+Math.min(100,Math.floor(100*g.done/g.total))+" % · "+bytes(g.done)+" von "+bytes(g.total):""));
    row.dataset.key="job"+job.id;
    if((g.state&&g.state!=="installed"||ids.has(job.id)&&!job.sent&&job.action==="install")&&controlData.hostBuild>=331){
     if(!["downloading","staging"].includes(g.state))act(g.state==="paused"?"Fortsetzen":"Jetzt herunterladen",()=>native("downloadfirst",job.id),row,"first"+job.id);
     if(g.state!=="paused"&&!job.held)act("Anhalten",()=>native("downloadpause",job.id),row,"hold"+job.id);
     act("Abbrechen",()=>confirmTransfer(job.id,job.name),row,"stop"+job.id);
    }
    if(g.total>0&&g.state!=="installed"){const meter=document.createElement("progress");meter.max=g.total;meter.value=g.done;row.append(meter)}
    if(job.sentAt && Date.now()/1000-job.sentAt>40 && !controlData.prompt?.id && !["staging","downloading","paused"].includes(g.state)){
     const note=document.createElement("p");note.textContent=job.direct?"Steam hat den Download noch nicht begonnen. Prüfe den verfügbaren Speicher und die Steam-Verbindung.":"Steam hat noch keinen vom TV bedienbaren Dialog gemeldet.";row.append(note);if(job.action==="install")act("Installation erneut anfordern",()=>native("retry",job.id),row,"retry"+job.id)
    }
    const prompt=controlData.prompt;
    if(prompt?.id===job.id){const t=document.createElement("p");t.textContent=prompt.text;row.append(t);
      act(prompt.confirm,()=>native("confirm",job.id),row,"confirm"+job.id);act("Abbrechen",()=>native("cancel",job.id),row,"cancel"+job.id)}
    if(controlData.hostBuild<331&&ids.has(job.id)&&!job.sent)act("Auftrag entfernen",()=>native("dismiss",job.id),row,"dismiss"+job.id);
    if(job.sent&&!prompt?.id&&!["staging","downloading"].includes(g.state))act("Auftrag aus Liste nehmen",()=>native("dismiss",job.id),row,"dismiss"+job.id)
   }
   act(controlData.paused?"Warteschlange fortsetzen":"Neue Aufträge anhalten",()=>native(controlData.paused?"resume":"pause"))
  }
 }
 act("Zurück",showHome);
 if(downloads){
  const active=document.activeElement,inside=live.contains(active),scroller=$("#manage"),top=scroller.scrollTop;
  syncDownloads(live,block);
  if(inside&&!active.isConnected){
   const next=[...live.querySelectorAll("button")].find(b=>b.dataset.key===old)||live.querySelector("button");
   next?.focus({preventScroll:true});scroller.scrollTop=top;
  }else if(!inside&&!live.dataset.downloads){live.querySelector("button")?.focus({preventScroll:true})}
  live.dataset.downloads="1";return;
 }
 delete live.dataset.downloads;
 const focus=[...block.querySelectorAll("button")].find(b=>b.dataset.key===old)||block.querySelector("button");if(focus)focus.focus()
}
function syncDownloads(parent,source){
 const key=(n,i)=>n.dataset.key||n.tagName+i;
 const existing=new Map(Array.from(parent.children,(n,i)=>[key(n,i),n]));
 Array.from(source.children).forEach((next,i)=>{
  const id=key(next,i),current=existing.get(id);
  if(!current||current.tagName!==next.tagName){parent.insertBefore(next,parent.children[i]||null);return}
  existing.delete(id);
  if(parent.children[i]!==current)parent.insertBefore(current,parent.children[i]||null);
  if(next.tagName==="SECTION")syncDownloads(current,next);
  else if(next.tagName==="PROGRESS"){if(current.max!==next.max)current.max=next.max;if(current.value!==next.value)current.value=next.value}
  else {if(current.textContent!==next.textContent)current.textContent=next.textContent;if(next.onclick)current.onclick=next.onclick}
 });
 for(const unused of existing.values())unused.remove()
}
function confirmTransfer(id,name){
 optionFocus=document.activeElement;const box=$(".gameSheet");box.replaceChildren();
 const title=document.createElement("h2");title.textContent=name;box.append(title);
 button(box,"Weiter herunterladen",closeOptions);
 button(box,"Download abbrechen",()=>{closeOptions();native("downloadcancel",id)});
 $("#gameOptions").hidden=false;box.querySelector("button").focus()
}
setInterval(()=>{if(!document.hidden&&page==="manage"&&!["Trophäen","Einstellungen"].includes(managePage))native(managePage==="Downloads"?"transfers":"status")},5000);

let saveScope="";
function renderSaveInfo(){
 const g=page==="product"?product:current();
 const slots=saveScope&&g?.steamId?(controlData.saveTimes?.[g.steamId]||[]):[];
 const key="dolos.save."+saveScope+"."+g?.steamId;
 const saved=slots.length===1?slots[0]:slots.find(s=>s.slot===localStorage.getItem(key));
 let label="";
 if(saved){
  const minutes=Math.floor(saved.seconds/60),hours=Math.floor(minutes/60);
  label="Spielstand "+(1+Number(saved.slot.slice(4)))+"  ·  "+(hours?hours+" Std. ":"")+(minutes%60)+" Min.";
 }
 for(const el of [$("#homeSave"),$("#productSave")]){el.hidden=!label||(el.id==="homeSave"&&!homeDetails.time);el.textContent=label}
 const choose=$("#slotChoice");choose.hidden=slots.length<2;
 choose.onclick=()=>{
  stopMedia();optionFocus=choose;
  const box=$(".gameSheet");box.replaceChildren();
  const title=document.createElement("h2");title.textContent="Spielstand für die Zeitanzeige";box.append(title);
  for(const slot of slots)button(box,"Spielstand "+(1+Number(slot.slot.slice(4))),()=>{localStorage.setItem(key,slot.slot);closeOptions();renderSaveInfo()});
  $("#gameOptions").hidden=false;box.querySelector("button").focus()
 };
}
