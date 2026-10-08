import os, time, threading
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)
pending=[]; cooldown={}; history=[]; last_debug="V75.2 ANTI-LAG pronto..."; scan_count=0; thread_started=False
pair_index=0
scan_lock=False

HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#0e0e0e;color:#fff;font-family:Arial;margin:0;padding:10px}
.top{text-align:center;color:#ffeb00;font-size:30px;font-weight:bold;padding:12px;background:#1a1a1a;border-radius:12px;margin-bottom:8px}
.badge{text-align:center;background:#2a2a2a;padding:8px;border-radius:8px;margin-bottom:8px;font-size:12px}
.green{background:#00e676;color:#000;padding:10px;border-radius:8px;text-align:center;font-weight:bold;margin-bottom:8px;cursor:pointer}
.card{border:2px solid #00e676;border-radius:10px;padding:10px;margin-bottom:8px;background:#1e1e1e;font-size:14px}
.sell{border-color:#ff5252}
.exp{color:#ffeb00;font-weight:bold}
.debug{background:#222;padding:7px;border-radius:6px;font-size:10px;color:#aaa;margin-top:8px}
</style></head><body>
<div class="top" id="clock">00:00:00</div>
<div class="badge">🟢 V75.2 ANTI-LAG - {{pending|length}} attivi - {{history|length}} oggi - Scan:{{scan_count}} - Idx:{{pair_idx}}/21 - {{'BUSY' if busy else 'IDLE'}}</div>
<div class="green" onclick="let a=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');a.play()">✅ SUONO ON - ANTI-LAG 2.3x 40%</div>
{% for h in pending[::-1] %}
<div class="card {{'sell' if h.signal=='SELL' else ''}}">
🎯 {{h.symbol}} {{h.signal}} <span class="exp">⏰ {{h.scadenza}}</span> {{h.time_str}} RSI{{h.rsi}} coda{{h.tail}}x
</div>
{% endfor %}
<div style="background:#1a1a1a;padding:8px;border-radius:8px;margin-top:10px">
<b>📊 STORICO 5MIN</b><br>
{% for h in history[::-1][:25] %}
{{h.time_str}} {{h.symbol}} {{h.signal}} ⏰{{h.scadenza}}<br>
{% endfor %}
</div>
<div class="debug">DEBUG: {{last_debug}}<br>{{now}}</div>
<script>function upd(){document.getElementById('clock').innerText=new Date().toLocaleTimeString('it-IT')}setInterval(upd,1000);upd();setTimeout(()=>location.reload(),20000);</script>
</body></html>
"""

@app.route('/')
def home():
    global thread_started
    if not thread_started:
        thread_started=True
        threading.Thread(target=loop, daemon=True).start()
    return render_template_string(HTML, pending=pending, cooldown=cooldown, history=history, last_debug=last_debug, scan_count=scan_count, pair_idx=pair_index, busy=scan_lock, now=datetime.now().strftime("%H:%M:%S"))

def send(msg):
    if not TOKEN or not CHAT_ID: return
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=5)
    except: pass

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def fetch_one(symbol):
    clean=symbol.replace("=X","")
    try:
        # ANTI-LAG: timeout 8s max, period corto
        df=yf.Ticker(symbol).history(period="1d", interval="5m", auto_adjust=False, timeout=8)
        df=fix_df(df)
        if len(df)<40: return None
        df['e20']=df['Close'].ewm(span=20).mean(); df['e50']=df['Close'].ewm(span=50).mean(); df['rsi']=rsi(df['Close'])
        last=df.iloc[-1]
        o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
        rsi_v=float(last['rsi']) if not pd.isna(last['rsi']) else 50; e20=float(last['e20']); e50=float(last['e50'])
        body=abs(c-o); rng=h-l
        if rng==0 or body==0: return None
        upper=h-max(o,c); lower=min(o,c)-l
        is_green=c>o; is_red=not is_green
        pin_bull = lower > body*2.3 and body < rng*0.40 and upper < body*0.7 and is_green
        pin_bear = upper > body*2.3 and body < rng*0.40 and lower < body*0.7 and is_red
        if not (pin_bull or pin_bear): return None
        tail=lower/body if pin_bull else upper/body
        signal="BUY" if pin_bull else "SELL"
        return {"symbol":clean,"c":c,"rsi":rsi_v,"e20":e20,"e50":e50,"tail":tail,"signal":signal,"pin_bull":pin_bull}
    except: return None

def scan():
    global pending, history, last_debug, scan_count, pair_index, scan_lock
    if scan_lock:
        last_debug=f"Skip scan {scan_count} - precedente ancora in corso - anti-lag"
        return
    scan_lock=True
    scan_count+=1
    start_t=time.time()
    try:
        pending=[p for p in pending if time.time()-p['time']<600]
        # ANTI-LAG: 7 coppie a rotazione, non 21
        batch = PAIRS[pair_index:pair_index+7]
        if len(batch)<7: batch = batch + PAIRS[:7-len(batch)]
        pair_index = (pair_index+7) % 21

        checked=0; found=0
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures={ex.submit(fetch_one, s): s for s in batch}
            for fut in as_completed(futures, timeout=25):
                checked+=1
                res=fut.result()
                if not res: continue
                clean=res["symbol"]
                if clean in cooldown and time.time()-cooldown[clean] < 900: continue
                if any(p['symbol']==clean for p in pending): continue
                if len(pending)>=2: break
                found+=1
                if res["pin_bull"] and res["e20"]>res["e50"] and 28<=res["rsi"]<=58:
                    t=datetime.now().strftime("%d/%m %H:%M")
                    item={"symbol":clean,"signal":"BUY","entry":f"{res['c']:.5f}","time":time.time(),"time_str":t,"rsi":int(res["rsi"]),"tail":f"{res['tail']:.1f}","scadenza":"5 MIN"}
                    pending.append(item); history.append(item); cooldown[clean]=time.time()
                    send(f"🎯 PINBAR BUY {clean} ⏰ 5 MIN RSI{int(res['rsi'])} coda {res['tail']:.1f}x")
                elif not res["pin_bull"] and res["e20"]<res["e50"] and 42<=res["rsi"]<=72:
                    t=datetime.now().strftime("%d/%m %H:%M")
                    item={"symbol":clean,"signal":"SELL","entry":f"{res['c']:.5f}","time":time.time(),"time_str":t,"rsi":int(res["rsi"]),"tail":f"{res['tail']:.1f}","scadenza":"5 MIN"}
                    pending.append(item); history.append(item); cooldown[clean]=time.time()
                    send(f"🎯 PINBAR SELL {clean} ⏰ 5 MIN RSI{int(res['rsi'])} coda {res['tail']:.1f}x")

        elapsed=time.time()-start_t
        last_debug=f"Scan {scan_count} OK {elapsed:.1f}s batch {pair_index-7}-{pair_index} viste {checked} pinbar {found} attivi {len(pending)} ANTI-LAG"
    except Exception as e:
        last_debug=f"Scan {scan_count} ERR {str(e)[:80]}"
    finally:
        scan_lock=False

def loop():
    time.sleep(2)
    send("🚀 V75.2 ANTI-LAG AVVIATO - 7 coppie x volta - 3 thread - no lag")
    while True:
        try: scan()
        except: pass
        time.sleep(40)

if not thread_started:
    thread_started=True
    threading.Thread(target=loop, daemon=True).start()

if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
