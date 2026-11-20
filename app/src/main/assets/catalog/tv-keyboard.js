"use strict";
(()=>{
 const board=document.createElement("dialog");
 board.style.cssText="border:1px solid #8191a6;border-radius:18px;background:#182333;color:white;padding:1em;width:min(36em,90vw);box-shadow:0 1em 4em #0008";
 const styling=document.createElement("style");
 styling.textContent=".dolosKeys button{border-radius:.4em;background:#2a3545;color:#f0f3f8;font-size:.93em}.dolosKeys button:focus{outline:2px solid white;background:#e9edf3;color:#121c2a}.dolosKeys::backdrop{background:#04081166}";
 document.head.append(styling);board.className="dolosKeys";
 const preview=document.createElement("p"),keys=document.createElement("div");board.append(preview,keys);
 keys.style.cssText="display:grid;grid-template-columns:repeat(10,1fr);gap:.22em";
 document.body.append(board);let target,upper=false;
 function close(){if(!board.hasAttribute("open"))return false;if(board.close)board.close();else board.removeAttribute("open");target.focus();return true}
 function draw(){
   keys.replaceChildren();let chars=(upper?"1234567890QWERTZUIOPASDFGHJKLÖYXCVBNMÄÜß":"1234567890qwertzuiopasdfghjklöyxcvbnmäüß").split("");
   for(const key of [...chars,"⇧","Leerzeichen","Löschen","Fertig"]){
     const b=document.createElement("button");b.textContent=key;b.type="button";b.style.minHeight="2.4em";
     if(key.length>1)b.style.gridColumn="span 2";
     b.onclick=()=>{if(key==="Fertig"){close();return}if(key==="⇧"){upper=!upper;draw();keys.children[40].focus();return}
       target.value=key==="Löschen"?[...target.value].slice(0,-1).join(""):target.value+(key==="Leerzeichen"?" ":key);
       target.dispatchEvent(new Event("input",{bubbles:true}));preview.textContent=target.value||"Suchen";b.focus()};
     keys.append(b);
   }
 }
 window.openTvKeyboard=el=>{
   if(!el||el.tagName!=="INPUT"||board.hasAttribute("open"))return;
   target=el;preview.textContent=el.value||"Suchen";draw();if(board.showModal)board.showModal();else{board.setAttribute("open","");board.style.cssText+=";position:fixed;inset:10% auto auto 10%;z-index:100"}keys.children[10].focus();
 };
 window.closeTvKeyboard=close;
 document.addEventListener("click",event=>{if(window.tvInput&&event.target.matches("input[type=search],input[type=text],input:not([type])"))openTvKeyboard(event.target)},true);
 document.addEventListener("keydown",event=>{
   if(!board.hasAttribute("open"))return;
   const buttons=[...keys.children],b=document.activeElement,i=buttons.indexOf(b);
   if(event.key==="Escape"||event.key==="Backspace"){event.preventDefault();event.stopImmediatePropagation();close();return}
   const dir={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];if(!dir||i<0)return;
   event.preventDefault();event.stopImmediatePropagation();const rect=b.getBoundingClientRect();
   const center=r=>[r.left+r.width/2,r.top+r.height/2];const [x,y]=center(rect);let best=null,cost=Infinity;
   for(const other of buttons){let [dx,dy]=center(other.getBoundingClientRect());dx-=x;dy-=y;const forward=dx*dir[0]+dy*dir[1],across=Math.abs(dx*dir[1]-dy*dir[0]);if(forward>1&&forward+4*across<cost){cost=forward+4*across;best=other}}
   best?.focus();
 },true);
})();
