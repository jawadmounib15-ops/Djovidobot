# analyzer.py - V96 2 MIN EFFICACE ZIGZAG + PINBAR 85/100
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
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def zigzag_pivots(h,l,dev=5):
    pivots=[]
    last_pivot=h[0]
    last_type='H'
    for i in range(1,len(h)):
        if h[i]>=last_pivot*(1+dev/1000) and last_type=='L':
            pivots.append((i,'H',h[i]))
            last_pivot=h[i]
            last_type='H'
        elif l[i]<=last_pivot*(1-dev/1000) and last_type=='H':
            pivots.append((i,'L',l[i]))
            last_pivot=l[i]
            last_type='L'
        elif h[i]>last_pivot and last_type=='H':
            last_pivot=h[i]
        elif l[i]<last_pivot and last_type=='L':
            last_pivot=l[i]
    return pivots

def demarker(high,low,period=14):
    demax=np.maximum(high[1:]-high[:-1],0)
    demin=np.maximum(low[:-1]-low[1:],0)
    demax=np.concatenate([[0],demax])
    demin=np.concatenate([[0],demin])
    sma_max=pd.Series(demax).rolling(period).mean()
    sma_min=pd.Series(demin).rolling(period).mean()
    dem=(sma_max/(sma_max+sma_min+0.00001)).fillna(0.5)
    return dem

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>analyzer.py V96 2MIN</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:22px;border-radius:18px;font-weight:bold;font-size:20px;width:98%;max-width:440px;display:block;margin:10px auto;cursor:pointer}
.g{background:#00ff88;color:#000;border:3px solid #00ff88}.d{background:#222;color:#fff;border:2px solid #555}
.card{background:#1e1e1e;border-radius:20px;padding:18px;margin:14px auto;max-width:460px;text-align:left;border-left:10px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}
.score{font-size:56px;font-weight:900}
.badge{position:absolute;top:14px;right:14px;text-align:right}
.prepara{background:#00ff88;color:#000;font-weight:bold;padding:14px;border-radius:12px;margin-top:12px;text-align:center;font-size:18px}
.prepara.sellbg{background:#ff3b3b;color:#fff}
#s{padding:12px;border-radius:10px;margin:10px auto;max-width:440px;font-weight:bold}
.on{background:#00ff88;color:#000}.off{background:#ff3b3b;color:#fff}
.info{color:#aaa;font-size:13px}
</style></head><body>
<h2>✅ analyzer.py V96 - 2 MIN</h2>
<div id="s" class="off">🔇 SUONO OFF</div>
<div class="btn g" onclick="att()">🔔 ATTIVA SUONO 2 MIN</div>
<div class="btn d" onclick="scan()">🔍 SCAN 85/100</div>
<p id="info">2 MIN - 85/100 solo</p><div id="live"></div>
<script>
let ctx=null,ok=false,expMin=2;
function att(){try{ctx=new (window.AudioContext||window.webkitAudioContext)(); ctx.resume(); ok=true; document.getElementById('s').className='on'; document.getElementById('s').innerText='🔊 ON 2 MIN'; b(900,0.3); setTimeout(()=>b(1300,0.4),200); scan();}catch(e){}}
function b(f,d){if(!ctx) return; let o=ctx.createOscillator(),g=ctx.createGain(); o.frequency.value=f; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(1,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+d); o.start(); o.stop(ctx.currentTime+d);}
function suona(){if(!ok) return; b(1000,0.25); setTimeout(()=>b(1500,0.35),180); setTimeout(()=>b(1000,0.4),400); if(navigator.vibrate) navigator.vibrate([500,100,800]);}
let cur=[],ent=0; function getN(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMilliseconds(0); nx.setMinutes(n.getMinutes()+1); return nx;}
function scan(){document.getElementById('info').innerText='⏳ Scan 2 MIN...'; fetch('/api/scan').then(r=>r.json()).then(d=>{cur=d.signals; ent=getN().getTime(); if(d.signals.length>0) suona(); render();});}
function render(){let now=Date.now(); let diff=Math.ceil((ent-now)/1000); let tot=expMin*60; let h=''; if(diff>0) document.getElementById('info').innerText=`⏰ ${diff}s - ${expMin} MIN`; else if(diff>-tot) document.getElementById('info').innerText=`✅ IN CORSO ${tot+diff}s`; cur.forEach(s=>{let col=s.dir=='BUY'?'#00ff88':'#ff3b3b'; let left=Math.max(0,tot+diff); let txt=diff>0?`ENTRA TRA ${diff}s - ${expMin} MIN`:`SCAD ${left}s`; h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><div class="badge"><div class="score" style="color:${col}">${s.score}/100</div><div style="color:${col};font-weight:900">${s.dir}</div></div><div style="width:60%"><b style="color:${col}">${s.pair}</b><div class="info">PIN ${s.ratio}x | ${s.zig}</div><div class="info">DeM ${s.dem}</div><div class="info">${s.price}</div></div><div class="prepara ${s.dir=='SELL'?'sellbg':''}">${txt}</div></div>`;}); document.getElementById('live').innerHTML=h||'Nessun 85/100 2 MIN';}
setInterval(render,1000); setInterval(scan,35000);
</script></body></html>"""

@app.route('/api/scan')
def api():
    out=[]
    for otc, real in OTC_MAP.items():
        try:
            df=yf.download(real, period="2d", interval="1m", progress=False, auto_adjust=True)
            df=fix(df)
            if len(df)<210: continue
            h=df['High'].values; l=df['Low'].values; c=df['Close'].values; o=df['Open'].values
            pivots=zigzag_pivots(h,l,5)
            if len(pivots)<2 or len(df)-pivots[-1][0]>5:
                del df; gc.collect()
                continue
            last_idx,last_type,last_price=pivots[-1]
            body=abs(c[-1]-o[-1])
            if body<0.00001: body=0.00001
            up=h[-1]-max(o[-1],c[-1]); down=min(o[-1],c[-1])-l[-1]
            dire=None; ratio=0
            if up>body*2.8 and last_type=='H': dire="SELL"; ratio=up/body
            elif down>body*2.8 and last_type=='L': dire="BUY"; ratio=down/body
            if not dire:
                del df; gc.collect()
                continue
            dem=demarker(h,l,14)
            dem_val=float(dem.iloc[-1])
            score=25
            score+=15 if ratio>=2.8 else 0
            score+=15 if ratio>=3.5 else 0
            if (dire=="SELL" and dem_val>=0.7) or (dire=="BUY" and dem_val<=0.3): score+=25
            if last_type=='H' and dire=='SELL': score+=10
            if last_type=='L' and dire=='BUY': score+=10
            if score<82:
                del df; gc.collect()
                continue
            score=min(95,score)
            fmt=f"{c[-1]:.5f}" if "JPY" not in otc else f"{c[-1]:.2f}"
            out.append({"pair":otc,"dir":dire,"price":fmt,"score":score,"ratio":round(ratio,1),"zig":f"{last_type} ZigZag","dem":f"{dem_val:.2f}"})
            del df; gc.collect()
        except:
            gc.collect()
            continue
    out=sorted(out, key=lambda x: x['score'], reverse=True)
    return jsonify({"signals":out})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
