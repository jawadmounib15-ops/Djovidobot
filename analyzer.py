# analyzer.py V99.1 - UN PELO PIU STRETTO + 40 SEC
import yfinance as yf, pandas as pd, gc
from flask import Flask, jsonify
import os
app = Flask(__name__)
OTC_MAP = {
    "EURUSD-OTC":"EURUSD=X", "GBPUSD-OTC":"GBPUSD=X", "USDJPY-OTC":"USDJPY=X",
    "AUDUSD-OTC":"AUDUSD=X", "EURJPY-OTC":"EURJPY=X", "EURGBP-OTC":"EURGBP=X",
    "GBPJPY-OTC":"GBPJPY=X", "AUDJPY-OTC":"AUDJPY=X", "EURCHF-OTC":"EURCHF=X",
    "CADJPY-OTC":"CADJPY=X", "EURAUD-OTC":"EURAUD=X", "GBPAUD-OTC":"GBPAUD=X",
    "AUDCHF-OTC":"AUDCHF=X", "EURTRY-OTC":"EURTRY=X", "USDTRY-OTC":"USDTRY=X",
    "NZDJPY-OTC":"NZDJPY=X", "EURCAD-OTC":"EURCAD=X", "AUDCAD-OTC":"AUDCAD=X",
    "Gold OTC":"GC=F","Silver OTC":"SI=F","WTI OTC":"CL=F","Brent OTC":"BZ=F"
}
def fix(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V99.1</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:18px;width:98%;max-width:440px;display:block;margin:8px auto;cursor:pointer}
.g{background:#00ff88;color:#000;border:3px solid #00ff88}.d{background:#222;color:#fff;border:2px solid #555}
.mode{background:#111;border:2px solid #00ff88;border-radius:12px;padding:10px;margin:10px auto;max-width:440px}
.mbtn{padding:10px 14px;border-radius:8px;font-weight:bold;margin:3px;cursor:pointer;border:2px solid #444}
.active{background:#00ff88;color:#000}.inactive{background:#222;color:#fff}
.card{background:#1e1e1e;border-radius:20px;padding:16px;margin:10px auto;max-width:460px;text-align:left;border-left:10px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}
.score{font-size:48px;font-weight:900}
.badge{position:absolute;top:12px;right:12px;text-align:right}
.prepara{background:#00ff88;color:#000;font-weight:bold;padding:12px;border-radius:10px;margin-top:10px;text-align:center}
.sellbg{background:#ff3b3b;color:#fff}
.warn40{background:#ffcc00;color:#000;font-weight:900;padding:14px;border-radius:12px;margin:10px auto;max-width:460px;animation:blink 0.5s infinite;font-size:18px}
@keyframes blink{0%,50%{opacity:1}51%,100%{opacity:0.6}}
.storico{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:14px auto;max-width:460px;text-align:left;font-size:12px}
#s{padding:12px;border-radius:8px;margin:8px auto;max-width:440px;font-weight:bold;font-size:18px}
.on{background:#00ff88;color:#000}.off{background:#ff3b3b;color:#fff}
</style></head><body>
<h2>✅ V99.1 - UN PELO STRETTO + 40 SEC</h2>
<div id="s" class="off">🔇 ATTIVA 40 SEC</div>
<div class="mode">
<button id="b60" class="mbtn active" onclick="setMode(60)">60 STRETTO 1.8x</button>
<button id="b70" class="mbtn inactive" onclick="setMode(70)">70 NORMALE 2.2x</button>
<button id="b85" class="mbtn inactive" onclick="setMode(85)">85 STRICT 3.0x</button>
</div>
<div class="btn g" onclick="att()">🔔 ATTIVA AVVISO 40 SEC</div>
<div class="btn d" onclick="scan()">🔍 SCAN</div>
<p id="info">1.8x invece di 1.5x - più pulito</p>
<div id="warn40box"></div>
<div id="live"></div>
<div class="storico"><b>📜 STORICO:</b><div id="storico">Vuoto</div><div style="margin-top:8px"><span onclick="clearStor()" style="color:#ff3b3b;cursor:pointer">🗑️ Pulisci</span> | <span onclick="test40()" style="color:#ffcc00;cursor:pointer">⏰ Test 40 sec</span></div></div>
<script>
let ctx=null,ok=false,mode=60,expMin=2,warned40=false;
let stor=JSON.parse(localStorage.getItem('v991_stor')||'[]');
function updStor(){let h=''; stor.slice(0,30).forEach(s=>{h+=`<div>${s}</div>`}); document.getElementById('storico').innerHTML=h||'Vuoto';}
updStor();
function clearStor(){stor=[]; localStorage.setItem('v991_stor',JSON.stringify(stor)); updStor();}
function setMode(m){mode=m; warned40=false; document.getElementById('b60').className=m==60?'mbtn active':'mbtn inactive'; document.getElementById('b70').className=m==70?'mbtn active':'mbtn inactive'; document.getElementById('b85').className=m==85?'mbtn active':'mbtn inactive'; scan();}
function att(){try{ctx=new (window.AudioContext||window.webkitAudioContext)(); ctx.resume().then(()=>{ok=true; document.getElementById('s').className='on'; document.getElementById('s').innerText='🔊 ON 40 SEC'; beep(800,0.4); setTimeout(()=>beep(1200,0.4),300); setTimeout(()=>beep(1600,0.5),600); if(navigator.vibrate) navigator.vibrate([300,100,300]); if(Notification && Notification.permission!=='granted') Notification.requestPermission(); scan();});}catch(e){}}
function beep(f,d){if(!ctx) return; try{let o=ctx.createOscillator(),g=ctx.createGain(); o.type='square'; o.frequency.value=f; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(1,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+d); o.start(); o.stop(ctx.currentTime+d);}catch(e){}}
function avviso40(){if(!ok) return; if(ctx && ctx.state=='suspended') ctx.resume(); beep(1000,0.5); setTimeout(()=>beep(1000,0.5),400); setTimeout(()=>beep(1000,0.5),800); setTimeout(()=>beep(1500,0.6),1300); setTimeout(()=>beep(1500,0.6),1900); setTimeout(()=>beep(2000,0.8),2500); if(navigator.vibrate) navigator.vibrate([800,200,800,200,1500]); if(Notification && Notification.permission==='granted'){ new Notification('⏰ 40 SEC - PREPARA!', {body: cur.length+' segnali mode '+mode}); } document.getElementById('warn40box').innerHTML='<div class="warn40">⏰ 40 SEC - PREPARA 2 MIN!! ⏰</div>'; document.title='⏰ 40 SEC!'; setTimeout(()=>{document.getElementById('warn40box').innerHTML='';},15000);}
function test40(){if(!ok){alert('Attiva'); return;} avviso40();}
let cur=[],ent=0; function getN(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMilliseconds(0); nx.setMinutes(n.getMinutes()+1); return nx;}
function scan(){fetch('/api/scan?mode='+mode).then(r=>r.json()).then(d=>{cur=d.signals; ent=getN().getTime(); warned40=false; if(d.signals.length>0){let now=new Date().toLocaleTimeString('it-IT'); d.signals.forEach(s=>{stor.unshift(`${now} - ${s.score}/100 ${s.dir} ${s.pair} ${s.ratio}x`);}); localStorage.setItem('v991_stor',JSON.stringify(stor.slice(0,50))); updStor();} render();});}
function render(){let now=Date.now(); let diff=Math.ceil((ent-now)/1000); let tot=expMin*60; let h=''; if(cur.length>0){if(diff>40) document.getElementById('info').innerText=`✅ ${cur.length} segnali - avviso tra ${diff-40}s`; else if(diff<=40 && diff>0 && !warned40){ avviso40(); warned40=true; document.getElementById('info').innerText=`🔔 40 SEC - PREPARA!`; } else if(diff<=40 && diff>0){ document.getElementById('info').innerText=`⏰ ${diff}s - ENTRA 2 MIN!`; } else document.getElementById('info').innerText=`✅ IN CORSO`; } cur.forEach(s=>{let col=s.dir=='BUY'?'#00ff88':'#ff3b3b'; let left=Math.max(0,tot+diff); let txt=diff>40?`AVVISO TRA ${diff-40}s` : diff>0?`⏰ ENTRA TRA ${diff}s - 2 MIN` : `SCAD ${left}s`; let bord=diff<=40&&diff>0?' style="border:3px solid #ffcc00"':''; h+=`<div class="card ${s.dir=='SELL'?'sell':''}"${bord}><div class="badge"><div class="score" style="color:${col}">${s.score}/100</div><div style="color:${col};font-weight:900">${s.dir}</div><div style="font-size:10px">${s.ratio}x</div></div><div style="width:58%"><b style="color:${col}">${s.pair}</b><br><span style="color:#aaa;font-size:11px">${s.reason}</span><br>${s.price}</div><div class="prepara ${s.dir=='SELL'?'sellbg':''}">${txt}</div></div>`;}); document.getElementById('live').innerHTML=h||`Nessun segnale mode ${mode} - 1.8x più stretto di prima`;}
setInterval(render,1000); setInterval(scan,30000);
</script></body></html>"""

@app.route('/api/scan')
def api():
    from flask import request
    mode=int(request.args.get('mode',60))
    out=[]
    # STRINGO UN PELO
    min_ratio=1.8 if mode==60 else 2.2 if mode==70 else 3.0
    for otc, real in OTC_MAP.items():
        try:
            df=yf.download(real, period="1d", interval="1m", progress=False, auto_adjust=True)
            df=fix(df)
            if len(df)<10: continue
            c=float(df.iloc[-1]['Close']); o=float(df.iloc[-1]['Open']); h=float(df.iloc[-1]['High']); l=float(df.iloc[-1]['Low'])
            body=abs(c-o)
            if body<0.00001: continue # scarta doji piccolissime
            up=h-max(o,c); down=min(o,c)-l
            dire=None; ratio=0; reason=""
            if up>body*min_ratio: dire="SELL"; ratio=up/body; reason=f"Pin SELL {ratio:.1f}x coda"
            elif down>body*min_ratio: dire="BUY"; ratio=down/body; reason=f"Pin BUY {ratio:.1f}x coda"
            else: continue
            # filtro extra: solo se coda davvero lunga
            if ratio<min_ratio: continue
            score=min(95,50+int(ratio*10))
            if score<mode: continue
            fmt=f"{c:.5f}" if "JPY" not in otc else f"{c:.2f}"
            out.append({"pair":otc,"dir":dire,"price":fmt,"score":score,"ratio":round(ratio,1),"reason":reason})
            del df; gc.collect()
        except: gc.collect(); continue
    out=sorted(out, key=lambda x: x['score'], reverse=True)[:12]
    return jsonify({"signals":out})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
