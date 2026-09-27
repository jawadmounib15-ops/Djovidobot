# ANALYZER POCKET OPTION - MERCATO COMPLETO 5M SICURO - FILE SEPARATO
import yfinance as yf, pandas as pd, time
from flask import Flask, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)

PAIRS = [
    ("EURUSD=X","EUR/USD-OTC"), ("GBPUSD=X","GBP/USD-OTC"), ("USDJPY=X","USD/JPY-OTC"),
    ("AUDUSD=X","AUD/USD-OTC"), ("EURJPY=X","EUR/JPY-OTC"), ("GBPJPY=X","GBP/JPY-OTC"),
    ("USDCHF=X","USD/CHF-OTC"), ("EURGBP=X","EUR/GBP-OTC"), ("AUDJPY=X","AUD/JPY-OTC"),
    ("CHFJPY=X","CHF/JPY-OTC"), ("EURUSD=X","EUR/USD"), ("GBPUSD=X","GBP/USD")
]

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pocket Analyzer 5M</title>
<style>
body{background:#0e0e10;color:#fff;font-family:system-ui;padding:15px}
.card{background:#1a1a1f;padding:15px;border-radius:14px;margin:10px 0;display:flex;justify-content:space-between}
.buy{border-left:5px solid #00c853} .sell{border-left:5px solid #ff1744} .wait{border-left:5px solid #444}
.top{border:2px solid gold} .badge{padding:6px 12px;border-radius:20px;font-weight:bold}
</style></head><body>
<h2>💎 POCKET OPTION - MERCATO COMPLETO 5M SICURO</h2>
<p id="clock"></p>
<div id="market">Scansiono...</div>
<script>
async function scan(){
  let r=await fetch('/api/scan'); let data=await r.json();
  let html=''; data.forEach(c=>{
    let cls=c.action=='BUY'?'buy':c.action=='SELL'?'sell':'wait';
    let top=c.score>=85?'top':'';
    html+=`<div class="card ${cls} ${top}"><div><b>${c.pair}</b><br><small>${c.reason}<br>RSI ${c.rsi} | Score ${c.score}/100</small></div><div><span class="badge">${c.action} ${c.score}%</span></div></div>`;
  });
  document.getElementById('market').innerHTML=html;
  document.getElementById('clock').innerText=new Date().toLocaleTimeString();
}
scan(); setInterval(scan,15000);
</script></body></html>
"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/api/scan')
def api_scan():
    res=[]
    for yahoo,label in PAIRS:
        try:
            df=yf.download(yahoo, period="3d", interval="5m", progress=False, auto_adjust=False)
            if len(df)<80: continue
            if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
            df['EMA9']=df['Close'].ewm(9).mean(); df['EMA21']=df['Close'].ewm(21).mean()
            df['EMA50']=df['Close'].ewm(50).mean()
            delta=df['Close'].diff(); g=delta.where(delta>0,0).ewm(14).mean(); l=-delta.where(delta<0,0).ewm(14).mean()
            df['RSI']=100-(100/(1+g/l))
            last=df.iloc[-1]
            c=float(last['Close']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50']); rsi=float(last['RSI'])
            
            score=0; action="WAIT"; reason=""
            if ema9>ema21>ema50 and c>ema9 and 30<=rsi<=45:
                score=80+int((45-rsi)); action="BUY"; reason="Trend BUY forte + RSI perfetto"
            elif ema9<ema21<ema50 and c<ema9 and 55<=rsi<=70:
                score=80+int((rsi-55)); action="SELL"; reason="Trend SELL forte + RSI perfetto"
            elif ema9>ema21 and c>ema21 and 35<=rsi<=50:
                score=65; action="BUY"; reason="Trend BUY medio"
            elif ema9<ema21 and c<ema21 and 50<=rsi<=65:
                score=65; action="SELL"; reason="Trend SELL medio"
            
            if score>=65:
                res.append({"pair":label,"action":action,"score":score,"rsi":round(rsi),"reason":reason,"type":action.lower()})
        except: continue
    res=sorted(res, key=lambda x:x['score'], reverse=True)[:10]
    return jsonify(res)

if __name__=='__main__':
    app.run(host="0.0.0.0", port=10000)
