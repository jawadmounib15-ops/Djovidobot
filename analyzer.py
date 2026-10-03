# analyzer.py V99 - SBLOCCATO - SEGNALI GARANTITI + STORICO
import yfinance as yf, pandas as pd, gc, numpy as np
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
    "Gold OTC":"GC=F","Silver OTC":"SI=F","WTI OTC":"CL=F","Brent OTC":"BZ=F","Gas OTC":"NG=F"
}
def fix(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V99 SBLOCCATO</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:18px;width:98%;max-width:440px;display:block;margin:8px auto;cursor:pointer}
.g{background:#00ff88;color:#000;border:3px solid #00ff88}.d{background:#222;color:#fff;border:2px solid #555}
.mode{background:#111;border:2px solid #00ff88;border-radius:12px;padding:10px;margin:10px auto;max-width:440px}
.mbtn{padding:10px 14px;border-radius:8px;font-weight:bold;margin:3px;cursor:pointer;border:2px solid #444;font-size:14px}
.active{background:#00ff88;color:#000}.inactive{background:#222;color:#fff}
.card{background:#1e1e1e;border-radius:20px;padding:16px;margin:10px auto;max-width:460px;text-align:left;border-left:10px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}
.score{font-size:48px;font-weight:900}
.badge{position:absolute;top:12px;right:12px;text-align:right}
.prepara{background:#00ff88;color:#000;font-weight:bold;padding:12px;border-radius:10px;margin-top:10px;text-align:center}
.sellbg{background:#ff3b3b;color:#fff}
.storico{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:14px auto;max-width:460px;text-align:left;font-size:12px}
#s{padding:10px;border-radius:8px;margin:8px auto;max-width:440px;font-weight:bold}
.on{background:#00ff88;color:#000}.off{background:#ff3b3b;color:#fff}
</style></head><body>
<h2>✅ V99 - SBLOCCATO 60/70/85</h2>
<div id="s" class="off">🔇 CLICCA ATTIVA</div>
<div class="mode">
<button id="b60" class="mbtn active" onclick="setMode(60)">60 LARGO - segnali sempre</button>
<button id="b70" class="mbtn inactive" onclick="setMode(70)">70 NORMALE</button>
<button id="b85" class="mbtn inactive" onclick="setMode(85)">85 STRICT</button>
</div>
<div class="btn g" onclick="att()">🔔 ATTIVA SUONO 2 MIN</div>
<div class="btn d" onclick="scan()">🔍 SCAN ORA</div>
<p id="info">Mode 60 sbloccato</p><div id="live"></div>
<div class="storico"><b>📜 STORICO (ultimi 30):</b><div id="storico">Vuoto - appena parte si riempie</div><div style="margin-top:8px"><span onclick="clearStor()" style="color:#ff3b3b;cursor:pointer">🗑️ Pulisci storico</span></div></div>
<script>
let ctx=null,ok=false,mode=60,expMin=2;
let stor=JSON.parse(localStorage.getItem('v99_stor')||'[]');
function updStor(){let h=''; stor.slice(0,30).forEach(s=>{h+=`<div>${s}</div>`}); document.getElementById('storico').innerHTML=h||'Vuoto';}
updStor();
function clearStor(){stor=[]; localStorage.setItem('v99_stor',JSON.stringify(stor)); updStor();}
function setMode(m){mode=m; document.getElementById('b60').className=m==60?'mbtn active':'mbtn inactive'; document.getElementById('b70').className=m==70?'mbtn active':'mbtn inactive'; document.getElementById('b85').className=m==85?'mbtn active':'mbtn inactive'; scan();}
function att(){try{ctx=new (window.AudioContext||window.webkitAudioContext)(); ctx.resume(); ok=true; document.getElementById('s').className='on'; document.getElementById('s').innerText='🔊 ON 2 MIN mode '+mode; let o=ctx.createOscillator(),g=ctx.createGain(); o.frequency.value=900; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(1,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+0.4); o.start(); o.stop(ctx.currentTime+0.4); scan();}catch(e){alert('attiva audio');}}
function suona(){if(!ok) return; try{let o=ctx.createOscillator(),g=ctx.createGain(); o.frequency.value=1100; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(1,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+0.5); o.start(); o.stop(ctx.currentTime+0.5);}catch(e){} if(navigator.vibrate) navigator.vibrate([400,100,600]);}
let cur=[],ent=0; function getN(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMilliseconds(0); nx.setMinutes(n.getMinutes()+1); return nx;}
function scan(){document.getElementById('info').innerText='⏳ Scan mode '+mode+'...'; fetch('/api/scan?mode='+mode).then(r=>r.json()).then(d=>{cur=d.signals; ent=getN().getTime(); if(d.signals.length>0){suona(); let now=new Date().toLocaleTimeString('it-IT'); d.signals.forEach(s=>{stor.unshift(`${now} - ${s.score}/100 ${s.dir} ${s.pair} PIN ${s.ratio}x`);}); localStorage.setItem('v99_stor',JSON.stringify(stor.slice(0,50))); updStor();} render();}).catch(e=>{document.getElementById('info').innerText='Errore scan - riprovo';});}
function render(){let now=Date.now(); let diff=Math.ceil((ent-now)/1000); let tot=expMin*60; let h=''; if(cur.length>0) document.getElementById('info').innerText=`✅ ${cur.length} segnali mode ${mode} - entra tra ${diff}s`; else document.getElementById('info').innerText=`Nessun segnale mode ${mode} - prova 60`; cur.forEach(s=>{let col=s.dir=='BUY'?'#00ff88':'#ff3b3b'; let left=Math.max(0,tot+diff); let txt=diff>0?`ENTRA TRA ${diff}s - ${expMin} MIN`:`SCAD ${left}s`; h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><div class="badge"><div class="score" style="color:${col}">${s.score}/100</div><div style="color:${col};font-weight:900">${s.dir}</div><div style="font-size:10px">${s.ratio}x</div></div><div style="width:58%"><b style="color:${col}">${s.pair}</b><br><span style="color:#aaa;font-size:11px">${s.reason}</span><br><span style="font-size:12px">${s.price}</span></div><div class="prepara ${s.dir=='SELL'?'sellbg':''}">${txt}</div></div>`;}); document.getElementById('live').innerHTML=h||`<p style="color:#666;margin-top:15px">Mode ${mode} vuoto - clicca 60 LARGO<br>Se ancora vuoto, yfinance lento, aspetta 30 sec</p>`;}
setInterval(render,1000); setInterval(scan,30000);
</script></body></html>"""

@app.route('/api/scan')
def api():
    from flask import request
    mode=int(request.args.get('mode',60))
    out=[]
    min_ratio=1.6 if mode==60 else 2.0 if mode==70 else 2.8
    min_score=mode
    for otc, real in OTC_MAP.items():
        try:
            df=yf.download(real, period="1d", interval="1m", progress=False, auto_adjust=True)
            df=fix(df)
            if len(df)<20:
                del df; gc.collect()
                continue
            c=float(df.iloc[-1]['Close']); o=float(df.iloc[-1]['Open']); h=float(df.iloc[-1]['High']); l=float(df.iloc[-1]['Low'])
            body=abs(c-o)
            if body<0.00002: body=0.00002
            up=h-max(o,c); down=min(o,c)-l
            dire=None; ratio=0; reason=""
            if up>body*min_ratio:
                dire="SELL"; ratio=up/body; reason=f"PinBar SELL coda alta {ratio:.1f}x"
            elif down>body*min_ratio:
                dire="BUY"; ratio=down/body; reason=f"PinBar BUY coda bassa {ratio:.1f}x"
            else:
                # se non pinbar, cerca engulfing semplice per non restare vuoto
                c2=float(df.iloc[-2]['Close']); o2=float(df.iloc[-2]['Open'])
                if c>o and c2<o2 and c>o2 and mode==60:
                    dire="BUY"; ratio=1.3; reason="Engulfing BUY (mode 60 largo)"
                elif c<o and c2>o2 and c<o2 and mode==60:
                    dire="SELL"; ratio=1.3; reason="Engulfing SELL (mode 60 largo)"
                else:
                    del df; gc.collect()
                    continue
            score=50+int(ratio*10)
            if ratio>=2.0: score+=10
            if ratio>=3.0: score+=10
            if score<min_score:
                del df; gc.collect()
                continue
            if score>95: score=95
            fmt=f"{c:.5f}" if "JPY" not in otc and "OTC" in otc and len(otc)<12 else f"{c:.3f}" if "JPY" in otc else f"{c:.2f}"
            out.append({"pair":otc,"dir":dire,"price":fmt,"score":score,"ratio":round(ratio,1),"reason":reason})
            del df; gc.collect()
        except:
            gc.collect()
            continue
    out=sorted(out, key=lambda x: x['score'], reverse=True)[:15]
    return jsonify({"signals":out})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
