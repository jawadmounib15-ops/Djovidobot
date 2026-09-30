# analyzer.py V64.2 - FIX ORA ITALIA + NO FALSI 12x + SCADENZA
import os, time, threading, requests
from flask import Flask, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

ITALY = ZoneInfo("Europe/Rome")
TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","EURNZD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","GBPCAD=X","GBPNZD=X","AUDJPY=X","AUDCAD=X","AUDCHF=X","AUDNZD=X","CADJPY=X","CADCHF=X","CHFJPY=X","NZDJPY=X","NZDCAD=X","NZDCHF=X"]

app = Flask(__name__)
last_signals = []
scan_status = {"last_scan": "Mai", "count": 0}
last_scan_ts = 0

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def ema(s,p): return s.ewm(span=p).mean()

def is_perfect_pinbar(o,h,l,c,rsi_val,dist_ema20,prev_high,prev_low):
    body=abs(c-o); rng=h-l
    if rng==0 or body==0: return None
    
    # FIX 1: no doji, no 12x falsi
    if body < rng*0.06: return None
    if body > rng*0.30: return None
    
    up=h-max(o,c); low=min(o,c)-l
    close_pos=(c-l)/rng
    dom=max(up,low)
    
    if dom==0: return None
    ratio = dom / body
    
    # FIX 2: ratio 2.8x - 8x, oltre 8x è falso
    if ratio < 2.8 or ratio > 8.0:
        return None
    
    if dom < rng*0.55: return None
    if min(up,low) > rng*0.30: return None
    if rsi_val and not (30<=rsi_val<=72): return None
    if dist_ema20 and dist_ema20>0.012: return None
    
    if up>low: # SHOOTING STAR
        if close_pos>0.40: return None
        if h<prev_high*0.9995: return None
        return "SELL", round(ratio,1)
    else: # HAMMER
        if close_pos<0.60: return None
        if l>prev_low*1.0005: return None
        return "BUY", round(ratio,1)

def do_scan():
    global last_signals, scan_status, last_scan_ts
    res=[]
    for symbol in PAIRS:
        try:
            df=yf.download(symbol, period="5d", interval="5m", progress=False)
            df=fix_df(df)
            if len(df)<210: continue
            df['RSI']=rsi(df['Close']); df['EMA20']=ema(df['Close'],20)
            last=df.iloc[-1]; prev_h=df['High'].iloc[-11:-1].max(); prev_l=df['Low'].iloc[-11:-1].min()
            rsi_v=float(last['RSI']); dist=abs(float(last['Close'])-float(last['EMA20']))/float(last['Close'])
            pin=is_perfect_pinbar(float(last['Open']),float(last['High']),float(last['Low']),float(last['Close']),rsi_v,dist,prev_h,prev_l)
            if pin:
                sig,ratio=pin
                item={"symbol":symbol.replace('=X',''),"signal":sig,"ratio":f"{ratio}x","price":round(float(last['Close']),5),"rsi":round(rsi_v,1),"time":datetime.now(ITALY).strftime("%H:%M:%S")}
                res.append(item)
                try:
                    if TOKEN and CHAT_ID:
                        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":f"{'🔴' if sig=='SELL' else '🟢'} {item['symbol']} {sig} PERFETTA {ratio}x RSI {rsi_v:.0f} - {item['time']}"}, timeout=5)
                except: pass
        except Exception as e:
            print(f"Err {symbol}: {e}")
            continue
    
    last_signals=res
    last_scan_ts = time.time()
    scan_status={"last_scan":datetime.now(ITALY).strftime("%H:%M:%S - %d/%m"),"count":len(res)}
    return res

@app.route('/')
def home():
    return """
<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>V64.2 Pinbar</title>
<style>
body{background:#0f0f0f;color:#fff;font-family:Arial;padding:20px;text-align:center}
button{background:#00ff88;color:#000;border:none;padding:15px 30px;font-size:18px;border-radius:10px;font-weight:bold;margin:10px;cursor:pointer}
button.active{background:#ff0044;color:#fff}
.card{background:#1e1e1e;padding:15px;margin:10px;border-radius:10px;border-left:5px solid #00ff88}
.sell{border-left-color:#ff4444}.buy{border-left-color:#00ff88}
#log{margin-top:20px;font-size:14px;color:#aaa}
</style></head><body>
<h2>🔥 PINBAR PERFETTA V64.2</h2>
<button id="soundBtn" onclick="toggleSound()">🔇 ATTIVA SUONO</button>
<button onclick="manualScan()">🔍 SCAN ORA</button>
<div id="status">Ultima scansione: Mai - Ora Italia</div>
<div id="signals"></div>
<div id="log">Fix: No falsi 12x, segnali scadono dopo 10min</div>
<script>
let soundOn=false; let audio=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
function toggleSound(){soundOn=!soundOn; let b=document.getElementById('soundBtn'); if(soundOn){b.textContent='🔊 SUONO ATTIVO'; b.classList.add('active'); audio.play().catch(()=>{});} else {b.textContent='🔇 ATTIVA SUONO'; b.classList.remove('active');} }
function manualScan(){fetch('/api/scan').then(r=>r.json()).then(d=>updateUI(d));}
function updateUI(data){
 document.getElementById('status').innerText='Ultima: '+data.status.last_scan+' - Trovate: '+data.status.count+' (ora ITALIA)';
 let div=document.getElementById('signals'); div.innerHTML='';
 if(data.signals.length==0){div.innerHTML='<p style=color:#777>Nessuna pinbar perfetta ora<br>I segnali durano 10 min poi spariscono</p>';}
 data.signals.forEach(s=>{
   let c=document.createElement('div'); c.className='card '+(s.signal=='SELL'?'sell':'buy');
   c.innerHTML='<b>'+s.symbol+'</b> - '+s.signal+' PERFETTA<br>Ratio: '+s.ratio+' | RSI: '+s.rsi+'<br>Prezzo: '+s.price+'<br><small>'+s.time+' IT</small>';
   div.appendChild(c);
 });
 if(data.signals.length>0 && soundOn){audio.play().catch(()=>{}); if('vibrate' in navigator) navigator.vibrate([300,100,300]);}
}
setInterval(()=>{fetch('/api/signals').then(r=>r.json()).then(d=>updateUI(d));}, 30000);
fetch('/api/signals').then(r=>r.json()).then(d=>updateUI(d));
</script></body></html>
"""

@app.route('/api/signals')
def api_signals():
    global last_signals
    # FIX 3: segnali scadono dopo 10 min
    if time.time() - last_scan_ts > 600 and last_scan_ts != 0:
        last_signals = []
    return jsonify({"signals": last_signals, "status": scan_status})

@app.route('/api/scan')
def api_scan():
    res=do_scan()
    return jsonify({"signals": res, "status": scan_status})

# scan immediato all'avvio
try:
    do_scan()
except Exception as e:
    print(f"Scan boot error: {e}")

def loop():
    try:
        if TOKEN and CHAT_ID: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":"🚀 V64.2 ATTIVO - Fix ora IT + no 12x falsi"}, timeout=5)
    except: pass
    while True:
        try: do_scan()
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
