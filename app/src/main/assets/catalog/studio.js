"use strict";
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const sources=["Alle Quellen","Dolos","Steam Deck Repo","VidSwap"], types=["Alle Animationen","Start","Abschalten"];
const builtin=[["dolos","Original und Abguss"],["galerie","Skulpturengalerie"],["helm","Flügelhelm"],["portikus","Säulengang"],["signet","Siegel"],["stich","Kupferstich"],["maske","Astrolabium"],["orbit","Orbit"]].flatMap(([id,title])=>["on","off"].map(mode=>({id,title,mode,source:"Dolos",author:"Dolos",image:"still_"+id+"_"+mode+".jpg"})));
builtin.push({id:"aster",title:"ASTER · Erster Auftakt",mode:"on",source:"Dolos",author:"Dolos",image:""});
const streamPages=["video","audio","controller","advanced"];
const labels={homeinfo:"Startbildschirm",system:"Konsole und Verbindung",appearance:"Darstellung",library:"Start und Abschalten",themes:"Erscheinungsbild",updates:"Systemupdate",video:"Bild und Streaming",audio:"Ton",controller:"Controller und Eingabe",advanced:"Weitere Optionen"};
const compact=matchMedia("(max-aspect-ratio:1/1)");
let indexView=false;
function mobileIndex(){
 $(".crumb").textContent="Dolos";indexView=compact.matches;document.body.classList.toggle("indexView",indexView);
 document.querySelector("nav .active")?.focus({preventScroll:true});scrollTo(0,0)
}
const strokes={
 appearance:'<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4"/>',
 video:'<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="m10 9 5 3-5 3z"/>',
 audio:'<path d="M4 10h4l5-4v12l-5-4H4zm12-2q5 4 0 8m2-11q8 7 0 14"/>',
 controller:'<path d="M7 7h10c3 0 4 5 4 10 0 3-3 2-6-2H9c-3 4-6 5-6 2 0-5 1-10 4-10zM6 11h5m-2.5-2.5v5"/><circle cx="16.5" cy="10" r=".8"/><circle cx="18.5" cy="12.5" r=".8"/>',
 advanced:'<path d="M3 6h5m4 0h9M3 12h10m4 0h4M3 18h3m4 0h11"/><circle cx="10" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>',
 system:'<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M9 21h6m-3-4v4m4-13h2"/>',
 updates:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v4h16v-4"/>'};
$$("[data-page]").forEach(b=>{const t=document.createElement("span");t.textContent=b.textContent;b.textContent="";b.insertAdjacentHTML("afterbegin",'<svg viewBox="0 0 24 24" aria-hidden="true">'+strokes[b.dataset.page]+'</svg>');b.append(t)});
function time(){document.querySelector(".clock").textContent=new Date().toLocaleTimeString("de-DE",{hour:"2-digit",minute:"2-digit"})}time();setInterval(time,30000);
let options={},editing=null;
let state={theme:"normal",on:"dolos",off:"dolos",files:[]},page="library",tab="saved",from=0,src=0,kind=0,selected=null,rows=[],loaded=false,loading=false,started=false,errors=[],lastKey="";
const link=(action,row={})=>{location.href="studio://"+action+"/"+encodeURIComponent(JSON.stringify(row))};
function notice(t){$("#status").textContent=t}
function available(v){$("#install").hidden=!v;$("#install").textContent="Build "+v+" installieren"}
function studioState(data){
 state=data;$$("[data-info]").forEach(b=>{const key=b.dataset.info,on=!!data[key];if(key==="trailerAudio")b.hidden=!data.tvEdition;b.textContent=b.textContent.split(" · ")[0]+" · "+(on?"Ein":"Aus");b.setAttribute("aria-pressed",String(on));b.onclick=()=>link("homeinfo",{id:key})});$(".route").hidden=!data.route;$(".route").textContent="Letzter Spielstream · "+(data.route||"");$$("[data-console]").forEach(b=>b.hidden=b.dataset.console!=="setup"&&!data.connectedMenu);document.body.classList.toggle("enhanced",data.theme==="enhanced");$("#version").textContent="Installiert · Build "+data.build;
 if(!started){started=true;openPage(labels[data.section]?data.section:"appearance");document.querySelector("nav .active").focus();if(compact.matches&&data.section==="appearance")mobileIndex()}
 else if(selected)detail(selected);else if(page==="library")draw();
 $$("[data-theme]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.theme===state.theme)));
}
function openPage(name){
 indexView=false;document.body.classList.remove("indexView");$(".crumb").textContent=compact.matches?"Einstellungen":"Dolos";page=name;selected=null;$("#filterChoices").hidden=true;notice("");editing=null;for(const id of ["system","appearance","library","themes","homeinfo","updates","details","streamPage"])$("#"+id).hidden=id!==(streamPages.includes(name)?"streamPage":name);
 if(streamPages.includes(name)){renderOptions();link("stream")}
 $$("nav [data-page]").forEach(b=>b.classList.toggle("active",b.dataset.page===(["library","themes","homeinfo"].includes(name)?"appearance":name)));
 $("#title").textContent=labels[name];if(name==="library")draw();
}
function saved(r){return r.source==="Dolos"||state.files.some(f=>f.id===r.id)}
function kindName(r){return r.mode==="off"?"Abschalten":"Start"}
function isActive(r){return state[r.mode]===r.id}
function draw(){
 const pool=tab==="saved"?[...builtin,...state.files]:[...rows,...builtin];
 const query=$("#search").value.trim().toLocaleLowerCase("de");
 const result=pool.filter(r=>(!src||sources[src]===r.source)&&(!kind||(kind===1?"on":"off")===r.mode)&&(!query||(r.title+" "+r.author).toLocaleLowerCase("de").includes(query)));
 if(from>=result.length)from=0;
 $("#source").textContent=sources[src];$("#type").textContent=types[kind];$$("[data-tab]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.tab===tab)));
 $("#count").textContent=(loading&&tab==="browse"?"Quellen werden geladen · ":"")+result.length+" Animationen"+(result.length?" · "+(from+1)+"–"+Math.min(from+12,result.length):"");
 const list=$("#list");list.replaceChildren();
 for(const r of result.slice(from,from+12)){
  const b=document.createElement("button");b.className="card";b.dataset.key=r.id+r.mode;
  const fallback=()=>{const t=document.createElement("span");t.className="thumb";t.textContent="▷";return t};
  if(r.image){const im=new Image();im.alt="";im.loading="lazy";im.src=r.image;im.onerror=()=>im.replaceWith(fallback());b.append(im)}else b.append(fallback());
  const title=document.createElement("strong"),sub=document.createElement("small");title.textContent=r.title;sub.textContent=[kindName(r),r.source,isActive(r)?"Aktiv":""].filter(Boolean).join(" · ");b.append(title,sub);b.onclick=()=>{lastKey=b.dataset.key;detail(r);$("#actions button").focus()};list.append(b)
 }
 $("#prev").hidden=!from;$("#next").hidden=from+12>=result.length;
 if(tab==="browse"&&errors.length)notice("Quelle nicht erreichbar: "+errors.join(", ")+". Zum erneuten Laden Entdecken wählen.");
}
async function discover(){
 if(loading||(loaded&&!errors.length))return;loading=true;errors=[];draw();
 const result=await Promise.allSettled([fetch("https://studio.invalid/deck").then(r=>r.json()).then(d=>d.posts.filter(x=>["boot_video","suspend_video"].includes(x.type)&&/^https:\/\/cdn\.steamdeckrepo\.com\/videos\/[\w.-]+\.webm$/.test(x.video)).map(x=>({id:"deck_"+x.id,title:x.title,mode:x.type==="boot_video"?"on":"off",author:x.user?.steam_name||"",source:sources[2],url:x.video,image:/^https:\/\/cdn\.steamdeckrepo\.com\/thumbnails\//.test(x.thumbnail)?x.thumbnail:""}))),
 fetch("https://studio.invalid/swap").then(r=>r.json()).then(d=>d.tree.filter(x=>/^vidswap\/vids\/[\w-]+\.webm$/i.test(x.path)).map(x=>{const name=x.path.split("/").pop().slice(0,-5);return {id:"swap_"+name,title:name.replace(/([a-z])([A-Z])/g,"$1 $2"),mode:"on",author:"AutoMcG · VidSwap",source:sources[3],url:"https://raw.githubusercontent.com/AutoMcG/steamdeck_tools/"+d.sha+"/"+x.path}}))]);
 rows=result.flatMap((r,i)=>{if(r.status==="fulfilled")return r.value;errors.push(sources[i+2]);return rows.filter(x=>x.source===sources[i+2])});
 loaded=true;loading=false;if(page==="library"&&!selected)draw()
}
function detail(r){
 selected=r;$("#library").hidden=true;$("#details").hidden=false;$("#art").style.backgroundImage=r.image?'url("'+r.image+'")':"linear-gradient(125deg,#394966,#121a32)";
 $("#filmTitle").textContent=r.title;$("#credit").textContent=[r.source,r.author!==r.source?r.author:"",kindName(r)].filter(Boolean).join(" · ");const actions=$("#actions");actions.replaceChildren();
 function add(label,action){const b=document.createElement("button");b.textContent=label;b.onclick=()=>link(action,r);actions.append(b)}
 add("Vorschau","preview");if(!saved(r))add("Herunterladen","download");else{if(!isActive(r))add("Für "+kindName(r)+" anwenden","apply");else{const s=document.createElement("span");s.textContent="✓ Aktiv";actions.append(s)}if(r.source!=="Dolos")add("Download entfernen","delete")}
}
function goBack(){if(window.closeTvKeyboard?.())return;if(indexView){link("close");return}if(!$("#filterChoices").hidden){$("#filterChoices").hidden=true;$("#source").focus();return}if(editing){editing=null;renderOptions();return}if(selected){openPage("library");const b=$$(".card").find(b=>b.dataset.key===lastKey);(b||$("#search")).focus()}else if(["library","themes","homeinfo"].includes(page)){openPage("appearance");$("[data-sub]").focus()}else if(compact.matches)mobileIndex();else link("close")}
$("#back").onclick=goBack;$$("[data-page]").forEach(b=>b.onclick=()=>openPage(b.dataset.page));$$("[data-sub]").forEach(b=>b.onclick=()=>{openPage(b.dataset.sub);document.querySelector("main section:not([hidden]) button")?.focus()});
$$("[data-tab]").forEach(b=>b.onclick=()=>{tab=b.dataset.tab;from=0;notice("");draw();if(tab==="browse")discover()});
$("#search").oninput=()=>{from=0;draw()};function filterMenu(isSource){
 const trigger=$(isSource?"#source":"#type"), choices=$("#filterChoices"),names=isSource?sources:types;
 choices.replaceChildren();choices.hidden=false;
 names.forEach((label,i)=>{const b=document.createElement("button");b.textContent=label;b.setAttribute("aria-pressed",String(i===(isSource?src:kind)));b.onclick=()=>{if(isSource)src=i;else kind=i;from=0;choices.hidden=true;draw();trigger.focus()};choices.append(b)});
 choices.querySelector("[aria-pressed=true]").focus()
}
$("#source").onclick=()=>filterMenu(true);$("#type").onclick=()=>filterMenu(false);
for(const [id,step] of [["prev",-12],["next",12]])$("#"+id).onclick=()=>{from+=step;draw();$(".card")?.focus()};
$$("[data-theme]").forEach(b=>b.onclick=()=>link("theme",{id:b.dataset.theme}));$("#check").onclick=()=>link("check");$("#install").onclick=()=>link("install");

document.addEventListener("keydown",e=>{
 if(e.key==="Escape"){e.preventDefault();goBack();return}
 const dir={ArrowRight:[1,0],ArrowLeft:[-1,0],ArrowDown:[0,1],ArrowUp:[0,-1]}[e.key];
 if(!dir||(e.target.tagName==="INPUT"&&dir[0]))return;
 const active=document.activeElement,box=active.getBoundingClientRect();
 let best,score=Infinity;
 for(const b of $$("button,input")){
  if(b===active||b.disabled||!b.offsetWidth)continue;
  const r=b.getBoundingClientRect(),dx=r.x+r.width/2-box.x-box.width/2,dy=r.y+r.height/2-box.y-box.height/2;
  const along=dx*dir[0]+dy*dir[1],cross=Math.abs(dx*dir[1]-dy*dir[0]);
  if(along>2&&cross<=along*2.4&&along+cross*5<score){score=along+cross*5;best=b}
 }
 if(best){e.preventDefault();best.focus()}
});

function streamOptions(model){options=model;if(streamPages.includes(page))renderOptions()}
function displayOption(r){if(r.type==="switch")return r.value?"Ein":"Aus";if(r.type==="list")return r.choices.find(o=>o.id===r.value)?.title||r.value||"";if(r.type==="range")return (r.value/r.divisor).toLocaleString("de-DE")+" "+(r.suffix||"");return ""}
function renderOptions(){
 const list=$("#optionRows"),panel=$("#optionEdit"),old=document.activeElement?.dataset.option;list.hidden=!!editing;panel.hidden=!editing;
 if(editing)return;
 list.replaceChildren();
 for(const r of options[page]||[]){const b=document.createElement("button"),title=document.createElement("strong"),v=document.createElement("small");
 b.dataset.option=r.key;b.disabled=!r.enabled;title.textContent=r.label;v.textContent=displayOption(r);b.append(title,v);list.append(b);
 b.onclick=()=>{if(r.type==="switch"){link("option",{key:r.key,value:!r.value});return}
 editing=r;list.hidden=true;panel.hidden=false;panel.replaceChildren();const title=document.createElement("h2"),help=document.createElement("p");title.textContent=r.label;help.textContent=r.help;panel.append(title,help);
 function save(value){editing=null;link("option",{key:r.key,value});renderOptions();document.querySelector('[data-option="'+r.key+'"]')?.focus()}
 function choice(label,fn){const c=document.createElement("button");c.textContent=label;c.onclick=fn;panel.append(c);return c}
 if(r.type==="list"){for(const v of r.choices){const c=choice(v.title,()=>save(v.id));c.setAttribute("aria-pressed",String(v.id===r.value))}}
 if(r.type==="range"){const input=document.createElement("input"),val=document.createElement("p");input.type="range";input.min=r.min;input.max=r.max;input.step=r.step;input.value=r.value;input.setAttribute("aria-label",r.label);input.oninput=()=>val.textContent=displayOption({...r,value:+input.value});input.oninput();panel.append(input,val);choice("Übernehmen",()=>save(+input.value))}
 if(r.type==="reset")choice("Layout zurücksetzen",()=>save(true));
 choice("Zurück",()=>{editing=null;renderOptions();document.querySelector('[data-option="'+r.key+'"]')?.focus()});(panel.querySelector('[aria-pressed="true"],input')||panel.querySelector("button")).focus()}
 }
 if(old)list.querySelector('[data-option="'+old+'"]')?.focus();
}

$$("[data-console]").forEach(b=>b.onclick=()=>link("consoleAction",{id:b.dataset.console}));

compact.addEventListener?.("change",()=>{if(!compact.matches){indexView=false;document.body.classList.remove("indexView")}});
