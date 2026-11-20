"use strict";
function remoteSteamId(game){
 const id=game?.steamId||((typeof controlData!=="undefined"&&controlData.storeLinks?.[game?.name])||"");
 return /^\d{1,10}$/.test(id)?id:"";
}
function remoteArt(box,game){
 box.replaceChildren();
 const label=document.createElement("span");label.className="placeholder";label.textContent=game.name;box.append(label);
 const id=remoteSteamId(game),im=new Image(),tried=new Set();
 const base=id?"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/"+id+"/":"";
 const candidates=[pcArt(game,"cover"),game.hasCover===false&&base?base+"library_600x900.jpg":game.art,base&&base+"library_600x900.jpg",game.art].filter(Boolean);
 let metadataRequested=false;
 im.alt="";im.loading=box.className==="art"?"lazy":"eager";
 async function next(){
   let src=candidates.find(value=>!tried.has(value));
   if(!src&&id&&!metadataRequested){
      metadataRequested=true;const details=await detailsFor(game);
      if(im.parentNode!==box)return;
      src=details?.header;
   }
   if(src&&!tried.has(src)){tried.add(src);im.src=src;return}
   im.remove();classifyCover(game,null);
 }
 im.onerror=next;
 im.onload=()=>{classifyCover(game,im);
    if((game.hasCover===false||coverFlags.get(game.id)===false)&&im.src===game.art&&id&&!metadataRequested){next();return}
    label.remove();
 };
 box.prepend(im);next();
}

function remoteWall(game){
 const key=game?.id||"";
 if(key===lastWall)return;
 lastWall=key;const token=++wallToken,walls=document.querySelectorAll(".wall");
 function clear(){walls.forEach(w=>w.classList.remove("lit"));document.body.classList.remove("art")}
 if(!key){clear();return}
 const img=new Image(),tried=new Set(),id=remoteSteamId(game);
 const candidates=[pcArt(game,"hero"),game.hero,id&&"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/"+id+"/library_hero.jpg"].filter(Boolean);
 let requested=false;
 async function next(){
   if(token!==wallToken)return;
   let url=candidates.find(v=>!tried.has(v));
   if(!url&&id&&!requested){
      requested=true;const details=await detailsFor(game);
      if(token!==wallToken)return;
      candidates.push(details?.shots?.[0]?.full,details?.backdrop,details?.header);
      url=candidates.find(v=>v&&!tried.has(v));
   }
   url=url||(!tried.has(game.art)&&game.art);
   if(!url){lastWall=null;clear();return}
   tried.add(url);img.src=url;
 }
 img.onerror=next;img.onload=()=>{
    if(token!==wallToken)return;
    const n=1-wallIndex;walls[n].style.backgroundImage="url("+JSON.stringify(img.src)+")";
    walls[n].classList.add("lit");walls[wallIndex].classList.remove("lit");wallIndex=n;document.body.classList.add("art");
 };
 next();
}
