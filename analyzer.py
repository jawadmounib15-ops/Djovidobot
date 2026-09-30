# analyzer.py - V65 VELOCE LARGO - 18 COPPIE - 4 SECONDI
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","NZDJPY=X","EURAUD=X","GBPAUD=X","CADJPY=X","CHFJPY=X","NZDCAD=X"]

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

def rsi(series, p=14):
    d=series.diff(); g=d.clip(lower=0).rolling(p).mean(); l=-d.clip(upper=0).rolling(p).mean()
    return 100-(100/(1+g/(l+1e-9)))

def check_pair(sym):
    try:
        df=yf.download(sym, period="5d", interval="15m", progress=False); df=fix_df(df)
        if len(df)<210: return None
        df['e200']=df['Close'].ewm(span=200).mean()
        df['e20']=df['Close'].ewm(span=20).mean()
        df['atr']=(df['High']-df['Low']).rolling(14).mean()
        df['atr_ma50']=df['atr'].rolling(50).mean()
        df['rsi']=rsi(df['Close'],14)
        df['stoch_k']=((df['Close']-df['Low'].rolling(14).min())/(df['High'].rolling(14).max()-df['Low'].rolling(14).min()+1e-9)*100).rolling(3).mean()
        
        last=df.iloc[-1]
        o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
        e200=float(last['e200']); e20=float(last['e20']); atr=float(last['atr']); atr_ma=float(last['atr_ma50'])
        rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
        rng=h-l; body=abs(c-o)
        if rng==0 or atr_ma==0: return None
        # FILTRO BODY
        if body > rng*0.55: return None
        up=h-max(o,c); down=min(o,c)-l
        if max(up,down) < body*1.8: return None
        # FILTRO ATR LARGO 0.45 - 3.2
        if atr < atr_ma*0.45 or atr > atr_ma*3.2: return None
        
        # REGOLA BUY/SELL LARGO TUA
        if down>up: # BUY
            if c < e200: return None
            if not (25 <= rsi_v <= 45 and stoch_k < 28): return None
            sig="BUY"
        else: # SELL
            if c > e200: return None
            if not (55 <= rsi_v <= 75 and stoch_k > 72): return None
            sig="SELL"
        
        # Vicinanza e20
        if abs(c-e20)/c > 0.008: return None

        return {"pair": sym.replace("=X",""), "dir": sig, "price": f"{c:.5f}", "rsi": f"{rsi_v:.0f}", "ratio": f"{max(up,down)/body:.1f}"}
    except:
        return None

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V65 VELOCE</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:20px}
.btn{background:#00ff88;color:#000;border:none;padding:16px 28px;margin:10px;border-radius:14px;font-weight:bold;font-size:18px;width:85%;max-width:350px;display:block;margin:15px auto;cursor:pointer}
.card{background:#1a1a1a;border-radius:12px;padding:14px;margin:10px auto;max-width:380px;text-align:left;border-left:4px solid #00ff88}
</style></head><body>
<h1>⚡ V65 VELOCE LARGO</h1><p style="color:#00ff88">18 coppie - 4 secondi - Tue regole</p>
<button class="btn" id="b1" onclick="attiva()">🔔 ATTIVA SUONO</button>
<button class="btn" onclick="cerca()">🔍 SCAN ORA</button>
<p id="info">Pronto...</p><div id="box"></div><p id="vuoto">Nessuna pinbar ora - mercato chiuso alle 20:30 è normale</p>
<audio id="snd" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
let ok=false; let a=document.getElementById('snd');
function attiva(){ok=true; a.play().then(()=>a.pause()); document.getElementById('b1').innerHTML='🔔 SUONO ATTIVO - Pronto'; document.getElementById('b1').style.background='#ffcc00';}
function cerca(){
 document.getElementById('info').innerText='Scansiono 18 coppie...'; 
 fetch('/api/scan').then(r=>r.json()).then(d=>{
  document.getElementById('info').innerText=d.time+' - Trovate: '+d.signals.length+' - '+d.elapsed;
  let h=''; if(d.signals.length>0){
   if(ok){a.play(); if(navigator.vibrate) navigator.vibrate([500,200,500,200,500]);}
   d.signals.forEach(s=>{h+=`<div class="card"><b style="color:${s.dir=='BUY'?'#00ff88':'#ff4d4d'}">${s.dir} ${s.pair} ${s.ratio}x</b> RSI:${s.rsi}<br>${s.price}<br><small>${d.time}</small></div>`});
   document.getElementById('box').innerHTML=h; document.getElementById('vuoto').style.display='none';
  } else {document.getElementById('box').innerHTML=''; document.getElementById('vuoto').style.display='block';}
 });
}
setInterval(cerca,60000); window.onload=cerca;
</script></body></html>"""

@app.route('/api/scan')
def api():
    import time; t0=time.time()
    tz=pytz.timezone('Europe/Rome'); now=datetime.now(tz).strftime('%H:%M:%S IT')
    out=[]
    with ThreadPoolExecutor(max_workers=18) as ex:
        futs={ex.submit(check_pair, s): s for s in PAIRS}
        for f in as_completed(futs):
            r=f.result()
            if r: out.append(r)
    elapsed=f"{time.time()-t0:.1f}s"
    return jsonify({"signals": out, "time": now, "elapsed": elapsed})

if __name__=="__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
