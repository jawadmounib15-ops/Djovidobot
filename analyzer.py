# analyzer.py V98 - 70/85 + STORICO + 2 MIN
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
    "NZDJPY-OTC":"NZDJPY=X", "EURCAD-OTC":"EURCAD=X",
    "Gold OTC":"GC=F","WTI OTC":"CL=F","Brent OTC":"BZ=F"
}
def fix(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def zigzag_pivots(h,l,dev=5):
    pivots=[]; last_pivot=h[0]; last_type='H'
    for i in range(1,len(h)):
        if h[i]>=last_pivot*(1+dev/1000) and last_type=='L':
            pivots.append((i,'H',h[i])); last_pivot=h[i]; last_type='H'
        elif l[i]<=last_pivot*(1-dev/1000) and last_type=='H':
            pivots.append((i,'L',l[i])); last_pivot=l[i]; last_type='L'
        elif h[i]>last_pivot and last_type=='H': last_pivot=h[i]
        elif l[i]<last_pivot and last_type=='L': last_pivot=l[i]
    return pivots
def demarker(high,low,period=14):
    demax=np.maximum(high[1:]-high[:-1],0); demin=np.maximum(low[:-1]-low[1:],0)
    demax=np.concatenate([[0],demax]); demin=np.concatenate([[0],demin])
    sma_max=pd.Series(demax).rolling(period).mean(); sma_min=pd.Series(demin).rolling(period).mean()
    dem=(sma_max/(sma_max+sma_min+0.00001)).fillna(0.5)
    return dem

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V98 STORICO</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:18px;width:98%;max-width:440px;display:block;margin:8px auto;cursor:pointer}
.g{background:#00ff88;color:#000;border:3px solid #00ff88}.d{background:#222;color:#fff;border:2px solid #555}
.mode{background:#111;border:2px solid #00ff88;border-radius:12px;padding:10px;margin:10px auto;max-width:440px}
.mbtn{padding:10px 16px;border-radius:8px;font-weight:bold;margin:4px;cursor:pointer;border:2px solid #444}
.active{background:#00ff88;color:#000}.inactive{background:#222;color:#fff}
.card{background:#1e1e1e;border-radius:20px;padding:18px;margin:12px auto;max-width:460px;text-align:left;border-left:10px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}
.score{font-size:52px;font-weight:900}
.badge{position:absolute;top:14px;right:14px;text-align:right}
.prepara{background:#00ff88;color:#000;font-weight:bold;padding:12px;border-radius:10px;margin-top:10px;text-align:center}
.sellbg{background:#ff3b3b;color:#fff}
.storico{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:14px auto;max-width:460px;text-align:left;font-size:12px}
#s{padding:10px;border-radius:8px;margin:8px auto;max-width:440px;font-weight:bold}
.on{background:#00ff88;color:#000}.off{background:#ff3b3b;color:#fff}
</style></head><body>
<h2>✅ V98 - 70/85 + STORICO 2 MIN</h2>
<div id="s" class="off">🔇 SUONO OFF</div>
<div class="mode">
<button id="b70" class="mbtn active" onclick="setMode(70)">70 NORMALE</button>
<button id="b85" class="mbtn inactive" onclick="setMode(85)">85 STRICT</button>
</div>
<div class="btn g" onclick="att()">🔔 ATTIVA SUONO</div>
<div class="btn d" onclick="scan()">🔍 SCAN</div>
<p id="info">70 mode + storico</p><div id="live"></div>
<div class="storico"><b>📜 STORICO SEGNALI (ultimi 30):</b><div id="storico">Vuoto</div><div style="margin-top:8px"><span onclick="clearStor()" style="color:#ff3b3b;cursor:pointer">🗑️ Pulisci storico</span></div></div>
<script>
let ctx=null,ok=false,mode=70,expMin=2;
let stor=JSON.parse(localStorage.getItem('v98_stor')||'[]');
function updStor(){let h=''; stor.slice(0,30).forEach(s=>{h+=`<div>${s}</div>`}); document.getElementById('storico').innerHTML=h||'Vuoto';}
updStor();
function clearStor(){stor=[]; localStorage.setItem('v98_stor',JSON.stringify(stor)); updStor();}
function setMode(m){mode=m; document.getElementById('b70').className=m==70?'mbtn active':'mbtn inactive'; document.getElementById('b85').className=m==85?'mbtn active':'mbtn inactive'; scan();}
function att(){try{ctx=new (window.AudioContext||window.webkitAudioContext)(); ctx.resume(); ok=true; document.getElementById('s').className='on'; document.getElementById('s').innerText='🔊 ON 2 MIN mode '+mode; b(900,0.3); setTimeout(()=>b(1300,0.4),200); scan();}catch(e){}}
function b(f,d){if(!ctx) return; let o=ctx.createOscillator(),g=ctx.createGain(); o.frequency.value=f; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(1,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+d); o.start(); o.stop(ctx.currentTime+d);}
function suona(){if(!ok) return; b(1000,0.25); setTimeout(()=>b(1500,0.35),180); if(navigator.vibrate) navigator.vibrate([400,100,600]);}
let cur=[],ent=0; function getN(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMilliseconds(0); nx.setMinutes(n.getMinutes()+1); return nx;}
function scan(){document.getElementById('info').innerText='⏳ Scan...'; fetch('/api/scan?mode='+mode).then(r=>r.json()).then(d=>{cur=d.signals; ent=getN().getTime(); if(d.signals.length>0){suona(); let now=new Date().toLocaleTimeString('it-IT'); d.signals.forEach(s=>{stor.unshift(`${now} - ${s.score}/100 ${s.dir} ${s.pair} 2MIN`);}); localStorage.setItem('v98_stor',JSON.stringify(stor.slice(0,50))); updStor();} render();});}
function render(){let now=Date.now(); let diff=Math.ceil((ent-now)/1000); let tot=expMin*60; let h=''; if(diff>0) document.getElementById('info').innerText=`⏰ ${diff}s - ${cur.length} segnali`; cur.forEach(s=>{let col=s.dir=='BUY'?'#00ff88':'#ff3b3b'; let left=Math.max(0,tot+diff); let txt=diff>0?`ENTRA TRA ${diff}s - ${expMin} MIN`:`SCAD ${left}s`; h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><div class="badge"><div class="score" style="color:${col}">${s.score}/100</div><div style="color:${col};font-weight:900">${s.dir}</div></div><div style="width:58%"><b style="color:${col}">${s.pair}</b><br><span style="color:#aaa;font-size:12px">PIN ${s.ratio}x | ${s.zig}</span><br>${s.price}</div><div class="prepara ${s.dir=='SELL'?'sellbg':''}">${txt}</div></div>`;}); document.getElementById('live').innerHTML=h||`Nessun segnale mode ${mode}`;}
setInterval(render,1000); setInterval(scan,35000);
</script></body></html>"""

@app.route('/api/scan')
def api():
    from flask import request
    mode=int(request.args.get('mode',70))
    out=[]
    min_ratio=2.2 if mode==70 else 2.8
    min_score=mode
    zig_window=12 if mode==70 else 6
    dem_thr=0.6 if mode==70 else 0.7
    for otc, real in OTC_MAP.items():
        try:
            df=yf.download(real, period="2d", interval="1m", progress=False, auto_adjust=True)
            df=fix(df)
            if len(df)<200: continue
            h=df['High'].values; l=df['Low'].values; c=df['Close'].values; o=df['Open'].values
            pivots=zigzag_pivots(h,l,4 if mode==70 else 5)
            if len(pivots)<2 or len(df)-pivots[-1][0]>zig_window:
                del df; gc.collect()
                continue
            body=abs(c[-1]-o[-1])
            if body<0.00001: body=0.00001
            up=h[-1]-max(o[-1],c[-1]); down=min(o[-1],c[-1])-l[-1]
            dire=None; ratio=0
            if up>body*min_ratio and pivots[-1][1]=='H': dire="SELL"; ratio=up/body
            elif down>body*min_ratio and pivots[-1][1]=='L': dire="BUY"; ratio=down/body
            if not dire:
                del df; gc.collect()
                continue
            dem=demarker(h,l,14)
            dem_val=float(dem.iloc[-1])
            score=30
            score+=10 if ratio>=min_ratio else 0
            score+=10 if ratio>=2.8 else 0
            score+=10 if ratio>=3.5 else 0
            if (dire=="SELL" and dem_val>=dem_thr) or (dire=="BUY" and dem_val<=1-dem_thr): score+=20
            if pivots[-1][1]=='H' and dire=='SELL': score+=8
            if pivots[-1][1]=='L' and dire=='BUY': score+=8
            if score<min_score:
                del df; gc.collect()
                continue
            score=min(95,int(score))
            fmt=f"{c[-1]:.5f}" if "JPY" not in otc else f"{c[-1]:.2f}"
            out.append({"pair":otc,"dir":dire,"price":fmt,"score":score,"ratio":round(ratio,1),"zig":f"{pivots[-1][1]} {len(df)-pivots[-1][0]}c fa"})
            del df; gc.collect()
        except:
            gc.collect()
            continue
    out=sorted(out, key=lambda x: x['score'], reverse=True)[:12]
    return jsonify({"signals":out})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
