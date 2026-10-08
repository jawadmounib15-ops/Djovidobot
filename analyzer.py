import os, time
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)
pending=[]; cooldown={}; history=[]; last_debug="V75.36 1MIN->5MIN pronto"; scan_count=0; pair_index=0; last_scan=0

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
<div class="badge">🟢 V75.36 1MIN->5MIN - {{pending|length}} attivi - {{history|length}} oggi - Scan:{{scan_count}} - Idx:{{pair_idx}}/21</div>
<div class="green" onclick="let a=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');a.play()">✅ SUONO ON - 1MIN SCAN 5MIN SCAD - 2.3x 42%</div>
{% for h in pending[::-1] %}
<div class="card {{'sell' if h.signal=='SELL' else ''}}">
🎯 {{h.symbol}} {{h.signal}} <span class="exp">⏰ {{h.scadenza}}</span> {{h.time_str}} RSI{{h.rsi}} coda{{h.tail}}x<br>
<span style="font-size:11px">Entry {{h.entry}} | 1m pinbar -> 5m scad</span>
</div>
{% endfor %}
<div style="background:#1a1a1a;padding:8px;border-radius:8px;margin-top:10px">
<b>📊 STORICO 1MIN -> 5MIN SCAD</b><br>
{% for h in history[::-1][:30] %}
{{h.time_str}} {{h.symbol}} <span style="color:{{'red' if h.signal=='SELL' else '#00e676'}}">{{h.signal}} ⏰{{h.scadenza}} RSI{{h.rsi}}</span><br>
{% endfor %}
</div>
<div class="debug">DEBUG: {{last_debug}}<br>{{now}} | 1MIN SCAN 5MIN SCAD | 2.3x 42%</div>
<script>function upd(){document.getElementById('clock').innerText=new Date().toLocaleTimeString('it-IT')}setInterval(upd,1000);upd();setTimeout(()=>location.reload(),15000);</script>
</body></html>
"""

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

def do_scan():
    global pending, history, last_debug, scan_count, pair_index, last_scan
    if time.time()-last_scan<25: return
    last_scan=time.time(); scan_count+=1
    pending=[p for p in pending if time.time()-p['time']<320]
    batch=PAIRS[pair_index:pair_index+7]
    if len(batch)<7: batch+=PAIRS[:7-len(batch)]
    pair_index=(pair_index+7)%21
    checked=0; found=0
    for symbol in batch:
        if len(pending)>=2: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean]<1200: continue
        if any(p['symbol']==clean for p in pending): continue
        try:
            # 1 MIN CANDELE PER PINBAR
            df=yf.Ticker(symbol).history(period="1d", interval="1m", auto_adjust=False)
            df=fix_df(df)
            checked+=1
            if len(df)<50: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e50']=df['Close'].ewm(span=50).mean()
            df['rsi']=rsi(df['Close'])
            last=df.iloc[-1]
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
            rsi_v=float(last['rsi']) if not pd.isna(last['rsi']) else 50
            e20=float(last['e20']); e50=float(last['e50'])
            body=abs(c-o); rng=h-l
            if rng==0 or body==0: continue
            upper=h-max(o,c); lower=min(o,c)-l; is_green=c>o
            pin_bull = lower > body*2.3 and body < rng*0.42 and upper < body*0.65 and is_green
            pin_bear = upper > body*2.3 and body < rng*0.42 and lower < body*0.65 and not is_green
            if not (pin_bull or pin_bear): continue
            found+=1
            tail=lower/body if pin_bull else upper/body
            t=datetime.now().strftime("%d/%m %H:%M")
            if pin_bull and e20>e50 and 30<=rsi_v<=55:
                item={"symbol":clean,"signal":"BUY","entry":f"{c:.5f}","time":time.time(),"time_str":t,"rsi":int(rsi_v),"tail":f"{tail:.1f}","scadenza":"5 MIN"}
                pending.append(item); history.append(item); cooldown[clean]=time.time()
                send(f"🎯 1m PINBAR BUY {clean} ⏰ 5 MIN RSI{int(rsi_v)} coda {tail:.1f}x")
            if pin_bear and e20<e50 and 50<=rsi_v<=70:
                item={"symbol":clean,"signal":"SELL","entry":f"{c:.5f}","time":time.time(),"time_str":t,"rsi":int(rsi_v),"tail":f"{tail:.1f}","scadenza":"5 MIN"}
                pending.append(item); history.append(item); cooldown[clean]=time.time()
                send(f"🎯 1m PINBAR SELL {clean} ⏰ 5 MIN RSI{int(rsi_v)} coda {tail:.1f}x")
        except: continue
    last_debug=f"Scan {scan_count} OK 1m->5m viste {checked} pinbar {found} attivi {len(pending)}"

@app.route('/')
def home():
    do_scan()
    return render_template_string(HTML, pending=pending, cooldown=cooldown, history=history, last_debug=last_debug, scan_count=scan_count, pair_idx=pair_index, now=datetime.now().strftime("%H:%M:%S"))
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
