import yfinance as yf, pandas as pd
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Coppie che funzionano anche weekend
PAIRS = [
    ("BTC-USD","BTC/USD-OTC"), ("ETH-USD","ETH/USD-OTC"), ("SOL-USD","SOL/USD-OTC"),
    ("EURUSD=X","EUR/USD-OTC"), ("GBPUSD=X","GBP/USD-OTC"), ("USDJPY=X","USD/JPY-OTC"),
    ("AUDUSD=X","AUD/USD-OTC"), ("EURJPY=X","EUR/JPY-OTC"), ("GBPJPY=X","GBP/JPY-OTC"),
]

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pocket Analyzer 5M</title>
<style>
body{background:#0e0e10;color:#fff;font-family:system-ui;padding:15px}
.card{background:#1a1a1f;padding:15px;border-radius:14px;margin:10px 0;display:flex;justify-content:space-between;border-left:5px solid #00c853}
.sell{border-left-color:#ff1744} .wait{border-left-color:#444}
.badge{padding:6px 12px;border-radius:20px;font-weight:bold;background:#00c853;color:#000}
.badge.s{background:#ff1744;color:#fff}
</style></head><body>
<h2>💎 POCKET OPTION - MERCATO COMPLETO 5M SICURO</h2>
<p id="clock"></p>
<div id="market">Scansiono mercato... (15 sec)</div>
<script>
async function scan(){
  try{
    let r=await fetch('/api/scan'); let data=await r.json();
    let html=''; 
    if(data.length==0) html='<div class=card><b>Nessun segnale forte adesso - Mercato in attesa (Domenica pochi movimenti). Controllo ogni 15s...</b></div>';
    data.forEach(c=>{
      let cls=c.action=='SELL'?'card sell':'card';
      let b=c.action=='SELL'?'badge s':'badge';
      html+=`<div class="${cls}"><div><b>${c.pair}</b><br><small>${c.reason}<br>RSI ${c.rsi} | Prezzo ${c.price} | Score ${c.score}</small></div><div><span class="${b}">${c.action} ${c.score}%</span></div></div>`;
    });
    document.getElementById('market').innerHTML=html;
    document.getElementById('clock').innerText=new Date().toLocaleTimeString() + ' - Aggiorno ogni 15s';
  }catch(e){document.getElementById('market').innerHTML='Connessione lenta, riprovo...';}
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
            df=yf.download(yahoo, period="2d", interval="5m", progress=False, auto_adjust=False)
            if len(df)<50: continue
            if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
            df['EMA9']=df['Close'].ewm(9).mean(); df['EMA21']=df['Close'].ewm(21).mean()
            delta=df['Close'].diff(); g=delta.where(delta>0,0).ewm(14).mean(); l=-delta.where(delta<0,0).ewm(14).mean()
            df['RSI']=100-(100/(1+g/l))
            last=df.iloc[-1]
            c=float(last['Close']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); rsi=float(last['RSI'])
            score=0; action="WAIT"; reason=""
            if ema9>ema21 and 25<=rsi<=50:
                score=75; action="BUY"; reason="Trend BUY + RSI ottimo 5M"
            elif ema9<ema21 and 50<=rsi<=75:
                score=75; action="SELL"; reason="Trend SELL + RSI ottimo 5M"
            if score>=60:
                res.append({"pair":label,"action":action,"score":score,"rsi":round(rsi,1),"price":round(c,4),"reason":reason})
        except: continue
    res=sorted(res, key=lambda x:x['score'], reverse=True)[:10]
    return jsonify(res)

if __name__=='__main__':
    app.run(host="0.0.0.0", port=10000)
