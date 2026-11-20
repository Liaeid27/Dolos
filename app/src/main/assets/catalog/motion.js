"use strict";
(()=>{
 const canvas=document.querySelector("canvas"),ctx=canvas.getContext("2d");
 function frame(ms){
  
  const scale=Math.min(devicePixelRatio||1,960/Math.max(innerWidth,innerHeight));const w=Math.max(1,Math.round(innerWidth*scale)),h=Math.max(1,Math.round(innerHeight*scale));
  if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}
  const t=ms/1000;ctx.clearRect(0,0,w,h);
  for(let band=0;band<2;band++){
   const gold=band===1;const grad=ctx.createLinearGradient(0,0,w,h*.3);
   for(const [v,color] of (gold?[[0,"#a6936800"],[.42,"#aa8f611f"],[.73,"#dfb879aa"],[1,"#d7e2fc12"]]:[[0,"#72a1d20a"],[.4,"#7699d33b"],[.7,"#c4e6ffcb"],[1,"#8cd9f152"]]))grad.addColorStop(v,color);
   ctx.strokeStyle=grad;
   for(let n=0;n<45;n++){
    const k=n/44;ctx.globalAlpha=.15+.68*Math.pow(Math.sin(k*Math.PI),2);ctx.lineWidth=(n%9===0?1.3:.7)*w/1000;
    ctx.beginPath();for(let j=0;j<=68;j++){
     const x=j/68;const y=.51+.22*Math.sin(x*5.5-1.1+t*.105+band*.5)+.085*Math.sin(x*11.5+t*.13)+
         (k-.5)*(.085+.21*Math.sin(x*6.4+t*.17+band))+(gold?.032:0);
     if(j)ctx.lineTo(x*w,y*h);else ctx.moveTo(x*w,y*h)
    }ctx.stroke()
   }
  }
  ctx.globalAlpha=1;
  for(let n=1;n<72;n++){const x=(n*.618034+t*(.0015+n%4*.0003))%1,y=(n*.38983-t*.003+20)%1;ctx.fillStyle="rgba(222,227,244,"+(.08+.2*(1+Math.sin(n+t*.4))/2)+")";ctx.beginPath();ctx.arc(x*w,y*h,.4+n%3*.38,0,2*Math.PI);ctx.fill()}
 }
 let scheduled=false;
 function redraw(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;frame(0)})}
 redraw();addEventListener("resize",redraw);
})();
