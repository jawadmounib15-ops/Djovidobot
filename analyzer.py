# analyzer.py - V65 APP SCANNER PERFETTA - LARGO TEST
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz

app = Flask(__name__)

MODE = "LENTO" # OGGI LARGO PER TESTARE - domani MEDIO
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","NZDJPY=X","EURAUD=X","GBPAUD=X","CADJPY=X","CHFJPY=X","NZDCAD=X"]

SETTINGS = {
    "LENTO": {"rsi_buy": (20,42), "rsi_sell": (58,80), "sto_buy": 26, "sto_sell": 74, "tocco": 0.0022, "ratio": 1.8, "cooldown": 5400},
    "MEDIO": {"rsi_buy": (24,38), "rsi_sell": (62,76), "sto_buy": 18, "sto_sell": 82, "tocco": 0.0015, "ratio": 2.2, "cooldown": 9000},
    "SICURO": {"rsi_buy": (26,36), "rsi_sell": (64,74), "sto_buy": 20, "sto_sell": 80, "tocco": 0.0012, "ratio": 2.5, "cooldown": 12600},
}
CFG = SETTINGS[MODE]

last_scan = "Mai"
last_results = []

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1); return tr.rolling(p).mean()
def stoch(df,k=14):
    return 100*((df['Close']-df['Low'].rolling(k).min())/(df['High'].rolling(k).max()-df['Low'].rolling(k).min()))

def scan_logic():
    global last_scan, last_results
    tz = pytz.timezone('Europe/Rome')
    last_scan = datetime.now(tz).strftime('%H:%M:%S IT')
    signals = []
    for symbol in PAIRS:
        try:
            df15=yf.download(symbol, period="5d", interval="15m", progress=False); df15=fix_df(df15)
            if len(df15)<210: continue
            df15['e20']=df15['Close'].ewm(span=20).mean(); df15['e200']=df15['Close'].ewm(span=200).mean()
            df15['rsi']=rsi(df15['Close']); df15['atr']=atr(df15,14); df15['atr_ma']=df15['atr'].rolling(50).mean(); df15['sto']=stoch(df15,14)
            df60=yf.download(symbol, period="20d", interval="60m", progress=False); df60=fix_df(df60); df60['e200']=df60['Close'].ewm(span=200).mean()
            last=df15.iloc[-1]; last60=df60.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); sto_v=float(last['sto'])
            e20=float(last['e20']); e200=float(last['e200']); e200_60=float(last60['e200'])
            # 1. TREND 1H + 15M
            if not ((price>e200_60 and price>e200) or (price<e200_60 and price<e200)): continue
            # 5. ATR
            if last['atr'] < last['atr_ma']*0.70 or last['atr'] > last['atr_ma']*2.0: continue
            # 2. TOCCO EMA 0.22%
            if abs(price-e20)/price > CFG["tocco"]: continue
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
            body=abs(c-o); rng=h-l
            if rng==0 or body < rng*0.07 or body > rng*0.30: continue
            up=h-max(o,c); down=min(o,c)-l; ratio=max(up,down)/body if body>0 else 0
            # 3. PINBAR 1.8x
            if ratio < CFG["ratio"] or min(up,down) > rng*0.22: continue
            # 4. RSI + STO
            sig=None
            if price>e200 and down>up and CFG["rsi_buy"][0] <= rsi_v <= CFG["rsi_buy"][1] and sto_v < CFG["sto_buy"]: sig="BUY"
            if price<e200 and up>down and CFG["rsi_sell"][0] <= rsi_v <= CFG["rsi_sell"][1] and sto_v > CFG["sto_sell"]: sig="SELL"
            if sig:
                signals.append({"pair": symbol.replace("=X",""), "dir": sig, "price": f"{price:.5f}", "rsi": int(rsi_v), "sto": int(sto_v), "ratio": f"{ratio:.1f}"})
        except: continue
    last_results = signals
    return signals

@app.route('/')
def home():
    return """
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V65 PERFETTA</title>
<style>
body{background:#0e0e0e;color:white;font-family:Arial;text-align:center;padding:20px;margin:0}
h1{font-size:28px;margin:20px 0}
.sub{color:#888;font-size:15px;margin-bottom:20px}
.btn{border:none;padding:16px 28px;margin:10px auto;border-radius:14px;font-weight:bold;font-size:18px;cursor:pointer;width:85%;max-width:340px;display:block}
.green{background:#00ff88;color:#000}
.card{background:#1e1e1e;border-radius:12px;padding:14px;margin:10px auto;max-width:360px;text-align:left;border-left:4px solid #00ff88}
.buy{color:#00ff88;font-weight:bold}.sell{color:#ff4d4d;font-weight:bold}
#info{margin:15px;color:#fff}
</style></head><body>
<h1>🔥 V65 PERFETTA</h1>
<div class="sub">""" + f"{CFG['ratio']}x-6x | RSI filtrato | {MODE} largo | vedi su Quotex" + """</div>
<button class="btn green" id="soundBtn" onclick="attivaSuono()">🔇 ATTIVA SUONO</button>
<button class="btn green" onclick="scanOra()">🔍 SCAN ORA</button>
<div id="info">Ultima: """ + last_scan + f" - Trovata: {len(last_results)} perfette</div>" + """
<div id="list"></div>
<p id="empty" style="color:#777;margin-top:30px">Nessuna pinbar PERFETTA ora<br>Quando appare, la vedi anche su Quotex</p>
<audio id="alarm" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto" loop></audio>
<script>
let suono=false; let audio=document.getElementById('alarm');
function attivaSuono(){
 suono=true;
 audio.play().then(()=>{audio.pause(); audio.currentTime=0; document.getElementById('soundBtn').innerHTML='🔔 SUONO ATTIVO - ALLARME ON';});
 if(navigator.vibrate) navigator.vibrate(200);
}
function scanOra(){
 document.getElementById('info').innerText='Scansione in corso...';
 fetch('/api/scan').then(r=>r.json()).then(d=>{
  document.getElementById('info').innerText='Ultima: '+d.time+' - Trovate: '+d.signals.length+' perfette';
  let html='';
  if(d.signals.length>0){
   if(suono){ audio.play(); if(navigator.vibrate) navigator.vibrate([500,200,500,200,500]); setTimeout(()=>{audio.pause()}, 4000); }
   d.signals.forEach(s=>{
    let col = s.dir=='BUY'? 'buy' : 'sell';
    html+=`<div class="card"><span class="${col}">${s.dir} ${s.pair}</span> - ${s.ratio}x<br>RSI ${s.rsi} STO ${s.sto} | Entry ${s.price}<br><small>Scad 15m - ${d.time}</small></div>`;
   });
   document.getElementById('list').innerHTML=html;
   document.getElementById('empty').style.display='none';
  } else {
   document.getElementById('list').innerHTML='';
   document.getElementById('empty').style.display='block';
  }
 });
}
setInterval(scanOra, 60000);
window.onload=scanOra;
</script></body></html>
"""

@app.route('/api/scan')
def api():
    s = scan_logic()
    return jsonify({"time": last_scan, "signals": s})

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
