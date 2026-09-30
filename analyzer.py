# V65 PERFETTA - Pinbar vera che vedi anche su Quotex
import os, time, threading, requests
from flask import Flask, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

ITALY = ZoneInfo("Europe/Rome")
TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","NZDCAD=X"]

app = Flask(__name__)
last_signals=[]; scan_status={"last_scan":"Mai","count":0}; last_scan_ts=0; cooldown={}

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def ema(s,p): return s.ewm(span=p).mean()

def is_perfect_pinbar(o,h,l,c,rsi_val,dist_ema20,prev_high,prev_low):
    body=abs(c-o); rng=h-l
    if rng==0 or body==0: return None
    if body < rng*0.08 or body > rng*0.25: return None # no doji
    up=h-max(o,c); low=min(o,c)-l
    close_pos=(c-l)/rng
    dom=max(up,low)
    ratio=dom/body if body>0 else 0
    if ratio < 3.2 or ratio > 6.0: return None # solo 3.2x - 6x perfette
    # wick opposto minuscolo
    if up > low: # SELL - shooting star
        if up < rng*0.62: return None
        if low > rng*0.15: return None
        if close_pos > 0.25: return None
        if rsi_val and rsi_val < 48: return None
        if h < prev_high*0.9996: return None
        return "SELL", round(ratio,1)
    else: # BUY - hammer
        if low < rng*0.62: return None
        if up > rng*0.15: return None
        if close_pos < 0.75: return None
        if rsi_val and rsi_val > 55: return None # LA TUA AUDCAD 62.9 ORA SALTA
        if l > prev_low*1.0004: return None
        return "BUY", round(ratio,1)

def do_scan():
    global last_signals, scan_status, last_scan_ts
    res=[]; found=0
    for symbol in PAIRS:
        if found>=2: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 5400: continue # 90min no repeat
        try:
            df=yf.download(symbol, period="5d", interval="5m", progress=False)
            df=fix_df(df)
            if len(df)<212: continue
            df['RSI']=rsi(df['Close']); df['EMA20']=ema(df['Close'],20)
            last=df.iloc[-2] # chiusa
            prev_h=df['High'].iloc[-12:-2].max(); prev_l=df['Low'].iloc[-12:-2].min()
            rsi_v=float(last['RSI']); dist=abs(float(last['Close'])-float(last['EMA20']))/float(last['Close'])
            if dist>0.007: continue
            pin=is_perfect_pinbar(float(last['Open']),float(last['High']),float(last['Low']),float(last['Close']),rsi_v,dist,prev_h,prev_l)
            if pin:
                sig,ratio=pin
                item={"symbol":clean,"signal":sig,"ratio":f"{ratio}x","price":round(float(last['Close']),5),"rsi":round(rsi_v,1),"time":datetime.now(ITALY).strftime("%H:%M:%S"),"ohlc":f"O{float(last['Open']):.5f} H{float(last['High']):.5f} L{float(last['Low']):.5f} C{float(last['Close']):.5f}"}
                res.append(item); cooldown[clean]=time.time(); found+=1
                if TOKEN and CHAT_ID:
                    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":f"{'🔴' if sig=='SELL' else '🟢'} {clean} {sig} PERFETTA {ratio}x RSI{int(rsi_v)} {item['ohlc']}"}, timeout=5)
                    except: pass
        except: continue
    last_signals=res; last_scan_ts=time.time()
    scan_status={"last_scan":datetime.now(ITALY).strftime("%H:%M:%S"),"count":len(res)}
    return res

@app.route('/')
def home():
    return """<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>V65 PERFETTA</title>
<style>body{background:#0f0f0f;color:#fff;font-family:Arial;padding:20px;text-align:center}button{background:#00ff88;color:#000;border:none;padding:15px 30px;font-size:18px;border-radius:12px;font-weight:bold;margin:10px;cursor:pointer}button.active{background:#ff0044;color:#fff}.card{background:#1e1e1e;padding:15px;margin:12px;border-radius:12px;border-left:6px solid #00ff88;font-size:13px}.sell{border-left-color:#ff4444}.buy{border-left-color:#00ff88}</style></head><body>
<h2>🔥 V65 PERFETTA</h2><p style=color:#888>3.2x-6x | RSI filtrato | 90min cooldown | vedi su Quotex</p>
<button id="soundBtn" onclick="toggleSound()">🔇 ATTIVA SUONO</button><button onclick="manualScan()">🔍 SCAN ORA</button>
<div id="status">Caricamento...</div><div id="signals"></div>
<script>
let soundOn=false; let audio=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
function toggleSound(){soundOn=!soundOn; let b=document.getElementById('soundBtn'); if(soundOn){b.textContent='🔊 SUONO ATTIVO'; b.classList.add('active'); audio.play().catch(()=>{});} else {b.textContent='🔇 ATTIVA SUONO'; b.classList.remove('active');}}
function manualScan(){fetch('/api/scan').then(r=>r.json()).then(d=>updateUI(d));}
function updateUI(data){document.getElementById('status').innerText='Ultima: '+data.status.last_scan+' IT - Trovate: '+data.status.count+' perfette'; let div=document.getElementById('signals'); div.innerHTML=''; if(data.signals.length==0){div.innerHTML='<p style=color:#777>Nessuna pinbar PERFETTA ora<br>Quando appare, la vedi anche su Quotex</p>';} data.signals.forEach(s=>{let c=document.createElement('div'); c.className='card '+(s.signal=='SELL'?'sell':'buy'); c.innerHTML='<b>'+s.symbol+'</b> - '+s.signal+' PERFETTA '+s.ratio+'<br>RSI:'+s.rsi+' Prezzo:'+s.price+'<br><small>'+s.ohlc+'</small><br><small>'+s.time+' IT</small>'; div.appendChild(c);}); if(data.signals.length>0 && soundOn){audio.play().catch(()=>{}); if('vibrate' in navigator) navigator.vibrate([300,100,300]);}}
setInterval(()=>{fetch('/api/signals').then(r=>r.json()).then(d=>updateUI(d));}, 45000);
fetch('/api/signals').then(r=>r.json()).then(d=>updateUI(d));
</script></body></html>"""

@app.route('/api/signals')
def api_signals():
    global last_signals
    if time.time()-last_scan_ts>600 and last_scan_ts!=0: last_signals=[]
    return jsonify({"signals":last_signals,"status":scan_status})
@app.route('/api/scan')
def api_scan(): return jsonify({"signals":do_scan(),"status":scan_status})
try: do_scan()
except: pass
def loop():
    while True:
        try: do_scan()
        except: pass
        time.sleep(90)
threading.Thread(target=loop, daemon=True).start()
