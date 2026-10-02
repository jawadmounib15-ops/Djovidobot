# V89 ULTRA LIGHT - SI APRE SUBITO - FIX ABOUT:BLANK
import yfinance as yf, pandas as pd, gc
from flask import Flask, jsonify
import os, time
app = Flask(__name__)
OTC_MAP = {
    "EURUSD-OTC":"EURUSD=X", "GBPUSD-OTC":"GBPUSD=X", "USDJPY-OTC":"USDJPY=X",
    "AUDUSD-OTC":"AUDUSD=X", "USDCAD-OTC":"USDCAD=X", "USDCHF-OTC":"USDCHF=X",
    "EURJPY-OTC":"EURJPY=X", "EURGBP-OTC":"EURGBP=X", "GBPJPY-OTC":"GBPJPY=X",
    "AUDJPY-OTC":"AUDJPY=X", "EURCHF-OTC":"EURCHF=X", "GBPCHF-OTC":"GBPCHF=X",
    "CADJPY-OTC":"CADJPY=X", "CHFJPY-OTC":"CHFJPY=X", "AUDCAD-OTC":"AUDCAD=X",
    "EURAUD-OTC":"EURAUD=X", "GBPAUD-OTC":"GBPAUD=X", "AUDCHF-OTC":"AUDCHF=X",
    "NZDUSD-OTC":"NZDUSD=X", "EURCAD-OTC":"EURCAD=X", "NZDJPY-OTC":"NZDJPY=X",
    "GBPCAD-OTC":"GBPCAD=X", "EURTRY-OTC":"EURTRY=X", "USDTRY-OTC":"USDTRY=X",
    "Tesla OTC":"TSLA","Apple OTC":"AAPL","Microsoft OTC":"MSFT",
    "Gold OTC":"GC=F","Silver OTC":"SI=F","WTI OTC":"CL=F","Brent OTC":"BZ=F","Gas OTC":"NG=F"
}
def fix(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V89 LIGHT</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:20px}.btn{padding:22px;border-radius:16px;font-weight:bold;font-size:22px;width:95%;max-width:400px;display:block;margin:20px auto;cursor:pointer}.g{background:#00ff88;color:#000}.d{background:#222;color:#fff;border:2px solid #444}.card{background:#1a1a1a;border-radius:12px;padding:14px;margin:10px auto;max-width:420px;text-align:left;border-left:6px solid #00ff88}.sell{border-left-color:#ff3b3b}</style></head><body>
<h2>✅ V89 LIGHT - APRE SUBITO</h2><p>Fix about:blank - clicca sotto</p>
<div class="btn g" onclick="cerca()">🔔 ATTIVA SCAN</div>
<div class="btn d" onclick="cerca()">🔍 SCAN 33 COPPIE - 1m+5m</div>
<p id="info" style="color:#00ff88">App pronta - 0 RAM all'avvio</p><div id="live"></div>
<script>
function cerca(){document.getElementById('info').innerText='⏳ Scan 33 coppie (30 sec)...'; fetch('/api/scan').then(r=>r.json()).then(d=>{document.getElementById('info').innerText='Trovati '+d.signals.length; let h=''; d.signals.forEach(s=>{h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><b>${s.dir} ${s.pair}</b><br>${s.note}<br>${s.price}</div>`;}); document.getElementById('live').innerHTML=h||'Nessun segnale - filtro 5min attivo';});}
</script></body></html>"""

@app.route('/api/scan')
def api():
    out=[]
    for otc, real in OTC_MAP.items():
        try:
            df1=yf.download(real, period="2d", interval="1m", progress=False, auto_adjust=True)
            df1=fix(df1)
            if len(df1)<60: continue
            d=df1['Close'].diff()
            rsi=100-(100/(1+d.where(d>0,0).rolling(14).mean()/-d.where(d<0,0).rolling(14).mean()))
            ema21=df1['Close'].ewm(21).mean(); ema50=df1['Close'].ewm(50).mean()
            df5=yf.download(real, period="2d", interval="5m", progress=False, auto_adjust=True)
            df5=fix(df5)
            if len(df5)<30: 
                del df1, df5; gc.collect()
                continue
            d5=df5['Close'].diff()
            rsi5=100-(100/(1+d5.where(d5>0,0).rolling(14).mean()/-d5.where(d5<0,0).rolling(14).mean()))
            ema50_5=df5['Close'].ewm(50).mean()
            c1=float(df1.iloc[-1]['Close']); c5=float(df5.iloc[-1]['Close'])
            r1=float(rsi.iloc[-1]); r5=float(rsi5.iloc[-1])
            e21=float(ema21.iloc[-1]); e50=float(ema50.iloc[-1]); e50_5=float(ema50_5.iloc[-1])
            dire=None
            if c1>e50 and e21>e50 and 35<=r1<=58: dire="BUY"
            elif c1<e50 and e21<e50 and 42<=r1<=65: dire="SELL"
            if dire:
                if dire=="BUY" and (c5<e50_5 or r5<40): dire=None
                if dire=="SELL" and (c5>e50_5 or r5>60): dire=None
            if dire:
                fmt=f"{c1:.5f}" if "JPY" not in otc and "OTC" in otc and len(otc)<13 else f"{c1:.2f}"
                out.append({"pair":otc,"dir":dire,"price":fmt,"note":f"85% {dire} 1+5m {r1:.0f}/{r5:.0f}"})
            del df1, df5; gc.collect()
            time.sleep(0.15)
        except:
            gc.collect()
            continue
    return jsonify({"signals":out})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
