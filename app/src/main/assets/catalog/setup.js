const q=s=>document.querySelector(s);
const pages=[
 ["Willkommen bei Dolos","Mit dem Steuerkreuz bewegen. Mit der Bestätigungstaste auswählen. Alle Schritte findest du später in den Einstellungen wieder."],
 ["Controller verbinden","Halte die Kopplungstaste deines Controllers gedrückt und wähle ihn in den Bluetooth-Einstellungen des Fernsehers. Deine Fernbedienung funktioniert ebenfalls."],
 ["PC vorbereiten","PC und TV ins gleiche Heimnetz bringen. Starte am PC einmal Einrichten.cmd als Administrator. Öffne danach Dolos-PC als normaler Benutzer und wähle „TV-Verwaltung koppeln“."],
 ["Konsole koppeln","Nach dem Guide deinen PC auswählen und die Apollo-PIN einmal am PC bestätigen. Dann unter Einstellungen → PC-Verwaltung das Prüfzeichen vergleichen und den TV-Code eingeben."],
 ["Start und Klang","Wake-on-LAN benötigt im PC eine aktivierte Weckfunktion. Beim ersten Test den PC im Energiesparmodus lassen."],
 ["Deine Spiele","Öffne den Dolos Store und wähle „Zu Spielen hinzufügen“. Unter Kontrollzentrum → Downloads siehst du Aufträge und Fortschritt."]];
let step=0;const prefs=JSON.parse(DolosSetup.options());
function checkbox(key,label){const l=document.createElement("label"),c=document.createElement("input");c.type="checkbox";c.checked=prefs[key];c.onchange=()=>{prefs[key]=c.checked;DolosSetup.option(key,c.checked)};l.append(c,document.createTextNode(" "+label));q("#choices").append(l)}
function draw(){q("h1").textContent=pages[step][0];q("p").textContent=pages[step][1];q(".steps").innerHTML=pages.map((_,i)=>'<i class="'+(i<=step?"done":"")+'"></i>').join("");q("#choices").replaceChildren();
 if(step===1){const b=document.createElement("button");b.textContent="Bluetooth öffnen";b.onclick=()=>DolosSetup.bluetooth();q("#choices").append(b)}
 if(step===4){checkbox("wake","PC beim Öffnen wecken");checkbox("sound","Systemklänge");checkbox("music","Menümusik")}
 q("#prev").hidden=!step;q("#skip").hidden=step===pages.length-1;q("#next").textContent=step===pages.length-1?"Einrichtung abschließen":"Weiter";const g=q(".guide");g.classList.remove("enter");void g.offsetWidth;g.classList.add("enter");q("#next").focus()}
function next(){if(step===pages.length-1)DolosSetup.finishGuide();else{step++;draw()}}
q("#next").onclick=next;q("#prev").onclick=()=>{step--;draw()};q("#skip").onclick=next;q("#end").onclick=()=>DolosSetup.finishGuide();
document.onkeydown=e=>{if(["Escape","Backspace"].includes(e.key)){step?(step--,draw()):DolosSetup.finishGuide();e.preventDefault()}};
document.addEventListener("keydown",e=>{
 if(!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown"].includes(e.key))return;
 const choices=[...document.querySelectorAll("button,input")].filter(b=>b.getClientRects().length);
 const i=choices.indexOf(document.activeElement),delta=["ArrowLeft","ArrowUp"].includes(e.key)?-1:1;
 choices[Math.max(0,Math.min(choices.length-1,i+delta))]?.focus();e.preventDefault()
});
draw();
