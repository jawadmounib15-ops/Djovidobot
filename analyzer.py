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
pending=[]; cooldown={}; history=[]
_YF_SESSION = cffi_requests.Session(impersonate="chrome")

HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#0e0e0e;color:#fff;font-family:Arial;margin:0;padding:10px}
.top{text-align:center;color:#ffeb00;font-size:32px;font-weight:bold;padding:15px;background:#1a1a1a;border-radius:12px;margin-bottom:10px}
.badge{text-align:center;background:#2a2a2a;padding:10px;border-radius:10px;margin-bottom:10px}
.green{background:#00e676;color:#000;padding:12px;border-radius:10px;text-align:center;font-weight:bold;margin-bottom:10px}
.card{border:2px solid #00e676;border-radius:12px;padding:10px;margin-bottom:8px;background:#1e1e1e}
.sell{border-color:#ff5252}
.entry{font-size:13px;color:#aaa}
</style></head><body>
<div class="top" id="clock">00:00:00</div>
<div class="badge">🟢 V72.4.1 BILANCIATO FIX - {{pending|length}} attivi - {{history|length}} totali oggi - Pending:{{pending|length}} Cooldown:{{cooldown|length}} - 21 PAIRS</div>
<div class="green">✅ SUONO ON</div>
{% for h in pending[::-1] %}
<div class="card {{'sell' if h.signal=='SELL' else ''}}">
🎯 {{h.symbol}} {{h.signal}} {{h.lavoro}} ⏰ {{h.scadenza}} {{h.time_str}} RSI{{h.rsi}}<br>
<span class="entry">Entry {{h.entry}}</span>
</div>
{% endfor %}
<div style="background:#1a1a1a;padding:10px;border-radius:10px;margin-top:15px">
<b>📊 SEGNALI V72.4.1</b><br>
{% for h in history[::-1][:20] %}
{{h.time_str}} {{h.symbol}} {{h.lavoro}} <span style="color:{{'red' if h.signal=='SELL' else '#00e676'}}">{{h.signal}} ⏰{{h.scadenza}} RSI{{h.rsi}}</span><br>
{% endfor %}
</div>
<div style="text-align:center;margin-top:15px;background:#333;padding:12px;border-radius:10px" onclick="testSound()">🔔 TEST SUONO</div>
<script>
function upd(){document.getElementById('clock').innerText=new Date().toLocaleTimeString('it-IT')}setInterval(upd,1000);upd();
function testSound(){let a=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');a.play()}
setTimeout(()=>location.reload(),60000);
</script>
</body></html>
"""

@app.route('/')
def home():
    return render_template_string(HTML, pending=pending, cooldown=cooldown, history=history)

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
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()
def stochastic(df,k=14,d=3):
    lo=df['Low'].rolling(k).min(); hi=df['High'].rolling(k).max()
    return 100*((df['Close']-lo)/(hi-lo))

def scan():
    global pending, history
    pending=[p for p in pending if time.time()-p['time']<1800]
    count_this_scan=0
    for symbol in PAIRS:
        if count_this_scan>=3: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 2400: continue
        if any(p['symbol']==clean for p in pending): continue
        try:
            df=yf.Ticker(symbol, session=_YF_SESSION).history(period="5d", interval="15m")
            df=fix_df(df)
            if len(df)<210: continue
            df['e20']=df['Close'].ewm(span=20).mean(); df['e50']=df['Close'].ewm(span=50).mean(); df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma50']=df['atr'].rolling(50).mean(); df['stoch_k']=stochastic(df)
            last=df.iloc[-1]
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
            price=c; rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
            e20=float(last['e20']); e50=float(last['e50']); e200=float(last['e200'])
            is_green=c>o; is_red=not is_green; body=abs(c-o); rng=h-l; upper=h-max(o,c); lower=min(o,c)-l
            if last['atr'] < last['atr_ma50']*0.58: continue
            if last['atr'] > last['atr_ma50']*2.20: continue
            tocco_e20=abs(price-e20)/price < 0.0045
            if abs(price-e200)/price < 0.0005: continue
            slope_e20 = float(df['e20'].iloc[-1] - df['e20'].iloc[-3])
            signal=None; lavoro=""; scadenza=""
            if not signal:
                if price>e200 and e20>e50 and slope_e20>=0 and 28<=rsi_v<=53 and stoch_k<38 and is_green and tocco_e20:
                    signal="BUY"; lavoro="L1 TREND"; scadenza="30 MIN"
                if price<e200 and e20<e50 and slope_e20<=0 and 57<=rsi_v<=72 and stoch_k>62 and is_red and tocco_e20:
                    if not (57<=rsi_v<=59 and slope_e20>-0.00010):
                        signal="SELL"; lavoro="L1 TREND"; scadenza="15 MIN"
            if not signal and rng>0:
                pin_bull = lower > body*2.0 and body < rng*0.45 and upper < body*1.1 and is_green
                pin_bear = upper > body*2.0 and body < rng*0.45 and lower < body*1.1 and is_red
                if pin_bull and price>e200 and e20>e50 and 28<=rsi_v<=54:
                    signal="BUY"; lavoro="L2 PINBAR"; scadenza="30 MIN"
                if pin_bear and price<e200 and e20<e50 and 46<=rsi_v<=72:
                    signal="SELL"; lavoro="L2 PINBAR"; scadenza="15 MIN"
            if signal:
                if clean in ["EURGBP","EURJPY","GBPCHF","EURAUD"]: scadenza="30 MIN"
                time_str=datetime.now().strftime("%d/%m %H:%M")
                item={"symbol":clean,"signal":signal,"entry":f"{price:.5f}","time":time.time(),"time_str":time_str,"rsi":int(rsi_v),"lavoro":lavoro,"scadenza":scadenza}
                pending.append(item); history.append(item); cooldown[clean]=time.time()
                send(f"🎯 {lavoro} {signal} {clean} ⏰ {scadenza} RSI{int(rsi_v)} STO{int(stoch_k)}\nEntry {price:.5f}")
                count_this_scan+=1
        except Exception as e: print(f"ERR {clean}: {e}"); continue

def loop():
    time.sleep(3)
    if TOKEN and CHAT_ID: send("🚀 V72.4.1 BILANCIATO FIX AVVIATO - Pagina FIXATA, ora vedi i segnali")
    while True:
        try: scan()
        except Exception as e: print(f"LOOP ERR {e}")
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
