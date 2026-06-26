"""Builds wc26_r32_predictions.html (standalone) from opponent_matrix_exact.csv.
Flags via flagcdn.com images (render cross-platform). Run: python build_webpage.py"""
import csv, json, datetime, os
from collections import defaultdict
from itertools import combinations

QUAL = {'France':1,'Argentina':1,'Spain':1,'England':1,'Germany':1,'Brazil':1,'Portugal':1,'Netherlands':1,
'Norway':1,'USA':1,'Colombia':1,'Mexico':1,'Switzerland':1,'Morocco':1,'Japan':1,'Canada':1,
'Egypt':1,'Ecuador':1,'Australia':1,'Sweden':1,'Bosnia':1,"Cote d'Ivoire":1,'South Africa':1,
'Belgium':.9216,'Croatia':.8907,'Ghana':.9996,'Austria':.9036,'Paraguay':.9985,'Algeria':.7465,
'Senegal':.569,'Iran':.55,'South Korea':.5324,'Cabo Verde':.6395,'Congo DR':.4116,'Saudi Arabia':.3459,
'Uruguay':.3641,'New Zealand':.07,'Scotland':.0524,'Iraq':.0028,'Uzbekistan':.002,
'Czechia':0,'Qatar':0,'Haiti':0,'Turkiye':0,'Tunisia':0,'Jordan':0,'Panama':0,'Curacao':0}

# match -> (month, day, hour24, minute, UTC offset, venue) in venue-local time
SCHED_RAW = {73:(6,28,12,0,-7,'Inglewood'),74:(6,29,16,30,-4,'Foxborough'),
75:(6,29,19,0,-6,'Guadalupe'),76:(6,29,12,0,-5,'Houston'),
77:(6,30,17,0,-4,'East Rutherford'),78:(6,30,12,0,-5,'Arlington'),
79:(6,30,19,0,-6,'Mexico City'),80:(7,1,12,0,-4,'Atlanta'),
81:(7,1,17,0,-7,'Santa Clara'),82:(7,1,13,0,-7,'Seattle'),
83:(7,2,19,0,-4,'Toronto'),84:(7,2,12,0,-7,'Inglewood'),
85:(7,2,20,0,-7,'Vancouver'),86:(7,3,18,0,-4,'Miami Gardens'),
87:(7,3,20,30,-5,'Kansas City'),88:(7,3,13,0,-5,'Arlington'),
89:(7,4,17,0,-4,'Philadelphia'),90:(7,4,12,0,-5,'Houston'),
91:(7,5,16,0,-4,'East Rutherford'),92:(7,5,18,0,-6,'Mexico City'),
93:(7,6,14,0,-5,'Arlington'),94:(7,6,17,0,-7,'Seattle'),
95:(7,7,12,0,-4,'Atlanta'),96:(7,7,13,0,-7,'Vancouver'),
97:(7,9,16,0,-4,'Foxborough'),98:(7,10,12,0,-7,'Inglewood'),
99:(7,11,17,0,-4,'Miami Gardens'),100:(7,11,20,0,-5,'Kansas City'),
101:(7,14,14,0,-5,'Arlington'),102:(7,15,15,0,-4,'Atlanta'),
104:(7,19,None,None,None,'East Rutherford')}
SCHED = {}
for _n, (_mo, _dy, _hh, _mm, _off, _ve) in SCHED_RAW.items():
    if _hh is None:
        _d = datetime.date(2026, _mo, _dy)
        SCHED[_n] = [_d.strftime('%a ') + str(_dy) + _d.strftime(' %B'), '', _ve]
    else:
        _uk = datetime.datetime(2026, _mo, _dy, _hh, _mm) + datetime.timedelta(hours=1 - _off)
        _h = _uk.hour; _ap = 'am' if _h < 12 else 'pm'; _h12 = _h % 12 or 12
        SCHED[_n] = [_uk.strftime('%a ') + str(_uk.day) + _uk.strftime(' %B'),
                     f"{_h12}:{_uk.minute:02d} {_ap} BST", _ve]

R32ORDER = [74,77,73,75,83,84,81,82,76,78,79,80,86,88,85,87]
KOR = [{'name':'Round of 16','col':2,'matches':[[89,74,77],[90,73,75],[93,83,84],[94,81,82],[91,76,78],[92,79,80],[95,86,88],[96,85,87]]},
       {'name':'Quarter-final','col':3,'matches':[[97,89,90],[98,93,94],[99,91,92],[100,95,96]]},
       {'name':'Semi-final','col':4,'matches':[[101,97,98],[102,99,100]]},
       {'name':'Final','col':5,'matches':[[104,101,102]]}]

# (group, finishing position) -> fixed R32 match number; 3rd is fixed only for K and L
POSMATCH = {'1':{'A':79,'B':85,'C':76,'D':81,'E':74,'F':75,'G':82,'H':84,'I':77,'J':86,'K':87,'L':80},
            '2':{'A':73,'B':73,'C':75,'D':88,'E':78,'F':76,'G':88,'H':86,'I':78,'J':84,'K':83,'L':83},
            '3':{'K':80,'L':87}}

# team -> flagcdn ISO code (gb-eng / gb-sct for the home nations)
ISO = {'Mexico':'mx','South Africa':'za','South Korea':'kr','Czechia':'cz','Switzerland':'ch','Canada':'ca',
'Bosnia':'ba','Qatar':'qa','Brazil':'br','Morocco':'ma','Scotland':'gb-sct','Haiti':'ht','USA':'us',
'Australia':'au','Paraguay':'py','Turkiye':'tr','Germany':'de',"Cote d'Ivoire":'ci','Ecuador':'ec',
'Curacao':'cw','Netherlands':'nl','Japan':'jp','Sweden':'se','Tunisia':'tn','Egypt':'eg','Belgium':'be',
'Iran':'ir','New Zealand':'nz','Spain':'es','Cabo Verde':'cv','Uruguay':'uy','Saudi Arabia':'sa','France':'fr',
'Norway':'no','Senegal':'sn','Iraq':'iq','Argentina':'ar','Austria':'at','Algeria':'dz','Jordan':'jo',
'Colombia':'co','Portugal':'pt','Congo DR':'cd','Uzbekistan':'uz','England':'gb-eng','Ghana':'gh',
'Croatia':'hr','Panama':'pa'}

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>World Cup 2026 — Round-of-32 opponent predictions</title>
<style>
:root{--bg:#faf9f6;--surface:#fff;--line:#e7e5df;--ink:#1d1c1a;--muted:#6b6a66;--faint:#9c9b96;--accent:#a16207;--accent-soft:#fbf3df;--elim:#d3d1c7}
@media(prefers-color-scheme:dark){:root{--bg:#1a1916;--surface:#232220;--line:#34332f;--ink:#f0efe9;--muted:#a3a29c;--faint:#6f6e69;--accent:#e3b341;--accent-soft:#33290d;--elim:#3a3935}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1060px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:25px;font-weight:600;margin:0 0 2px;display:flex;align-items:center;gap:10px;letter-spacing:-.01em}
h1 img{height:30px;width:30px}
.tsub{font-size:17px;font-weight:500;color:var(--accent);margin:0 0 14px;letter-spacing:.01em}
.sub{color:var(--muted);font-size:14px;margin:0 0 16px}
.source{display:flex;gap:11px;align-items:flex-start;background:var(--accent-soft);border:1px solid var(--line);border-radius:12px;padding:12px 14px;font-size:13px;color:var(--ink);margin:0 0 24px;line-height:1.55}
.src-badge{flex-shrink:0;font-weight:600;color:var(--accent);font-size:12px;border:1px solid var(--accent);border-radius:6px;padding:3px 9px;white-space:nowrap}
.updated{font-size:12px;color:var(--faint);margin:-10px 0 20px}
.frozen-note{display:inline-block;color:var(--accent);font-weight:600;border:1px solid var(--accent);border-radius:6px;padding:2px 8px;margin-left:6px}
.source a{font-weight:500;cursor:pointer}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin-bottom:22px}
label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px}
.dd{position:relative}
.ddbtn{width:100%;display:flex;align-items:center;gap:8px;font-size:16px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);cursor:pointer;text-align:left}
.ddbtn .chev{margin-left:auto;color:var(--muted);font-size:18px;line-height:1}
.ddbtn .grp{margin-left:0}
.ddpanel{position:absolute;z-index:20;top:calc(100% + 6px);left:0;right:0;background:var(--surface);border:1px solid var(--line);border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.14);max-height:340px;overflow:auto;padding:8px}
.ddsearch{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font-size:14px;margin-bottom:4px;position:sticky;top:0}
.ddhead{font-size:11px;color:var(--faint);letter-spacing:.04em;padding:9px 8px 3px}
.dditem{display:flex;align-items:center;gap:8px;padding:8px;border-radius:8px;cursor:pointer;font-size:14px}
.dditem:hover{background:var(--bg)}
.dditem.sel{background:var(--accent-soft)}
.dditem .grp{margin-left:auto}
.posrow{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 6px}
.posbtn{flex:1;min-width:60px;display:flex;flex-direction:column;align-items:center;gap:1px;padding:9px 6px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);cursor:pointer;font-size:14px}
.posbtn small{font-size:12px;color:var(--muted)}
.posbtn.active{border-color:var(--accent);background:var(--accent-soft)}
.posbtn.active small{color:var(--accent)}
.cap{font-size:14px;margin:16px 0 14px;color:var(--ink);display:flex;align-items:center;gap:4px;flex-wrap:wrap}
.cap b{font-weight:600}
.row{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.nm{width:150px;flex-shrink:0;font-size:13px;display:flex;align-items:center;justify-content:flex-end;gap:0;white-space:nowrap;overflow:hidden}
.fl{height:13px;width:auto;margin-right:6px;border-radius:2px;vertical-align:-1px;flex-shrink:0}
.lt{overflow:hidden;text-overflow:ellipsis}
.grp{font-size:11px;color:var(--faint);margin-left:6px;flex-shrink:0}
.lnk{cursor:pointer;display:inline-flex;align-items:center;min-width:0}
.lnk:hover .lt{text-decoration:underline;text-decoration-color:var(--accent)}
.track{flex:1;background:var(--bg);border-radius:7px;height:22px;overflow:hidden}
.fill{height:100%;background:var(--accent);border-radius:7px}
.fill.e{background:var(--elim)}
.pc{width:50px;flex-shrink:0;font-size:13px;font-weight:600;text-align:right}
.pc.e{color:var(--faint);font-weight:400}
.nm.e .lt{color:var(--faint)}
.muted{color:var(--muted)}
h2{font-size:17px;font-weight:600;margin:0 0 14px}
.foot{font-size:12px;color:var(--faint);margin-top:8px;line-height:1.6}
.mu{display:flex;align-items:center;gap:6px;font-size:14px;padding:7px 0;border-top:1px solid var(--line)}
.mu:first-child{border-top:none}
.mu .v{font-weight:600}
details{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:4px 22px;margin-bottom:16px}
summary{cursor:pointer;font-weight:600;font-size:15px;padding:14px 0;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"\203A";display:inline-block;margin-right:10px;transition:transform .15s;color:var(--muted)}
details[open] summary::before{transform:rotate(90deg)}
details p,details li{font-size:14px;color:var(--ink)}
details .foot{font-size:12px}
a{color:var(--accent)}
.disc{font-size:12px;color:var(--faint);line-height:1.7;border-top:1px solid var(--line);margin-top:8px;padding-top:16px}
.fixture{font-size:13px;color:var(--muted);background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:8px 12px;margin:0 0 14px;display:none}
.fixture.show{display:block}
.fixture b{color:var(--ink);font-weight:600}
.fxpc{font-weight:600;color:var(--accent);white-space:nowrap}
.fxdt::before{content:"\00A0\00B7\00A0"}
.fixture .fxhead{font-weight:600;color:var(--ink);font-size:12px;margin-bottom:5px}
.mdate{margin-left:auto;font-size:11px;color:var(--faint);margin-right:10px;white-space:nowrap}
.bwrap{overflow:auto;padding-bottom:8px}
.bhead{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));column-gap:24px;min-width:940px;margin-bottom:8px}
.bhead span{font-size:11px;color:var(--faint);text-align:center;font-weight:600}
.bgrid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));grid-template-rows:repeat(16,124px);column-gap:24px;min-width:940px}
.slot{position:relative;display:flex;align-items:center;justify-content:center}
.mcard,.kocard{width:100%;position:relative;border:1px solid var(--line);border-radius:9px;padding:7px 9px;background:var(--surface)}
.mcard{cursor:pointer}
.mcard.sel{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.mh{display:flex;align-items:center;font-size:10px;color:var(--faint);margin-bottom:4px;gap:5px}
.mh .p{margin-left:auto;font-weight:600;color:var(--accent);font-size:11px}
.mteam{display:flex;align-items:center;gap:6px;font-size:13px;padding:1px 0}
.mteam .lt{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.msched{font-size:10px;color:var(--muted);margin-top:4px;line-height:1.35}
.msched div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kocard .kh{font-size:10px;color:var(--faint);margin-bottom:3px}
.kocard .kp{font-size:12px;line-height:1.35}
.kocard .kvs{font-size:10px;color:var(--faint)}
.kocard .ks{font-size:10px;color:var(--muted);margin-top:4px}
.slot.adv::before{content:"";position:absolute;left:-12px;top:25%;height:50%;border-left:1.5px solid var(--line)}
.slot.adv>.mcard::before,.slot.adv>.kocard::before{content:"";position:absolute;left:-12px;top:50%;width:12px;border-top:1.5px solid var(--line)}
.slot.fwd::after{content:"";position:absolute;right:-12px;top:50%;width:12px;border-top:1.5px solid var(--line)}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;z-index:50;padding:20px}
.modal[hidden]{display:none}
.modal-card{background:var(--surface);border:1px solid var(--line);border-radius:14px;max-width:440px;width:100%;max-height:82vh;overflow:auto;padding:18px 22px;position:relative}
.modal-x{position:absolute;top:9px;right:12px;border:none;background:transparent;font-size:24px;line-height:1;color:var(--muted);cursor:pointer;padding:2px 6px}
.msub{font-size:12px;color:var(--faint);margin:2px 0 10px}
.alt{display:flex;align-items:center;gap:5px;font-size:13px;padding:6px 2px;border-top:1px solid var(--line)}
.alt:first-child{border-top:none}
.alt .p{margin-left:auto;font-weight:600}
.alt .fl{height:12px}
@media(max-width:560px){
 .wrap{padding:22px 14px 48px}
 h1{font-size:19px;gap:8px}
 h1 img{height:26px;width:26px}
 .card{padding:16px 15px}
 details{padding:2px 16px}
 .nm{width:120px}
 .grp{display:none}
 .pc{width:44px}
 .row{gap:8px}
 .posbtn{min-width:54px;padding:8px 4px}
 .mu .grp{display:none}
 .source{flex-direction:column;gap:8px}
 .frozen-note{display:block;margin:6px 0 0;width:fit-content}
 .fxdt{display:block}
 .fxdt::before{content:""}
}
</style></head>
<body><div class="wrap">
<h1><img src="https://img.icons8.com/color/96/world-cup.png" alt="">World Cup 2026</h1>
<p class="tsub">Round-of-32 opponent predictions</p>
<p class="sub">Who will each team face in the round of 32? Pick a team and a finishing position to see every possible opponent and its probability.</p>
<div class="source">
  <span class="src-badge">Data: Opta Analyst</span>
  <span>Every probability here comes directly from the publicly available <a href="https://theanalyst.com/" target="_blank" rel="noopener">Opta Analyst</a> Supercomputer - the same group-stage forecasts Opta publishes. Nothing is re-modelled: the possible opponents are worked out solely by applying FIFA's official round-of-32 bracket to Opta's numbers. <a onclick="var d=document.getElementById('src-details');d.open=true;d.scrollIntoView({behavior:'smooth'})">How it works &rsaquo;</a></span>
</div>
<div class="updated">Last updated: /*UPDATED*/</div>

<div class="card">
  <label>Select a team</label>
  <div class="dd" id="dd">
    <button class="ddbtn" id="ddbtn" aria-haspopup="listbox" aria-expanded="false"></button>
    <div class="ddpanel" id="ddpanel" hidden>
      <input class="ddsearch" id="ddsearch" placeholder="Search team..." aria-label="Search team">
      <div id="ddlist" role="listbox"></div>
    </div>
  </div>
  <div class="posrow" id="posrow"></div>
  <div class="fixture" id="fixture"></div>
  <div class="cap" id="cap"></div>
  <div id="bars"></div>
  <p class="foot" id="foot"></p>
</div>

<div class="card">
  <h2>Most likely knockout bracket</h2>
  <div class="bwrap">
    <div class="bhead"><span>Round of 32</span><span>Round of 16</span><span>Quarter-finals</span><span>Semi-finals</span><span>Final</span></div>
    <div class="bgrid" id="bgrid"></div>
  </div>
  <p class="foot">Round-of-32 boxes show each slot's most likely tie and the chance that exact tie occurs - click a box to pop up every possible pairing. Later rounds show how the bracket and schedule progress to the final; the teams there depend on knockout results, which this page does not forecast.</p>
</div>

<details>
  <summary>How the round of 32 works</summary>
  <p>The 48 teams are split into 12 groups (A-L) of four. The top two from every group advance, together with the eight best third-placed teams - 32 teams in all.</p>
  <p>The eight best third-placed teams are ranked across all groups by: points, then goal difference, then goals scored, then disciplinary record, then drawing of lots.</p>
  <p>The bracket is partly fixed and partly variable. Four group winners meet a specified runner-up, and the remaining group runners-up meet each other. The other eight group winners each host one of the eight qualifying third-placed teams - but <em>which</em> third a given winner plays depends on which groups the eight qualifying thirds come from. FIFA pre-defines this with a table of 495 possible combinations (Annex C of the tournament regulations), so once the eight thirds are known, every matchup is fixed.</p>
  <p class="foot">Rules summarised from <a href="https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_knockout_stage" target="_blank" rel="noopener">"2026 FIFA World Cup knockout stage", Wikipedia</a>, available under <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener">CC BY-SA 4.0</a>. Tournament regulations: FIFA.</p>
</details>

<details id="src-details">
  <summary>Data, sourcing &amp; disclaimer</summary>
  <p>The finish-position probabilities (each team's chance of finishing 1st / 2nd / 3rd / 4th in its group, and of qualifying) are sourced from the publicly available <a href="https://theanalyst.com/" target="_blank" rel="noopener">Opta Analyst</a> Supercomputer. No additional predictive modelling has been applied to those numbers.</p>
  <p>The opponent probabilities shown here are obtained purely by applying FIFA's published round-of-32 bracket rules (above) to Opta's figures - i.e. bracket arithmetic, not a new forecast. The one unavoidable assumption is the <em>joint</em> distribution of which eight third-placed teams qualify together, because Opta publishes only the per-group marginals; this is modelled as independent Bernoulli draws conditioned on exactly eight advancing, restricted to combinations consistent with the now-fixed order of the already-decided third-placed teams (impossible combinations are ruled out). Probabilities reflect a single snapshot (/*SNAPDATE*/) and change as results come in.</p>
  <p class="disc">Finish-position and qualification data &copy; Stats Perform / Opta. "Opta", "Opta Analyst" and the Opta Supercomputer are trademarks of Stats Perform. This page is an independent, non-commercial, illustrative visualisation and is not affiliated with, endorsed by, or produced by Stats Perform, Opta, FIFA or any national association. Data is used here for personal, non-commercial reference only; all rights in the underlying data remain with their respective owners. Tournament rules text is adapted from Wikipedia under CC BY-SA 4.0. Flag images courtesy of <a href="https://flagcdn.com/" target="_blank" rel="noopener">flagcdn.com</a>; World Cup icon by <a href="https://icons8.com/" target="_blank" rel="noopener">Icons8</a>.</p>
</details>

<div class="modal" id="modal" hidden>
  <div class="modal-card">
    <button class="modal-x" id="modal-x" aria-label="Close">&times;</button>
    <div id="modal-body"></div>
  </div>
</div>
</div>
<script>
const DATA=/*DATA*/;const ISO=/*FLAGS*/;const GRP=/*GROUPS*/;const BRACKET=/*BRACKET*/;const SCHED=/*SCHED*/;const POSMATCH=/*POSMATCH*/;const R32ORDER=/*R32O*/;const KOR=/*KOR*/;const G3RD=/*G3RD*/;
const ORDER=['1st','2nd','3rd','4th'];
const fl=n=>ISO[n]?('<img class="fl" loading="lazy" alt="" src="https://flagcdn.com/h24/'+ISO[n]+'.png">'):'';
const gtag=n=>GRP[n]?('<span class="grp">Group '+GRP[n]+'</span>'):'';
const isE=n=>n.indexOf('Eliminated')===0;
const pct=v=>(v*100).toFixed(1)+'%';
let team='England',view='overall';
const bg={};Object.keys(DATA).forEach(t=>{(bg[DATA[t].g]=bg[DATA[t].g]||[]).push(t);});
const ddbtn=document.getElementById('ddbtn'),ddpanel=document.getElementById('ddpanel'),
 ddlist=document.getElementById('ddlist'),ddsearch=document.getElementById('ddsearch');
function updateTrigger(){ddbtn.innerHTML=fl(team)+'<span class="lt">'+team+'</span><span class="grp">Group '+DATA[team].g+'</span><span class="chev">›</span>';}
function buildList(q){q=(q||'').toLowerCase();ddlist.innerHTML='';
 Object.keys(bg).sort().forEach(g=>{const items=bg[g].slice().sort().filter(t=>t.toLowerCase().includes(q));
  if(!items.length)return;const h=document.createElement('div');h.className='ddhead';h.textContent='Group '+g;ddlist.appendChild(h);
  items.forEach(t=>{const it=document.createElement('div');it.className='dditem'+(t===team?' sel':'');it.setAttribute('role','option');
   it.innerHTML=fl(t)+'<span class="lt">'+t+'</span><span class="grp">Group '+g+'</span>';it.onclick=()=>{closeDD();go(t);};ddlist.appendChild(it);});});}
function openDD(){ddpanel.hidden=false;ddbtn.setAttribute('aria-expanded','true');ddsearch.value='';buildList('');ddsearch.focus();}
function closeDD(){ddpanel.hidden=true;ddbtn.setAttribute('aria-expanded','false');}
ddbtn.onclick=()=>{ddpanel.hidden?openDD():closeDD();};
ddsearch.oninput=()=>buildList(ddsearch.value);
document.addEventListener('click',e=>{if(!document.getElementById('dd').contains(e.target))closeDD();});
function go(name){if(!DATA[name])return;team=name;if(view!=='overall'&&!DATA[team].pos[view])view='overall';updateTrigger();render();window.scrollTo({top:0,behavior:'smooth'});}
updateTrigger();
function overall(t){const a={};const P=DATA[t].pos;for(const p in P){for(const x of P[p].o){const n=x[0],c=x[1];const k=isE(n)?'Eliminated':n;a[k]=(a[k]||0)+P[p].p*c;}}return Object.entries(a).sort((x,y)=>y[1]-x[1]);}
function teamSpan(n){if(isE(n))return '<span class="lt">'+n+'</span>';
 return '<span class="lnk" data-team="'+n+'">'+fl(n)+'<span class="lt">'+n+'</span>'+gtag(n)+'</span>';}
function render(){
 const P=DATA[team].pos;
 const pr=document.getElementById('posrow');pr.innerHTML='';
 const views=[['overall','Overall',null]].concat(ORDER.filter(p=>P[p]).map(p=>[p,p,P[p].p]));
 views.forEach(v=>{const b=document.createElement('button');b.className='posbtn'+(view===v[0]?' active':'');
  b.innerHTML='<span>'+v[1]+'</span><small>'+(v[2]!=null?pct(v[2]):'all')+'</small>';b.onclick=()=>{view=v[0];render();};pr.appendChild(b);});
 let list,cap;
 if(view==='overall'){list=overall(team);cap='<span class="muted">Across all scenarios,</span> '+'<b>'+team+'</b> <span class="muted">would face:</span>';}
 else{list=P[view].o.map(x=>[isE(x[0])?(x[0].indexOf('4th')>=0?'Eliminated - finished 4th':'Eliminated - not a top-8 third'):x[0],x[1]]);
  cap='<span class="muted">If</span> '+'<b>'+team+'</b> <span class="muted">finish</span> <b>'+view+'</b> <span class="muted">('+pct(P[view].p)+' likely), their opponent:</span>';}
 document.getElementById('cap').innerHTML=cap;
 const fx=document.getElementById('fixture'),g=DATA[team].g;
 function fmtMatch(mn){const s=SCHED[mn];return 'Match '+mn+' &middot; '+s[2]+'<span class="fxdt">'+s[0]+(s[1]?', '+s[1]:'')+'</span>';}
 function fxline(p){
  if(p==='1st'||p==='2nd'){const mn=POSMATCH[p[0]]&&POSMATCH[p[0]][g];return mn?fmtMatch(mn):null;}
  if(p==='3rd'){const arr=(G3RD[g]||[]).filter(o=>o[1]>=0.005);if(!arr.length)return null;
   if(arr.length===1||arr[0][1]>=0.995)return fmtMatch(arr[0][0]);
   return 'one of <span class="muted">(if among the 8 best thirds)</span>:<br>'
    +arr.map(o=>'&nbsp;&nbsp;&bull; '+fmtMatch(o[0])+' <span class="fxpc">('+pct(o[1])+' probability)</span>').join('<br>');}
  return null;}
 if(view==='overall'){
  let lines=[];['1st','2nd','3rd'].forEach(p=>{if(P[p]){const l=fxline(p);if(l)lines.push('<b>'+p+'</b> <span class="fxpc">('+pct(P[p].p)+' probability)</span> '+l);}});
  if(lines.length){fx.className='fixture show';fx.innerHTML='<div class="fxhead">Possible fixtures by finishing position</div>'+lines.join('<br>');}
  else{fx.className='fixture';fx.innerHTML='';}}
 else{const l=fxline(view);
  if(l){fx.className='fixture show';fx.innerHTML='Fixture: '+l;}
  else{fx.className='fixture';fx.innerHTML='';}}
 const max=Math.max.apply(null,list.map(x=>x[1]));
 const bars=document.getElementById('bars');bars.innerHTML='';
 list.forEach(it=>{const n=it[0],v=it[1],e=isE(n);const r=document.createElement('div');r.className='row';
  r.innerHTML='<div class="nm'+(e?' e':'')+'">'+teamSpan(n)+'</div>'
   +'<div class="track"><div class="fill'+(e?' e':'')+'" style="width:'+Math.max(v/max*100,1.5)+'%"></div></div>'
   +'<div class="pc'+(e?' e':'')+'">'+pct(v)+'</div>';bars.appendChild(r);});
 document.getElementById('foot').innerHTML='Toggle a finishing position to condition the list; the % on each toggle is the chance of finishing there. Click any opponent to jump to it.';
}
document.body.addEventListener('click',e=>{const el=e.target.closest('[data-team]');if(el)go(el.getAttribute('data-team'));});
render();
const BR={};BRACKET.forEach(m=>BR[m.n]=m);
const SPAN={2:2,3:4,4:8,5:16};
const bgrid=document.getElementById('bgrid');
const modal=document.getElementById('modal'),modalBody=document.getElementById('modal-body');
function showDetail(n){const mt=BR[n];if(!mt)return;
 let h='<div class="ddhead">Match '+n+' &middot; '+mt.slot+'</div><div class="msub">Every possible tie, by likelihood</div>';
 mt.pairs.forEach(p=>{h+='<div class="alt">'+fl(p[0])+'<span class="lt">'+p[0]+'</span> <span class="muted">v</span> '+fl(p[1])+'<span class="lt">'+p[1]+'</span><span class="p">'+pct(p[2])+'</span></div>';});
 modalBody.innerHTML=h;modal.hidden=false;}
function closeModal(){modal.hidden=true;}
document.getElementById('modal-x').onclick=closeModal;
modal.addEventListener('click',e=>{if(e.target===modal)closeModal();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
R32ORDER.forEach((n,i)=>{const mt=BR[n],top=(mt&&mt.pairs[0])||['TBD','TBD',0],s=SCHED[n];
 const slot=document.createElement('div');slot.className='slot fwd';slot.style.gridColumn=1;slot.style.gridRow=''+(i+1);
 const c=document.createElement('div');c.className='mcard';c.id='slot'+n;
 c.innerHTML='<div class="mh"><span>M'+n+'</span><span class="p">'+pct(top[2])+'</span></div>'
  +'<div class="mteam">'+fl(top[0])+'<span class="lt">'+top[0]+'</span></div>'
  +'<div class="mteam">'+fl(top[1])+'<span class="lt">'+top[1]+'</span></div>'
  +(s?'<div class="msched"><div>'+s[0]+(s[1]?', '+s[1]:'')+'</div><div>'+s[2]+'</div></div>':'');
 c.addEventListener('click',()=>showDetail(n));slot.appendChild(c);bgrid.appendChild(slot);});
KOR.forEach(rd=>{const span=SPAN[rd.col];rd.matches.forEach((m,i)=>{const n=m[0],s=SCHED[n];
 const slot=document.createElement('div');slot.className='slot adv'+(rd.col<5?' fwd':'');
 slot.style.gridColumn=rd.col;slot.style.gridRow=(i*span+1)+' / span '+span;
 const c=document.createElement('div');c.className='kocard';
 c.innerHTML='<div class="kh">'+rd.name+' &middot; M'+n+'</div>'
  +'<div class="kp"><span class="muted">Winner M'+m[1]+'</span><div class="kvs">v</div><span class="muted">Winner M'+m[2]+'</span></div>'
  +(s?'<div class="ks">'+s[0]+(s[1]?', '+s[1]:'')+' &middot; '+s[2]+'</div>':'');
 slot.appendChild(c);bgrid.appendChild(slot);});});
</script></body></html>
"""


def main():
    rows = list(csv.DictReader(open('opponent_matrix_exact.csv')))
    T, GROUP = {}, {}
    for r in rows:
        t = r['team']; GROUP[t] = r['group']
        T.setdefault(t, {'g': r['group'], 'pos': {}})
        pos = r['league_position']
        d = T[t]['pos'].setdefault(pos, {'p': round(float(r['prob_of_position']), 4), 'o': []})
        cond = float(r['prob_of_opponent_given_position'])
        if cond >= 0.001:
            d['o'].append([r['possible_opponent'], round(cond, 4)])
    for t in T:
        for pos in T[t]['pos']:
            T[t]['pos'][pos]['o'].sort(key=lambda x: -x[1])

    # ---- per-slot R32 bracket distributions ----
    prows = list(csv.reader(open('opta_positions.csv')))[1:]
    Pm, ti = {}, defaultdict(list)
    for g, t, a, b, c, d in prows:
        Pm[t] = [float(a)/100, float(b)/100, float(c)/100, float(d)/100]; ti[g].append(t)
    q3 = {t: max(0.0, QUAL[t]-Pm[t][0]-Pm[t][1]) for t in Pm}
    A = {g: sum(q3[t] for t in ti[g]) for g in ti}
    GRPS = list('ABCDEFGHIJKL')
    # Completed-group thirds, best->worst; advancing subset must be a top-down
    # prefix (mirrors opponent_matrix_exact.py). [] disables pruning.
    LOCKED = ['F', 'E', 'B', 'D', 'A', 'C']  # Swe, Ecu, Bos, Par, Kor, Sco
    def _locked_ok(S):
        out = False
        for g in LOCKED:
            if g in S:
                if out:
                    return False
            else:
                out = True
        return True
    tbl = {''.join(sorted(r['advancing'])): r['assign']
           for r in json.load(open('assignment_table.json')).values()}
    combos, Z = [], 0.0
    for eight in combinations(GRPS, 8):
        S = set(eight); w = 1.0
        for g in GRPS:
            w *= A[g] if g in S else (1-A[g])
        if w == 0:
            continue
        if not _locked_ok(S):
            continue
        combos.append((S, w, tbl[''.join(sorted(eight))])); Z += w
    hostopp = {}
    for G in 'ABDEGIKL':
        dd = defaultdict(float)
        for S, w, amap in combos:
            Y = amap['1'+G][1]
            for u in ti[Y]:
                if q3[u] > 0:
                    dd[u] += w/Z * q3[u] / A[Y]
        hostopp[G] = dd

    # which group winner hosts each group's third (-> which R32 slot) | given it advances
    HOSTMATCH = {'E':74,'I':77,'A':79,'L':80,'D':81,'G':82,'B':85,'K':87}
    PYm = {g: sum(w for S, w, _ in combos if g in S) for g in GRPS}
    host_of = {Y: defaultdict(float) for Y in GRPS}
    for S, w, amap in combos:
        inv = {amap['1'+X][1]: X for X in HOSTMATCH}
        for Y in S:
            host_of[Y][inv[Y]] += w / PYm[Y]
    G3RD = {g: sorted([[HOSTMATCH[X], round(p, 4)] for X, p in host_of[g].items()],
                      key=lambda x: -x[1]) for g in GRPS}

    def slot(pd, grp):
        i = int(pd)-1
        return [(t, Pm[t][i]) for t in ti[grp] if Pm[t][i] > 0]

    fixed = [('73','2A v 2B',('2','A'),('2','B')),('75','1F v 2C',('1','F'),('2','C')),
             ('76','1C v 2F',('1','C'),('2','F')),('78','2E v 2I',('2','E'),('2','I')),
             ('83','2K v 2L',('2','K'),('2','L')),('84','1H v 2J',('1','H'),('2','J')),
             ('86','1J v 2H',('1','J'),('2','H')),('88','2D v 2G',('2','D'),('2','G'))]
    hostlab = {'74':('E','1E v 3rd A/B/C/D/F'),'77':('I','1I v 3rd C/D/F/G/H'),
               '79':('A','1A v 3rd C/E/F/H/I'),'80':('L','1L v 3rd E/H/I/J/K'),
               '81':('D','1D v 3rd B/E/F/I/J'),'82':('G','1G v 3rd A/E/H/I/J'),
               '85':('B','1B v 3rd E/F/G/I/J'),'87':('K','1K v 3rd D/E/I/J/L')}
    bracket = []
    for n, sl, sa, sb in fixed:
        pairs = [[ta, tb, round(pa*pb, 4)] for ta, pa in slot(*sa) for tb, pb in slot(*sb)]
        pairs = [p for p in sorted(pairs, key=lambda x: -x[2]) if p[2] >= 0.003][:12]
        bracket.append({'n': n, 'slot': sl, 'pairs': pairs})
    for n, (G, sl) in hostlab.items():
        win = [(t, Pm[t][0]) for t in ti[G] if Pm[t][0] > 0]
        pairs = [[w_, u, round(pw*pu, 4)] for w_, pw in win for u, pu in hostopp[G].items()]
        pairs = [p for p in sorted(pairs, key=lambda x: -x[2]) if p[2] >= 0.003][:12]
        bracket.append({'n': n, 'slot': sl, 'pairs': pairs})
    bracket.sort(key=lambda x: int(x['n']))

    html = (TEMPLATE
            .replace('/*DATA*/', json.dumps(T, separators=(',', ':')))
            .replace('/*FLAGS*/', json.dumps(ISO, ensure_ascii=False))
            .replace('/*GROUPS*/', json.dumps(GROUP, ensure_ascii=False))
            .replace('/*BRACKET*/', json.dumps(bracket, ensure_ascii=False))
            .replace('/*SCHED*/', json.dumps(SCHED))
            .replace('/*POSMATCH*/', json.dumps(POSMATCH))
            .replace('/*R32O*/', json.dumps(R32ORDER))
            .replace('/*KOR*/', json.dumps(KOR, ensure_ascii=False))
            .replace('/*G3RD*/', json.dumps(G3RD))
            .replace('/*UPDATED*/', datetime.datetime.fromtimestamp(
                os.path.getmtime('opta_positions.csv')).strftime('%d %B %Y, %H:%M'))
            .replace('/*SNAPDATE*/', datetime.datetime.fromtimestamp(
                os.path.getmtime('opta_positions.csv')).strftime('%d %B %Y')))
    # write the canonical page plus index.html (GitHub Pages root landing copy)
    for _out in ('wc26_r32_predictions.html', 'index.html'):
        open(_out, 'w', encoding='utf-8').write(html)
    print('wrote wc26_r32_predictions.html + index.html')


if __name__ == '__main__':
    main()
