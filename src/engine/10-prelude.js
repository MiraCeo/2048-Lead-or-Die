// ==== 10-prelude ====
// 来源: main.script.js 第 1–13 行（原样搬移，未改一字符）
// IIFE 头、'use strict'、DOM/常量、全局状态、工具函数
(()=>{'use strict';
const $=id=>document.getElementById(id),canvas=$('canvas'),ctx=canvas.getContext('2d'),N=100,V=25,C=32,X=30,Y=43,KEY='core-expedition-v10';const dirs={up:[-1,0],down:[1,0],left:[0,-1],right:[0,1]},copy=q=>({...q,g:q.g.map(t=>t?{...t}:null),logs:q.logs.slice()}),lvl=n=>Math.round(Math.log2(n));let s,history=[],mode='main',selected=null,preview=null,effects=[],drag=null;
function neighbor(i,d){const [dr,dc]=dirs[d],r=Math.floor(i/N)+dr,c=i%N+dc;return r>=0&&r<N&&c>=0&&c<N?r*N+c:-1;}
function rand(q){q.seed=(Math.imul(q.seed,1664525)+1013904223)>>>0;return q.seed/4294967296;}
function log(q,t){q.logs.unshift(t);q.logs=q.logs.slice(0,30);}
function cores(q,side){return q.g.filter(t=>t?.core&&(!side||t.side===side));}
function coreIndex(q,id=q.active){return q.g.findIndex(t=>t?.core&&t.id===id);}
const digitPalette=['#233d2a','#185227','#006064','#17498d','#573189','#81376d','#9b302d','#87400c','#72550a','#415d12','#684208','#22596b'];
function digitColor(n){return digitPalette[(lvl(n)-1)%digitPalette.length];}
function fmt(n){return n<1000000?String(n):n.toExponential(1);}
// Keep the separate guide encoded, so preview wrappers never parse nested document tags.
const guideHTML=new TextDecoder('utf-8').decode(Uint8Array.from(atob('__GUIDE_B64__'),c=>c.charCodeAt(0)));
const kindName={squad:'编队',fighter:'敌机',bunker:'碉堡',collector:'采集机'};
