# Analyzer.py V21.1 - SOLO 30M - SINGLE FILE - FIX per gunicorn analyzer:app
import yfinance as yf
import pandas as pd
import time, threading, os
from datetime import datetime
from zoneinfo import ZoneInfo
from curl_cffi import requests as cffi_requests
from flask import Flask, render_template_string

_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
SCADENZA = 30
RITRACC = 0.70
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCAD=X"]

# === FLASK APP - QUESTO E' QUELLO CHE CERCAVA GUNICORN E NON TROVAVA ===
app = Flask(__name__)
live_signals = []
storico = []
stats_30m = 0
cooldown = {}

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df

def rsi(s, p=7):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def pinbar_30m_balanced(df):
    if len(df) < 30: return None
    c=df.iloc[-2]; O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
    total=H-L
    if total<=0: return None
    corpo=abs(O-C); inf=min(O,C)-L; sup=H-max(O,C)
    if corpo>total*0.30: return None
    if inf>=total*0.60 and sup<=total*0.20:
        return {"dir":"SU","target":L+(inf*RITRACC),"forza":inf/total*100,"rsi":0,"O":O,"H":H,"L":L,"C":C}
    if sup>=total*0.60 and inf<=total*0.20:
        return {"dir":"GIÙ","target":H-(sup*RITRACC),"forza":sup/total*100,"rsi":0,"O":O,"H":H,"L":L,"C":C}
    return None

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")

def scanna_30m():
    global live_signals, storico, stats_30m
    now=datetime.now(ITALY)
    if now.weekday()>=5 or now.hour<8 or now.hour>=22: return []
    risultati=[]
    for symbol in PAIRS:
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean]<1800: continue
        try:
            df=fix_df(yf.Ticker(symbol, session=_YF).history(period="60d", interval="30m"))
            if len(df)<30: continue
            df['rsi7']=rsi(df['Close'],7); last_rsi=float(df['rsi7'].iloc[-2])
            pin=pinbar_30m_balanced(df)
            if not pin: continue
            if pin["dir"]=="SU" and last_rsi>35: continue
            if pin["dir"]=="GIÙ" and last_rsi<65: continue
            cooldown[clean]=time.time(); stats_30m+=1
            risultati.append({"asset":clean,"dir":"CALL" if pin["dir"]=="SU" else "PUT","entry":pin["target"],"forza":pin["forza"],"rsi":last_rsi,"ora":ora_it()})
            print(f"[{ora_it()}] 30m {clean} TROVATO")
        except Exception as e:
            print(e); continue
    return risultati

HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V21 SOLO 30M</title><style>
body{background:#0f0f0f;color:#fff;font-family:Arial;padding:15px}
.card{background:#1e1e2e;border-radius:15px;padding:15px;margin:10px 0;border-left:5px solid #ffaa00}
.btn{background:#00ff88;color:#000;padding:15px;border-radius:12px;text-align:center;font-weight:bold;font-size:18px;cursor:pointer;border:none;width:100%}
.orange{border-left-color:#ffaa00}.green{border-left-color:#00ff88}
</style></head><body>
<h2>🎯 V21.1 SOLO 30M - FIXED</h2>
<div class="card"><div>🕐 {{ora}} | Trovati 30m: {{tot}} | Status: LIVE</div></div>
<button class="btn" onclick="fetch('/scanna').then(()=>setTimeout(()=>location.reload(),2000))">🎯 SCANNA 30M BALANCED</button>
<div class="card orange"><h3>✅ SICURA 30 MIN - LIVE: {{live|length}}</h3>
{% for s in live %}<div><b>{{s.asset}} {{s.dir}}</b> - {{s.ora}} - Entry {{'%.5f'%s.entry}} - RSI {{s.rsi|int}}% - Forza {{s.forza|int}}%</div>{% else %}<div>Nessuna - premi SCANNA</div>{% endfor %}</div>
<div class="card green"><h3>📜 STORICO</h3>{% for r in storico %}<div>{{r.ora}} - {{r.asset}} {{r.dir}} - {{'%.5f'%r.entry}}</div>{% else %}<div>Vuoto</div>{% endfor %}</div>
<script>setInterval(()=>location.reload(),60000)</script>
</body></html>
"""

@app.route('/')
def home():
    return render_template_string(HTML, ora=ora_it(), tot=stats_30m, live=live_signals, storico=storico)

@app.route('/scanna')
def route_scanna():
    global live_signals, storico
    res=scanna_30m()
    if res:
        live_signals=res+live_signals; live_signals=live_signals[:10]
        storico=res+storico; storico=storico[:30]
    return f"Trovati {len(res)} segnali"

def loop_auto():
    while True:
        try:
            now=datetime.now(ITALY)
            sleep_sec=(30-(now.minute%30))*60-now.second+5
            if sleep_sec<10: sleep_sec+=1800
            time.sleep(sleep_sec)
            res=scanna_30m()
            if res:
                global live_signals, storico
                live_signals=res+live_signals; storico=res+storico
        except Exception as e:
            print(e); time.sleep(10)

threading.Thread(target=loop_auto, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
