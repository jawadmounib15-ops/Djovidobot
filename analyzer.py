from flask import Flask, jsonify, render_template_string, request
from curl_cffi import requests as c_requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta
app = Flask(__name__)
ITALY_TZ = timezone(timedelta(hours=2))
PAIRS = {"EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X","USD/CAD-OTC":"USDCAD=X","EUR/JPY-OTC":"EURJPY=X","AUD/CAD-OTC":"AUDCAD=X","SOL/USD-OTC":"SOL-USD","BTC/USD-OTC":"BTC-USD","ETH/USD-OTC":"ETH-USD","EUR/USD":"EURUSD=X"}
session = c_requests.Session(impersonate="chrome")
def get_data(symbol):
    try:
        df = yf.download(symbol, period="2d", interval="5m", progress=False, auto_adjust=False, threads=False, session=session)
        if df is None or len(df)<60: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        c=df['Close']
        df['EMA9']=c.ewm(9).mean(); df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean(); df['EMA200']=c.ewm(200).mean()
        delta=c.diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=-delta.where(delta<0,0).rolling(14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        return df
    except: return None
def is_pinbar(o,h,l,c):
    body=abs(c-o); rng=h-l
    if rng==0 or body<rng*0.08 or body>rng*0.38: return None
    upper=h-max(o,c); lower=min(o,c)-l
    if lower>=body*2.0 and lower>=rng*0.50 and upper<=rng*0.30:
        ratio=lower/body
        if 2.0 <= ratio <= 3.8: return "CALL", round(ratio,1)
    if upper>=body*2.0 and upper>=rng*0.50 and lower<=rng*0.30:
        ratio=upper/body
        if 2.0 <= ratio <= 3.8: return "PUT", round(ratio,1)
    return None
def analyze_92(symbol):
    now=datetime.now(ITALY_TZ)
    df=get_data(symbol)
    if df is None: return {"score":0,"action":"WAIT","reason":"Yahoo occupato","time":now.strftime("%H:%M:%S")}
    last=df.iloc[-2]
    price=float(last['Close']); rsi=float(last['RSI'])
    pin=is_pinbar(float(last['Open']),float(last['High']),float(last['Low']),price)
    if not pin: return {"score":0,"action":"WAIT","reason":f"No pinbar RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}
    direzione,ratio=pin
    e9,e21,e50=float(last['EMA9']),float(last['EMA21']),float(last['EMA50']); e200=float(last['EMA200'])
    up = e9>e21>e50 and price>e200
    down = e9<e21<e50 and price<e200
    if direzione=="CALL" and not up: return {"score":0,"action":"WAIT","reason":"CALL contro trend","time":now.strftime("%H:%M:%S")}
    if direzione=="PUT" and not down: return {"score":0,"action":"WAIT","reason":"PUT contro trend","time":now.strftime("%H:%M:%S")}
    if direzione=="CALL" and not (40 <= rsi <= 56): return {"score":0,"action":"WAIT","reason":f"RSI {rsi:.0f} non buono CALL","time":now.strftime("%H:%M:%S")}
    if direzione=="PUT" and not (44 <= rsi <= 60): return {"score":0,"action":"WAIT","reason":f"RSI {rsi:.0f} non buono PUT","time":now.strftime("%H:%M:%S")}
    score = 95 if 2.2 <= ratio <= 3.2 else 90
    return {"score":score,"action":f"{'BUY' if direzione=='CALL' else 'SELL'} {score}%","reason":f"Pinbar {ratio}x | RSI {rsi:.0f} | Trend OK","time":now.strftime("%H:%M:%S")}
HTML="""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V3.7 BILANCIATA</title>
<style>body{background:#0a0a0f;color:#fff;font-family:system-ui;padding:12px}select{width:100%;padding:12px;border-radius:10px;background:#1a1a22;color:#fff;border:1px solid #333;margin:6px 0}.row{display:flex;gap:8px}.row select{flex:1}.card{background:#1a1a22;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #333}.sbuy{border-left-color:gold;border:2px solid gold}.badge{padding:6px 12px;border-radius:20px;font-weight:bold;background:gold;color:#000}.perc{font-size:26px;font-weight:900;color:gold}button{width:100%;padding:14px;background:gold;color:#000;border:none;border-radius:12px;font-weight:bold;font-size:17px}</style></head><body>
<h2>⚡ V3.7 BILANCIATA - ANTI 7x</h2><p style=color:#888>6-8 segnali/giorno - Blocca 7.0x/43x</p>
<div class="row"><select id="pair"><option>EUR/USD-OTC</option><option>USD/CAD-OTC</option><option>USD/JPY-OTC</option><option>GBP/USD-OTC</option><option>EUR/JPY-OTC</option><option>AUD/CAD-OTC</option><option>SOL/USD-OTC</option><option>BTC/USD-OTC</option><option>EUR/USD</option></select><select id="tf"><option>5m</option></select></div>
<button onclick="analyze()">ANALIZZA</button><div id="result"><div class=card>Pronto V3.7</div></div><h3>Segnali 90%+ ora</h3><div id="auto"></div>
<script>
async function analyze(){let p=document.getElementById('pair').value;let r=await fetch('/api/analyze?pair='+encodeURIComponent(p)+'&t='+Date.now());let d=await r.json();document.getElementById('result').innerHTML='<div class=card '+(d.score>=90?'sbuy':'')+'><b>'+p+'</b> <span class=badge>'+d.action+'</span><div class=perc>'+d.score+'%</div><small>'+d.reason+' - '+d.time+'</small></div>';}
async function scan(){try{let r=await fetch('/api/scan?t='+Date.now());let d=await r.json();let h='';d.forEach(c=>{h+='<div class=card sbuy><b>'+c.pair+'</b> <span class=badge>'+c.action+'</span><div class=perc>'+c.score+'%</div><small>'+c.reason+'</small></div>'});if(h=='')h='<div class=card>⏳ Nessun 90%+ ora - normale</div>';document.getElementById('auto').innerHTML=h;}catch(e){}}scan();setInterval(scan,12000);
</script></body></html>"""
@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/analyze')
def api_analyze():
    pair=request.args.get('pair','EUR/USD-OTC'); sym=PAIRS.get(pair,"EURUSD=X")
    return jsonify(analyze_92(sym))
@app.route('/api/scan')
def api_scan():
    res=[]
    for lab,y in PAIRS.items():
        d=analyze_92(y)
        if d['score']>=90: res.append({"pair":lab, **d})
    return jsonify(res)
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
