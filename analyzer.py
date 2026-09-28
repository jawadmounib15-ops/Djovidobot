from flask import Flask, jsonify, render_template_string, request
from curl_cffi import requests as c_requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta
import time

app = Flask(__name__)
ITALY_TZ = timezone(timedelta(hours=2))
PAIRS = {
 "EUR/USD-OTC":"EURUSD=X","USD/CAD-OTC":"USDCAD=X","USD/JPY-OTC":"USDJPY=X",
 "GBP/USD-OTC":"GBPUSD=X","EUR/JPY-OTC":"EURJPY=X","AUD/CAD-OTC":"AUDCAD=X",
 "GBP/JPY-OTC":"GBPJPY=X","EUR/GBP-OTC":"EURGBP=X","AUD/USD-OTC":"AUDUSD=X",
 "USD/CHF-OTC":"CHF=X","EUR/AUD-OTC":"EURAUD=X","GBP/AUD-OTC":"GBPAUD=X",
 "EUR/CAD-OTC":"EURCAD=X","NZD/USD-OTC":"NZDUSD=X","GBP/CAD-OTC":"GBPCAD=X",
 "SOL/USD-OTC":"SOL-USD","BTC/USD-OTC":"BTC-USD","ETH/USD-OTC":"ETH-USD",
 "EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X"
}
session = c_requests.Session(impersonate="chrome")
CACHE = {"data": None, "time": 0}

def get_all_data():
    now = time.time()
    if CACHE["data"] is not None and now - CACHE["time"] < 55: # cache 55 sec
        return CACHE["data"]
    try:
        symbols = list(set(PAIRS.values()))
        df_all = yf.download(" ".join(symbols), period="2d", interval="5m", group_by='ticker', progress=False, auto_adjust=False, threads=True, session=session)
        CACHE["data"] = df_all
        CACHE["time"] = now
        return df_all
    except:
        return CACHE["data"]

def get_single_df(df_all, symbol):
    try:
        if len(PAIRS) == 1 or isinstance(df_all.columns, pd.MultiIndex):
            try: df = df_all[symbol]
            except: df = df_all
        else:
            df = df_all
        if df is None or len(df)<60: return None
        c=df['Close']
        df=df.copy()
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
        r=lower/body
        if 2.0 <= r <= 3.8: return "CALL", round(r,1)
    if upper>=body*2.0 and upper>=rng*0.50 and lower<=rng*0.30:
        r=upper/body
        if 2.0 <= r <= 3.8: return "PUT", round(r,1)
    return None

def analyze_92(df):
    now=datetime.now(ITALY_TZ)
    if df is None: return {"score":0,"action":"WAIT","reason":"Cache...","time":now.strftime("%H:%M:%S")}
    last=df.iloc[-2]
    price=float(last['Close']); rsi=float(last['RSI'])
    pin=is_pinbar(float(last['Open']),float(last['High']),float(last['Low']),price)
    if not pin: return {"score":0,"action":"WAIT","reason":f"No pin RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}
    dir,ratio=pin
    e9,e21,e50=float(last['EMA9']),float(last['EMA21']),float(last['EMA50']); e200=float(last['EMA200'])
    up = e9>e21>e50 and price>e200; down = e9<e21<e50 and price<e200
    if dir=="CALL" and not up: return {"score":0,"action":"WAIT","reason":"CALL vs trend","time":now.strftime("%H:%M:%S")}
    if dir=="PUT" and not down: return {"score":0,"action":"WAIT","reason":"PUT vs trend","time":now.strftime("%H:%M:%S")}
    if dir=="CALL" and not (40 <= rsi <= 56): return {"score":0,"action":"WAIT","reason":f"RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}
    if dir=="PUT" and not (44 <= rsi <= 60): return {"score":0,"action":"WAIT","reason":f"RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}
    score = 95 if 2.2 <= ratio <= 3.2 else 90
    return {"score":score,"action":f"{'BUY' if dir=='CALL' else 'SELL'} {score}%","reason":f"Pin {ratio}x RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}

HTML="""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V3.9 ANTI-LAG</title>
<style>body{background:#0a0a0f;color:#fff;font-family:system-ui;padding:12px}select{width:100%;padding:12px;border-radius:10px;background:#1a1a22;color:#fff;border:1px solid #333;margin:6px 0}.row{display:flex;gap:8px}.row select{flex:1}.card{background:#1a1a22;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #333}.sbuy{border-left-color:gold;border:2px solid gold;animation:pulse 1s infinite}.badge{padding:6px 12px;border-radius:20px;font-weight:bold;background:gold;color:#000}.perc{font-size:26px;font-weight:900;color:gold}button{width:100%;padding:14px;background:gold;color:#000;border:none;border-radius:12px;font-weight:bold;font-size:17px}@keyframes pulse{0%{box-shadow:0 0 0 0 gold}70%{box-shadow:0 0 0 10px transparent}100%{box-shadow:0 0 0 0 transparent}}</style></head><body>
<h2>⚡ V3.9 ANTI-LAG 🔊</h2><p style=color:#0f0>20 coppie - 1 richiesta - 0 blocchi</p>
<div class="row"><select id="pair"><option>EUR/USD-OTC</option><option>USD/CAD-OTC</option><option>USD/JPY-OTC</option><option>GBP/USD-OTC</option><option>EUR/JPY-OTC</option><option>AUD/CAD-OTC</option><option>GBP/JPY-OTC</option><option>EUR/GBP-OTC</option><option>AUD/USD-OTC</option><option>USD/CHF-OTC</option><option>EUR/AUD-OTC</option><option>GBP/AUD-OTC</option><option>EUR/CAD-OTC</option><option>NZD/USD-OTC</option><option>GBP/CAD-OTC</option><option>SOL/USD-OTC</option><option>BTC/USD-OTC</option><option>ETH/USD-OTC</option><option>EUR/USD</option><option>GBP/USD</option></select><select id="tf"><option>5m</option></select></div>
<button onclick="analyze()">ANALIZZA</button>
<label style="display:flex;align-items:center;gap:8px;margin:10px 0;color:#aaa"><input type="checkbox" id="soundOn" checked> 🔊 Suono ON</label>
<div id="result"><div class=card>Pronto - Anti-Lag 20 coppie</div></div><h3>Segnali 90%+ LIVE</h3><div id="auto"></div>
<script>
let lastS=new Set();
function beep(){try{let c=new (window.AudioContext||window.webkitAudioContext)();let o=c.createOscillator();let g=c.createGain();o.connect(g);g.connect(c.destination);o.frequency.value=880;g.gain.setValueAtTime(0.8,c.currentTime);o.start();setTimeout(()=>{o.stop();c.close();},350);if(navigator.vibrate) navigator.vibrate([250,100,250]);}catch(e){}}
async function analyze(){let p=document.getElementById('pair').value;let r=await fetch('/api/analyze?pair='+encodeURIComponent(p)+'&t='+Date.now());let d=await r.json();document.getElementById('result').innerHTML='<div class=card '+(d.score>=90?'sbuy':'')+'><b>'+p+'</b> <span class=badge>'+d.action+'</span><div class=perc>'+d.score+'%</div><small>'+d.reason+' - '+d.time+'</small></div>';if(d.score>=90) beep();}
async function scan(){try{let r=await fetch('/api/scan?t='+Date.now());let d=await r.json();let h='';let nf=false;let cur=new Set();d.forEach(c=>{let k=c.pair+c.action;cur.add(k);if(!lastS.has(k)) nf=true;h+='<div class=card sbuy><b>'+c.pair+'</b> <span class=badge>'+c.action+'</span><div class=perc>'+c.score+'%</div><small>'+c.reason+'</small></div>'});if(nf && lastS.size>0 && document.getElementById('soundOn').checked) beep();lastS=cur;if(d.length==0) h='<div class=card>⏳ Nessun 90%+ - scan 20 mercati ogni 15s (anti-lag)</div>';document.getElementById('auto').innerHTML=h;}catch(e){}}
scan(); setInterval(scan,15000);
document.body.addEventListener('click',()=>{try{new (window.AudioContext||window.webkitAudioContext)().resume();}catch(e){}},{once:true});
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/api/analyze')
def api_analyze():
    pair=request.args.get('pair','EUR/USD-OTC'); sym=PAIRS.get(pair,"EURUSD=X")
    df_all=get_all_data()
    if df_all is None: return jsonify({"score":0,"action":"WAIT","reason":"Carico...","time":datetime.now(ITALY_TZ).strftime("%H:%M:%S")})
    df=get_single_df(df_all,sym)
    return jsonify(analyze_92(df))

@app.route('/api/scan')
def api_scan():
    df_all=get_all_data()
    if df_all is None: return jsonify([])
    res=[]
    for lab,y in PAIRS.items():
        df=get_single_df(df_all,y)
        d=analyze_92(df)
        if d['score']>=90: res.append({"pair":lab, **d})
    return jsonify(res)

if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
