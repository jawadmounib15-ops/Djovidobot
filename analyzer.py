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
    if CACHE["data"] is not None and now - CACHE["time"] < 50:
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
        if df is None or len(df)<60: return None
        c=df['Close']; df=df.copy()
        df['EMA9']=c.ewm(9).mean(); df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean(); df['EMA100']=c.ewm(100).mean()
        delta=c.diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=-delta.where(delta<0,0).rolling(14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        return df
    except: return None

def job1_pinbar(o,h,l,c):
    body=abs(c-o); rng=h-l
    if rng==0 or body<rng*0.06 or body>rng*0.45: return None
    upper=h-max(o,c); lower=min(o,c)-l
    if lower>=body*1.8 and lower>=rng*0.45 and upper<=rng*0.35:
        r=lower/body
        if 1.8 <= r <= 4.2: return "CALL", round(r,1)
    if upper>=body*1.8 and upper>=rng*0.45 and lower<=rng*0.35:
        r=upper/body
        if 1.8 <= r <= 4.2: return "PUT", round(r,1)
    return None

def job2_engulfing(df):
    # candela 2 mangia candela 1
    p1=df.iloc[-3]; p2=df.iloc[-2]
    o1,c1=p1['Open'],p1['Close']; o2,c2=p2['Open'],p2['Close']
    # bullish engulfing
    if c1<o1 and c2>o2 and o2<=c1 and c2>=o1 and abs(c2-o2) > abs(c1-o1)*1.2:
        if c2>o1 and p2['High']-p2['Low'] < abs(c2-o2)*1.5: # no ombra 7x
            return "CALL", "Engulf BULL"
    if c1>o1 and c2<o2 and o2>=c1 and c2<=o1 and abs(c2-o2) > abs(c1-o1)*1.2:
        if p2['High']-p2['Low'] < abs(c2-o2)*1.5:
            return "PUT", "Engulf BEAR"
    return None

def job3_ema50_bounce(df):
    last=df.iloc[-2]; prev=df.iloc[-3]
    price=float(last['Close']); ema50=float(last['EMA50'])
    o,h,l,c = float(last['Open']),float(last['High']),float(last['Low']),price
    body=abs(c-o); rng=h-l
    if rng==0: return None
    # vicino a EMA50 entro 0.15%
    if abs(price-ema50)/price > 0.0015: return None
    if rng > body*4.5: return None # anti 7x
    if price>ema50 and (min(o,c)-l) >= body*1.2: return "CALL", "Bounce EMA50"
    if price<ema50 and (h-max(o,c)) >= body*1.2: return "PUT", "Bounce EMA50"
    return None

def job4_double_push(df):
    # 2 candele stesso colore + 3a opposta forte
    c1=df.iloc[-4]; c2=df.iloc[-3]; c3=df.iloc[-2]
    if c1['Close']<c1['Open'] and c2['Close']<c2['Open'] and c3['Close']>c3['Open']:
        if c3['Close'] > max(c1['Open'],c2['Open']):
            rng=c3['High']-c3['Low']
            if rng < abs(c3['Close']-c3['Open'])*2.0:
                return "CALL", "Double Push UP"
    if c1['Close']>c1['Open'] and c2['Close']>c2['Open'] and c3['Close']<c3['Open']:
        if c3['Close'] < min(c1['Open'],c2['Open']):
            rng=c3['High']-c3['Low']
            if rng < abs(c3['Close']-c3['Open'])*2.0:
                return "PUT", "Double Push DOWN"
    return None

def job5_break_retest(df):
    last=df.iloc[-2]
    highs=df['High'].iloc[-21:-1].max(); lows=df['Low'].iloc[-21:-1].min()
    c=float(last['Close']); o=float(last['Open'])
    rng=float(last['High']-last['Low']); body=abs(c-o)
    if rng > body*3.5: return None
    if c > highs*0.9995 and c>o and body>rng*0.55: return "CALL", "Break High"
    if c < lows*1.0005 and c<o and body>rng*0.55: return "PUT", "Break Low"
    return None

def analyze(df):
    now=datetime.now(ITALY_TZ)
    if df is None: return {"score":0,"action":"WAIT","reason":"Cache...","time":now.strftime("%H:%M:%S")}
    last=df.iloc[-2]; rsi=float(last['RSI'])
    e9,e21,e50=float(last['EMA9']),float(last['EMA21']),float(last['EMA50'])
    price=float(last['Close'])
    up = e9>e21 and price>e50
    down = e9<e21 and price<e50
    # RSI comune a tutti i lavori - largo ma sicuro
    if not (32 <= rsi <= 68):
        return {"score":0,"action":"WAIT","reason":f"RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}

    # CATENA DI LAVORI
    j1=job1_pinbar(float(last['Open']),float(last['High']),float(last['Low']),price)
    if j1:
        d,r=j1
        if (d=="CALL" and up) or (d=="PUT" and down):
            return {"score":92,"action":f"{'BUY' if d=='CALL' else 'SELL'} 92%","reason":f"JOB1 Pinbar {r}x RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}

    j2=job2_engulfing(df)
    if j2:
        d,r=j2
        if (d=="CALL" and price>e50) or (d=="PUT" and price<e50):
            return {"score":88,"action":f"{'BUY' if d=='CALL' else 'SELL'} 88%","reason":f"JOB2 {r} RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}

    j3=job3_ema50_bounce(df)
    if j3:
        d,r=j3
        if (d=="CALL" and up) or (d=="PUT" and down):
            return {"score":86,"action":f"{'BUY' if d=='CALL' else 'SELL'} 86%","reason":f"JOB3 {r} RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}

    j4=job4_double_push(df)
    if j4:
        d,r=j4
        return {"score":85,"action":f"{'BUY' if d=='CALL' else 'SELL'} 85%","reason":f"JOB4 {r} RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}

    j5=job5_break_retest(df)
    if j5:
        d,r=j5
        if (d=="CALL" and up) or (d=="PUT" and down):
            return {"score":85,"action":f"{'BUY' if d=='CALL' else 'SELL'} 85%","reason":f"JOB5 {r} RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}

    return {"score":0,"action":"WAIT","reason":f"5 jobs checked RSI {rsi:.0f}","time":now.strftime("%H:%M:%S")}

HTML="""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V4.0 5 JOBS</title>
<style>body{background:#0a0a0f;color:#fff;font-family:system-ui;padding:12px}select{width:100%;padding:12px;border-radius:10px;background:#1a1a22;color:#fff;border:1px solid #333;margin:6px 0}.row{display:flex;gap:8px}.row select{flex:1}.card{background:#1a1a22;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #333}.sbuy{border-left-color:gold;border:2px solid gold;animation:pulse 1s infinite}.badge{padding:6px 12px;border-radius:20px;font-weight:bold;background:gold;color:#000}.perc{font-size:26px;font-weight:900;color:gold}button{width:100%;padding:14px;background:gold;color:#000;border:none;border-radius:12px;font-weight:bold;font-size:17px}@keyframes pulse{0%{box-shadow:0 0 0 0 gold}70%{box-shadow:0 0 0 10px transparent}100%{box-shadow:0 0 0 0 transparent}}</style></head><body>
<h2>⚡ V4.0 5 LAVORI CATENA 🔊</h2><p style=color:#0f0>20 coppie - 5 lavori sicuri - Se non c'è 1 arriva altro</p>
<div class="row"><select id="pair"><option>EUR/USD-OTC</option><option>USD/CAD-OTC</option><option>USD/JPY-OTC</option><option>GBP/USD-OTC</option><option>EUR/JPY-OTC</option><option>AUD/CAD-OTC</option><option>GBP/JPY-OTC</option><option>EUR/GBP-OTC</option><option>AUD/USD-OTC</option><option>USD/CHF-OTC</option><option>EUR/AUD-OTC</option><option>GBP/AUD-OTC</option><option>EUR/CAD-OTC</option><option>NZD/USD-OTC</option><option>GBP/CAD-OTC</option><option>SOL/USD-OTC</option><option>BTC/USD-OTC</option><option>ETH/USD-OTC</option><option>EUR/USD</option><option>GBP/USD</option></select><select id="tf"><option>5m</option></select></div>
<button onclick="analyze()">ANALIZZA</button>
<label style="display:flex;align-items:center;gap:8px;margin:10px 0;color:#aaa"><input type="checkbox" id="soundOn" checked> 🔊 Suono ON 85%+</label>
<div id="result"><div class=card>Pronto - V4.0 5 lavori</div></div><h3>Segnali 85%+ LIVE (tutti i lavori)</h3><div id="auto"></div>
<script>
let lastS=new Set();
function beep(){try{let c=new (window.AudioContext||window.webkitAudioContext)();let o=c.createOscillator();let g=c.createGain();o.connect(g);g.connect(c.destination);o.frequency.value=880;g.gain.setValueAtTime(0.8,c.currentTime);o.start();setTimeout(()=>{o.stop();c.close();},400);if(navigator.vibrate) navigator.vibrate([250,100,250]);}catch(e){}}
async function analyze(){let p=document.getElementById('pair').value;let r=await fetch('/api/analyze?pair='+encodeURIComponent(p)+'&t='+Date.now());let d=await r.json();document.getElementById('result').innerHTML='<div class=card '+(d.score>=85?'sbuy':'')+'><b>'+p+'</b> <span class=badge>'+d.action+'</span><div class=perc>'+d.score+'%</div><small>'+d.reason+' - '+d.time+'</small></div>';if(d.score>=85) beep();}
async function scan(){try{let r=await fetch('/api/scan?t='+Date.now());let d=await r.json();let h='';let nf=false;let cur=new Set();d.forEach(c=>{let k=c.pair+c.action;cur.add(k);if(!lastS.has(k)) nf=true;h+='<div class=card sbuy><b>'+c.pair+'</b> <span class=badge>'+c.action+'</span><div class=perc>'+c.score+'%</div><small>'+c.reason+'</small></div>'});if(nf && lastS.size>0 && document.getElementById('soundOn').checked) beep();lastS=cur;if(d.length==0) h='<div class=card>⏳ Scansiono 5 lavori su 20 mercati...</div>';document.getElementById('auto').innerHTML=h;}catch(e){}}
scan(); setInterval(scan,15000);
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/analyze')
def api_analyze():
    pair=request.args.get('pair','EUR/USD-OTC'); sym=PAIRS.get(pair,"EURUSD=X")
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
        if d['score']>=85: res.append({"pair":lab, **d})
    return jsonify(res)
if __name__=='__main__': app.run(host="0.0.0.0",port=10000)
