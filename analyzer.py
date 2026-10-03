# V96 - 2 MIN SCADENZA + 85/100 + TRACK % VINCENTE REALE
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
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V96 2MIN</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:22px;border-radius:18px;font-weight:bold;font-size:20px;width:98%;max-width:440px;display:block;margin:10px auto;cursor:pointer}
.g{background:#00ff88;color:#000;border:3px solid #00ff88}.d{background:#222;color:#fff;border:2px solid #555}.b{background:#1a1a1a;color:#ffcc00;border:2px solid #ffcc00}
.card{background:#1e1e1e;border-radius:20px;padding:18px;margin:14px auto;max-width:460px;text-align:left;border-left:10px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}
.score{font-size:56px;font-weight:900}
.badge{position:absolute;top:14px;right:14px;text-align:right}
.decide{background:#111;border:2px dashed #ffcc00;border-radius:12px;padding:12px;margin-top:12px;text-align:center;font-weight:bold;color:#ffcc00}
.prepara{background:#00ff88;color:#000;font-weight:bold;padding:14px;border-radius:12px;margin-top:12px;text-align:center;font-size:18px}
.prepara.sellbg{background:#ff3b3b;color:#fff}
#s{padding:12px;border-radius:10px;margin:10px auto;max-width:440px;font-weight:bold}
.on{background:#00ff88;color:#000}.off{background:#ff3b3b;color:#fff}
.info{color:#aaa;font-size:13px}
.winbox{background:#111;border:2px solid #00ff88;border-radius:12px;padding:12px;margin:12px auto;max-width:460px}
.wbtn{padding:10px 18px;border-radius:8px;font-weight:bold;margin:5px;cursor:pointer;border:none;font-size:16px}
.w{background:#00ff88;color:#000}.l{background:#ff3b3b;color:#fff}
</style></head><body>
<h2>✅ V96 - 2 MIN + 85/100</h2><p style="color:#888">2 min più vincente di 1 min per pinbar</p>
<div id="s" class="off">🔇 SUONO OFF - Clicca ATTIVA</div>
<div class="btn g" onclick="att()">🔔 ATTIVA SUONO + SCAN 2 MIN</div>
<div class="btn d" onclick="scan()">🔍 SCAN 85/100 SOLO</div>
<div class="btn b" onclick="toggleExp()">⏱️ SCADENZA: <span id="expTxt">2 MIN</span> - CLICCA PER CAMBIARE</div>
<div class="winbox"><b>📊 % VINCENTE REALE (tu segni):</b><br><span id="stats">0 trade - 0% win</span><br><button class="wbtn w" onclick="addWin()">✅ WIN</button><button class="wbtn l" onclick="addLoss()">❌ LOSS</button><button class="wbtn" style="background:#333;color:#fff" onclick="resetStats()">🗑️ Reset</button></div>
<p id="info">Solo 85+ per puntare a 70-75% win</p><div id="live"></div>
<script>
let ctx=null,ok=false,expMin=2;
let wins=parseInt(localStorage.getItem('v96_wins')||'0'); let losses=parseInt(localStorage.getItem('v96_losses')||'0');
function updStats(){let tot=wins+losses; let perc=tot>0?Math.round(wins/tot*100):0; document.getElementById('stats').innerText=`${tot} trade - ${wins} WIN / ${losses} LOSS = ${perc}% WIN`; localStorage.setItem('v96_wins',wins); localStorage.setItem('v96_losses',losses);}
updStats();
function addWin(){wins++; updStats();} function addLoss(){losses++; updStats();} function resetStats(){wins=0; losses=0; updStats();}
function toggleExp(){expMin=expMin==1?2:expMin==2?3:1; document.getElementById('expTxt').innerText=expMin+' MIN'; render();}
function att(){try{ctx=new (window.AudioContext||window.webkitAudioContext)(); ctx.resume(); ok=true; document.getElementById('s').className='on'; document.getElementById('s').innerText='🔊 ON - 2 MIN'; b(900,0.3); setTimeout(()=>b(1300,0.4),200); scan();}catch(e){}}
function b(f,d){if(!ctx) return; let o=ctx.createOscillator(),g=ctx.createGain(); o.frequency.value=f; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(1,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+d); o.start(); o.stop(ctx.currentTime+d);}
function suona(){if(!ok) return; if(ctx&&ctx.state=='suspended') ctx.resume(); b(1000,0.25); setTimeout(()=>b(1500,0.35),180); setTimeout(()=>b(1000,0.4),400); if(navigator.vibrate) navigator.vibrate([500,100,800]);}
let cur=[],ent=0; function getN(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMilliseconds(0); nx.setMinutes(n.getMinutes()+1); return nx;}
function scan(){document.getElementById('info').innerText='⏳ Cerco 85/100 2 MIN...'; fetch('/api/scan').then(r=>r.json()).then(d=>{cur=d.signals; ent=getN().getTime(); if(d.signals.length>0) suona(); render();});}
function render(){let now=Date.now(); let diff=Math.ceil((ent-now)/1000); let totSec=expMin*60; let h=''; if(diff>40) document.getElementById('info').innerText=`⏰ Entra tra ${diff}s - scadenza ${expMin} MIN`; else if(diff>0) document.getElementById('info').innerText=`🔥 PREPARA ${diff}s - ${expMin} MIN`; else if(diff>-totSec) document.getElementById('info').innerText=`✅ TRADE 2 MIN IN CORSO - scade ${totSec+diff}s`; cur.forEach(s=>{let col=s.dir=='BUY'?'#00ff88':'#ff3b3b'; let left=Math.max(0,totSec+diff); let txt=diff>0?`ENTRA TRA ${diff} SEC - SCAD ${expMin} MIN`:`IN CORSO - SCAD ${left}s / ${totSec}s`; h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><div class="badge"><div class="score" style="color:${col}">${s.score}/100</div><div style="color:${col};font-weight:900">${s.dir}</div><div style="font-size:11px">2 MIN</div></div><div style="width:60%"><b style="font-size:20px;color:${col}">${s.pair}</b><div class="info">ZIGZAG TOP/BOTTOM + PIN ${s.ratio}x</div><div class="info">DeM ${s.dem} - per 2 MIN meglio</div><div class="info">Prezzo: ${s.price}</div></div><div class="prepara ${s.dir=='SELL'?'sellbg':''}">${txt}</div><div class="decide">TU DECIDI - ${s.score}% + 2 MIN = più tempo per vincere<br>Dopo segna WIN/LOSS sopra per % reale</div></div>`;}); document.getElementById('live').innerHTML=h||'Nessun 85/100 ora - aspetta pinbar grossa come foto';}
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
            if len(pivots)<2:
                del df; gc.collect()
                continue
            last_idx,last_type,last_price=pivots[-1]
            if len(df)-last_idx>5:
                del df; gc.collect()
                continue
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
            dem_val=float(dem.iloc[-1]) if hasattr(dem,'iloc') else float(dem[-1])
            ema200=float(pd.Series(c).ewm(200).mean().iloc[-1])
            score=25
            score+=15 if ratio>=2.8 else 0
            score+=15 if ratio>=3.5 else 0
            if (dire=="SELL" and dem_val>=0.7) or (dire=="BUY" and dem_val<=0.3): score+=25
            elif (dire=="SELL" and dem_val>=0.6) or (dire=="BUY" and dem_val<=0.4): score+=12
            if last_type=='H' and dire=='SELL': score+=10
            if last_type=='L' and dire=='BUY': score+=10
            # filtro più duro per 2 min
            if score<82:
                del df; gc.collect()
                continue
            if score>95: score=95
            fmt=f"{c[-1]:.5f}" if "JPY" not in otc and "OTC" in otc and len(otc)<12 else f"{c[-1]:.2f}"
            out.append({"pair":otc,"dir":dire,"price":fmt,"score":score,"ratio":round(ratio,1),"dem":f"{dem_val:.2f}"})
            del df; gc.collect()
        except:
            gc.collect()
            continue
    out=sorted(out, key=lambda x: x['score'], reverse=True)
    return jsonify({"signals":out})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
