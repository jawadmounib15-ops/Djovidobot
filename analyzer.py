import os, time, threading
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)
pending=[]; cooldown={}; history=[]; last_debug="Avvio V74 LOOSE..."
_YF_SESSION = cffi_requests.Session(impersonate="chrome")

HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#0e0e0e;color:#fff;font-family:Arial;margin:0;padding:10px}
.top{text-align:center;color:#ffeb00;font-size:32px;font-weight:bold;padding:15px;background:#1a1a1a;border-radius:12px;margin-bottom:10px}
.badge{text-align:center;background:#2a2a2a;padding:10px;border-radius:10px;margin-bottom:10px;font-size:14px}
.green{background:#00e676;color:#000;padding:12px;border-radius:10px;text-align:center;font-weight:bold;margin-bottom:10px}
.card{border:2px solid #00e676;border-radius:12px;padding:12px;margin-bottom:10px;background:#1e1e1e}
.sell{border-color:#ff5252}
.exp{font-weight:bold;color:#ffeb00}
.debug{background:#222;padding:8px;border-radius:8px;font-size:11px;color:#aaa;margin-top:10px}
</style></head><body>
<div class="top" id="clock">00:00:00</div>
<div class="badge">🟢 V74 PINBAR LOOSE 5MIN - {{pending|length}} attivi - {{history|length}} oggi - Cooldown:{{cooldown|length}} - 21 PAIRS</div>
<div class="green" onclick="let a=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');a.play()">✅ SUONO ON - TEST</div>
{% for h in pending[::-1] %}
<div class="card {{'sell' if h.signal=='SELL' else ''}}">
🎯 {{h.symbol}} {{h.signal}} PINBAR <span class="exp">⏰ {{h.scadenza}}</span> {{h.time_str}} RSI{{h.rsi}}<br>
<span style="font-size:13px;color:#aaa">Entry {{h.entry}} | Coda {{h.tail}}x</span>
</div>
{% endfor %}
<div style="background:#1a1a1a;padding:10px;border-radius:10px;margin-top:15px">
<b>📊 STORICO - CON SCADENZA</b><br>
{% if history|length==0 %}In attesa...{% endif %}
{% for h in history[::-1][:30] %}
{{h.time_str}} {{h.symbol}} <span style="color:{{'red' if h.signal=='SELL' else '#00e676'}}">{{h.signal}} PINBAR ⏰{{h.scadenza}} RSI{{h.rsi}} coda{{h.tail}}x</span><br>
{% endfor %}
</div>
<div class="debug">DEBUG: {{last_debug}}<br>Ora: {{now}}</div>
<script>function upd(){document.getElementById('clock').innerText=new Date().toLocaleTimeString('it-IT')}setInterval(upd,1000);upd();setTimeout(()=>location.reload(),30000);</script>
</body></html>
"""

@app.route('/')
def home():
    return render_template_string(HTML, pending=pending, cooldown=cooldown, history=history, last_debug=last_debug, now=datetime.now().strftime("%H:%M:%S"))

def send(msg):
    if not TOKEN or not CHAT_ID: return
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=15)
    except: pass

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def scan():
    global pending, history, last_debug
    pending=[p for p in pending if time.time()-p['time']<600]
    found_pinbar=0; checked=0
    for symbol in PAIRS:
        if len([p for p in pending if time.time()-p['time']<600])>=3: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 900: continue
        if any(p['symbol']==clean for p in pending): continue
        try:
            df=yf.Ticker(symbol, session=_YF_SESSION).history(period="2d", interval="5m")
            df=fix_df(df)
            checked+=1
            if len(df)<100: continue
            df['e20']=df['Close'].ewm(span=20).mean(); df['e50']=df['Close'].ewm(span=50).mean()
            df['rsi']=rsi(df['Close'])
            last=df.iloc[-1]
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
            price=c; rsi_v=float(last['rsi']); e20=float(last['e20']); e50=float(last['e50'])
            is_green=c>o; is_red=not is_green; body=abs(c-o); rng=h-l
            if rng==0 or body==0: continue
            upper=h-max(o,c); lower=min(o,c)-l

            # LOOSE MA PULITA - POCO STRETTA COME HAI CHIESTO
            pin_bull = lower > body*2.0 and body < rng*0.45 and is_green
            pin_bear = upper > body*2.0 and body < rng*0.45 and is_red
            if pin_bull or pin_bear: found_pinbar+=1

            if not (pin_bull or pin_bear):
                last_debug=f"Scans {checked}/21 pinbar trovate oggi {found_pinbar} - {clean} no pinbar"
                continue

            tail_ratio = lower/body if pin_bull else upper/body
            scadenza = "5 MIN"

            # BUY LOOSE - basta e20>e50 e rsi largo
            if pin_bull and e20>e50 and 25<=rsi_v<=60:
                time_str=datetime.now().strftime("%d/%m %H:%M")
                item={"symbol":clean,"signal":"BUY","entry":f"{price:.5f}","time":time.time(),"time_str":time_str,"rsi":int(rsi_v),"tail":f"{tail_ratio:.1f}","scadenza":scadenza}
                pending.append(item); history.append(item); cooldown[clean]=time.time()
                send(f"🎯 PINBAR BUY {clean} ⏰ {scadenza} RSI{int(rsi_v)} coda {tail_ratio:.1f}x\nEntry {price:.5f}")
                last_debug=f"SEGNALE BUY {clean} coda {tail_ratio:.1f}x"
                continue
            if pin_bear and e20<e50 and 40<=rsi_v<=75:
                time_str=datetime.now().strftime("%d/%m %H:%M")
                item={"symbol":clean,"signal":"SELL","entry":f"{price:.5f}","time":time.time(),"time_str":time_str,"rsi":int(rsi_v),"tail":f"{tail_ratio:.1f}","scadenza":scadenza}
                pending.append(item); history.append(item); cooldown[clean]=time.time()
                send(f"🎯 PINBAR SELL {clean} ⏰ {scadenza} RSI{int(rsi_v)} coda {tail_ratio:.1f}x\nEntry {price:.5f}")
                last_debug=f"SEGNALE SELL {clean} coda {tail_ratio:.1f}x"

        except Exception as e:
            last_debug=f"ERR {clean}: {e}"
            continue
    if found_pinbar==0:
        last_debug=f"Nessuna pinbar su {checked} coppie - mercato piatto {datetime.now().strftime('%H:%M')}"
    else:
        last_debug=f"Trovate {found_pinbar} pinbar ma filtrate da RSI/trend - {last_debug}"

def loop():
    time.sleep(5)
    if TOKEN and CHAT_ID: send("🚀 V74 LOOSE 5MIN AVVIATO - Filtro poco stretto, ora arrivano segnali")
    while True:
        try: scan()
        except Exception as e: print(e)
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
