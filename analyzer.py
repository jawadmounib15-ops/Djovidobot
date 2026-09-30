# V65 VELOCE SICURO - FILTRA FALSI
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed
app = Flask(__name__)
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","NZDJPY=X","EURAUD=X","GBPAUD=X","CADJPY=X","CHFJPY=X","NZDCAD=X"]
def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.clip(lower=0).rolling(p).mean(); l=-d.clip(upper=0).rolling(p).mean()
    return 100-(100/(1+g/(l+1e-9)))
def check_pair(sym):
    try:
        df=yf.download(sym, period="5d", interval="15m", progress=False); df=fix_df(df)
        if len(df)<210: return None
        df['e200']=df['Close'].ewm(span=200).mean(); df['e20']=df['Close'].ewm(span=20).mean()
        df['atr']=(df['High']-df['Low']).rolling(14).mean(); df['atr_ma']=df['atr'].rolling(50).mean()
        df['rsi']=rsi(df['Close'],14)
        df['sk']=((df['Close']-df['Low'].rolling(14).min())/(df['High'].rolling(14).max()-df['Low'].rolling(14).min()+1e-9)*100).rolling(3).mean()
        last=df.iloc[-1]; o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
        e200=float(last['e200']); e20=float(last['e20']); atr=float(last['atr']); atr_ma=float(last['atr_ma']); r=float(last['rsi']); k=float(last['sk'])
        rng=h-l; body=abs(c-o)
        if rng==0 or atr_ma==0: return None
        if body > rng*0.45: return None # CORPO PIU PICCOLO
        up=h-max(o,c); down=min(o,c)-l
        if max(up,down) < body*2.5: return None # RATIO 2.5x non 1.8x
        if atr < atr_ma*0.6 or atr > atr_ma*2.0: return None # ATR 0.6-2.0 non 0.45-3.2
        if down>up: # BUY SICURO
            if c<e200: return None
            if not (30 <= r <= 36 and k < 20): return None # RSI 30-36 e Stoch <20
            sig="BUY"
        else: # SELL SICURO
            if c>e200: return None
            if not (64 <= r <= 70 and k > 80): return None # RSI 64-70 e Stoch >80
            sig="SELL"
        if abs(c-e20)/c > 0.003: return None # VICINO EMA20 0.3% non 0.8%
        return {"pair":sym.replace("=X",""),"dir":sig,"price":f"{c:.5f}","rsi":f"{r:.0f}","ratio":f"{max(up,down)/body:.1f}"}
    except: return None

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V65 SICURO</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:20px}
.btn{background:#00ff88;color:#000;border:none;padding:16px 28px;margin:10px;border-radius:14px;font-weight:bold;font-size:18px;width:85%;max-width:350px;display:block;margin:15px auto;cursor:pointer}
.card{background:#1a1a1a;border-radius:12px;padding:14px;margin:10px auto;max-width:380px;text-align:left;border-left:4px solid #00ff88}
</style></head><body>
<h1>✅ V65 VELOCE SICURO</h1><p style="color:#00ff88">18 coppie - Solo vincenti - Niente falsi</p>
<button class="btn" id="b1" onclick="attiva()">🔔 ATTIVA SUONO</button>
<button class="btn" onclick="cerca()">🔍 SCAN ORA</button>
<p id="info">Pronto...</p><div id="box"></div><p id="vuoto">Nessun segnale ora = mercato senza setup buoni - NORMALE</p>
<audio id="snd" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
let ok=false; let a=document.getElementById('snd');
function attiva(){ok=true; a.play().then(()=>a.pause()); document.getElementById('b1').innerHTML='🔔 SUONO ATTIVO'; document.getElementById('b1').style.background='#ffcc00';}
function cerca(){
 fetch('/api/scan').then(r=>r.json()).then(d=>{
  document.getElementById('info').innerText=d.time+' - Trovate: '+d.signals.length+' - '+d.elapsed;
  let h=''; if(d.signals.length>0){
   if(ok){a.play(); if(navigator.vibrate) navigator.vibrate([500,200,500,200,500]);}
   d.signals.forEach(s=>{h+=`<div class="card"><b style="color:${s.dir=='BUY'?'#00ff88':'#ff4d4d'}">${s.dir} ${s.pair} ${s.ratio}x</b> RSI:${s.rsi}<br>${s.price}<br><small>${d.time}</small></div>`});
   document.getElementById('box').innerHTML=h; document.getElementById('vuoto').style.display='none';
  } else {document.getElementById('box').innerHTML=''; document.getElementById('vuoto').style.display='block';}
 });}
setInterval(cerca,60000); window.onload=cerca;
</script></body></html>"""
@app.route('/api/scan')
def api():
    import time; t0=time.time(); tz=pytz.timezone('Europe/Rome'); now=datetime.now(tz).strftime('%H:%M:%S IT')
    out=[]
    with ThreadPoolExecutor(max_workers=18) as ex:
        futs={ex.submit(check_pair,s):s for s in PAIRS}
        for f in as_completed(futs):
            r=f.result()
            if r: out.append(r)
    return jsonify({"signals":out,"time":now,"elapsed":f"{time.time()-t0:.1f}s"})
if __name__=="__main__":
    import os; app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
