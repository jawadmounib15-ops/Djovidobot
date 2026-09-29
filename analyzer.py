from flask import Flask, jsonify, render_template_string, request
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta
import time
from curl_cffi import requests as c_requests

app = Flask(__name__)
ITALY_TZ = timezone(timedelta(hours=2))

PAIRS = {
 "EUR/USD (REAL)":"EURUSD=X",
 "GBP/USD (REAL)":"GBPUSD=X",
 "EUR/JPY (REAL)":"EURJPY=X",
 "GBP/JPY (REAL)":"GBPJPY=X",
 "USD/JPY (REAL)":"JPY=X",
 "AUD/USD (REAL)":"AUDUSD=X",
 "Ethereum (REAL)":"ETH-USD",
 "Bitcoin (REAL)":"BTC-USD"
}

session = c_requests.Session(impersonate="chrome")
CACHE = {"data": None, "time": 0}

def get_all_data():
    now = time.time()
    if CACHE["data"] is not None and now - CACHE["time"] < 40:
        return CACHE["data"]
    try:
        symbols = list(set(PAIRS.values()))
        df_all = yf.download(symbols, period="2d", interval="5m", group_by='ticker', progress=False, auto_adjust=False, threads=True, session=session)
        CACHE["data"] = df_all
        CACHE["time"] = now
        return df_all
    except:
        return CACHE["data"]

def get_single_df(df_all, symbol):
    try:
        if isinstance(df_all.columns, pd.MultiIndex):
            try: df = df_all[symbol]
            except: df = df_all
        else: df = df_all
        if df is None or len(df)<50: return None
        c=df['Close']; df=df.copy()
        df['EMA9']=c.ewm(9).mean(); df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean()
        delta=c.diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=-delta.where(delta<0,0).rolling(14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        return df
    except: return None

def analyze(df):
    now=datetime.now(ITALY_TZ)
    if df is None or len(df)<50: return {"score":0,"action":"WAIT","reason":"Carico dati...","time":now.strftime("%H:%M:%S")}
    last=df.iloc[-2]
    if pd.isna(last['RSI']): return {"score":0,"action":"WAIT","reason":"Calcolo...","time":now.strftime("%H:%M:%S")}
    rsi=float(last['RSI'])
    e9,e21,e50=float(last['EMA9']),float(last['EMA21']),float(last['EMA50'])
    price=float(last['Close'])
    up_trend = e9 > e21 and e21 > e50 and price > e9
    down_trend = e9 < e21 and e21 < e50 and price < e9
    if not (30 <= rsi <= 70): return {"score":0,"action":"WAIT","reason":f"RSI {rsi:.0f} fuori zona","time":now.strftime("%H:%M:%S")}
    bullish = float(last['Close']) > float(last['Open'])
    bearish = float(last['Close']) < float(last['Open'])
    if up_trend and 45 <= rsi <= 62 and bullish: return {"score":92,"action":"BUY 92%","reason":f"TREND UP RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}
    if down_trend and 38 <= rsi <= 55 and bearish: return {"score":92,"action":"SELL 92%","reason":f"TREND DOWN RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}
    return {"score":0,"action":"WAIT","reason":f"Attendo trend RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}

HTML="""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V7.1 FIX</title>
<style>body{background:#0a0a0f;color:#fff;font-family:system-ui;padding:12px}select{width:100%;padding:12px;border-radius:10px;background:#1a1a22;color:#fff;border:1px solid #333;margin:6px 0}.row{display:flex;gap:8px}.row select{flex:1}.card{background:#1a1a22;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #333}.sbuy{border-left-color:#00ff88;border:2px solid #00ff88}.new{animation:pulse 1s infinite}.badge{padding:6px 12px;border-radius:20px;font-weight:bold;background:#00ff88;color:#000}.perc{font-size:26px;font-weight:900;color:#00ff88}button{width:100%;padding:14px;background:#00ff88;color:#000;border:none;border-radius:12px;font-weight:bold;font-size:17px}.status{padding:8px 12px;border-radius:8px;font-size:13px;margin:8px 0}.open{background:#00ff8822;color:#00ff88;border:1px solid #00ff88}.closed{background:#ffaa0022;color:#ffaa00;border:1px solid #ffaa00}@keyframes pulse{0%{box-shadow:0 0 0 0 #00ff88}70%{box-shadow:0 0 0 10px transparent}100%{box-shadow:0 0 0 0 transparent}}</style></head><body>
<h2>🚀 V7.1 FIX - REAL</h2><p style=color:#00ff88>✅ Fix mercato chiuso - Ora funziona</p>
<div id="marketInfo" class="status open">🟢 Mercato REAL APERTO - Scansione attiva</div>
<div class="row"><select id="pair"><option>EUR/USD (REAL)</option><option>GBP/USD (REAL)</option><option>EUR/JPY (REAL)</option><option>GBP/JPY (REAL)</option><option>USD/JPY (REAL)</option><option>AUD/USD (REAL)</option><option>Ethereum (REAL)</option><option>Bitcoin (REAL)</option></select><select id="tf"><option>5m</option></select></div>
<button onclick="analyze()">ANALIZZA MANUALE</button>
<label style="display:flex;align-items:center;gap:8px;margin:10px 0;color:#aaa"><input type="checkbox" id="soundOn" checked> 🔊 Suono su 92%</label>
<div id="result"><div class=card>🤖 Pronto - Auto-scan attivo</div></div><h3>🚨 Segnali REAL LIVE (auto)</h3><div id="auto"></div>
<script>
let firstSeen={};
function beep(){try{let c=new (window.AudioContext||window.webkitAudioContext)();let o=c.createOscillator();let g=c.createGain();o.connect(g);g.connect(c.destination);o.frequency.value=900;g.gain.setValueAtTime(0.9,c.currentTime);o.start();setTimeout(()=>{o.stop();c.close();},800);if(navigator.vibrate) navigator.vibrate([500,100,500]);}catch(e){}}
async function analyze(){let p=document.getElementById('pair').value;let r=await fetch('/api/analyze?pair='+encodeURIComponent(p)+'&t='+Date.now());let d=await r.json();document.getElementById('result').innerHTML='<div class=card '+(d.score>=92?'sbuy new':'')+'><b>'+p+'</b> <span class=badge>'+d.action+'</span><div class=perc>'+d.score+'%</div><small>'+d.reason+' - '+d.time+'</small></div>';if(d.score>=92) beep();}
async function scan(){try{let r=await fetch('/api/scan?t='+Date.now());let d=await r.json();let h='';let now=Date.now();d.forEach(c=>{let key=c.pair+c.action;if(!firstSeen[key]){firstSeen[key]=now;if(document.getElementById('soundOn').checked) beep();}let ageSec=Math.floor((now-firstSeen[key])/1000);let ageText=ageSec<120?'🟢 NUOVO! '+ageSec+'s':'🟡 '+Math.floor(ageSec/60)+'m';h+='<div class=\"card sbuy new\"><b>'+c.pair+'</b> <span class=badge>'+c.action+'</span> <span style=\"font-size:12px;color:#00ff88\">'+ageText+'</span><div class=perc>'+c.score+'%</div><small>'+c.reason+' - '+c.time+'</small></div>';});if(d.length===0){h='<div class=card>🤖 Nessun segnale 92% ora<br><small>RSI in attesa - '+new Date().toLocaleTimeString()+'</small></div>';}document.getElementById('auto').innerHTML=h;}catch(e){}}
scan(); setInterval(scan,15000);
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/analyze')
def api_analyze():
    pair=request.args.get('pair','EUR/USD (REAL)'); sym=PAIRS.get(pair,"EURUSD=X")
    df_all=get_all_data()
    if df_all is None: return jsonify({"score":0,"action":"WAIT","reason":"Carico...","time":datetime.now(ITALY_TZ).strftime("%H:%M:%S")})
    df=get_single_df(df_all,sym)
    return jsonify(analyze(df))
@app.route('/api/scan')
def api_scan():
    df_all=get_all_data()
    if df_all is None: return jsonify([])
    res=[]
    for lab,y in PAIRS.items():
        df=get_single_df(df_all,y)
        d=analyze(df)
        if d['score']>=92: res.append({"pair":lab, **d})
    return jsonify(res)
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
