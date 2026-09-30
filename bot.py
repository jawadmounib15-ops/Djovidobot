# bot.py - PULITO 45% - SOLO SEGNALI, NIENTE TEST
from flask import Flask, render_template_string
import threading, time, os, pytz, pandas as pd
from datetime import datetime
from curl_cffi import requests as crequests
import requests as req

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")

NOSE_MIN = 45
BODY_MAX = 55
TOL = 0.30

TOKEN = os.environ.get("TELEGRAM_TOKEN","").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID","").strip()

COPPIE = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDUSD=X","USDCAD=X","NZDUSD=X","EURGBP=X","USDCHF=X"]
NOMI = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDUSD=X":"AUD/USD","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","EURGBP=X":"EUR/GBP","USDCHF=X":"USD/CHF"}

def send_tg(txt):
    if not TOKEN or not CHAT_ID: return
    try: req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":txt,"parse_mode":"Markdown"}, timeout=15)
    except: pass

def ema(s,n): return s.ewm(span=n).mean()

def get_df(ticker, interval, range_):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_}"
        r=crequests.get(url, impersonate="chrome110", timeout=20)
        j=r.json()
        if j['chart']['result'] is None: return pd.DataFrame()
        res=j['chart']['result'][0]; ts=res['timestamp']; q=res['indicators']['quote'][0]
        df=pd.DataFrame({"Open":q['open'],"High":q['high'],"Low":q['low'],"Close":q['close']}, index=pd.to_datetime(ts,unit='s')).dropna()
        return df
    except: return pd.DataFrame()

def is_pinbar(last, prev):
    O,H,L,C=float(last['Open']),float(last['High']),float(last['Low']),float(last['Close'])
    Ph,Pl=float(prev['High']),float(prev['Low'])
    body=abs(C-O); rng=H-L
    if rng==0: return False,"",0,0
    upper=H-max(O,C); lower=min(O,C)-L
    nose=max(upper,lower); nose_pct=nose/rng*100; body_pct=body/rng*100
    if nose_pct < NOSE_MIN: return False,"",nose_pct,body_pct
    if body_pct > BODY_MAX: return False,"",nose_pct,body_pct
    tol=rng*TOL
    if min(O,C) < Pl - tol: return False,"",nose_pct,body_pct
    if max(O,C) > Ph + tol: return False,"",nose_pct,body_pct
    tipo="BULLISH" if lower>upper else "BEARISH"
    return True,tipo,nose_pct,body_pct

stato={"live":0,"sig":"Avvio...","best":"-"}

def lavoro():
    last_sig=""
    while True:
        try:
            best=0; best_cp=""; live=0
            for cp in COPPIE:
                df=get_df(cp,"5m","5d")
                if df.empty or len(df)<30: continue
                live+=1
                df['EMA21']=ema(df['Close'],21)
                last=df.iloc[-1]; prev=df.iloc[-2]

                O,H,L,C=float(last['Open']),float(last['High']),float(last['Low']),float(last['Close'])
                rng=H-L
                if rng>0:
                    cur = max(H-max(O,C), min(O,C)-L)/rng*100
                    if cur>best: best=cur; best_cp=cp

                ok,tipo,nose,body=is_pinbar(last,prev)
                if not ok: continue
                # filtro trend largo
                up = last['Close'] > last['EMA21']
                if tipo=="BULLISH" and not up: continue
                if tipo=="BEARISH" and up: continue

                sig=f"{NOMI[cp]} {tipo} {nose:.0f}%"
                if sig!=last_sig:
                    send_tg(f"🟢 *{NOMI[cp]} {tipo} {nose:.0f}%*\n📏 Naso {nose:.0f}% Body {body:.0f}%\n⏰ {'CALL 30m' if tipo=='BULLISH' else 'PUT 30m'}")
                    last_sig=sig; stato["sig"]=sig
                    break

            stato["live"]=live
            stato["best"]=f"{best_cp} {best:.0f}%"
            if best_cp=="": stato["sig"]=f"LIVE {live}/10 - mercato piatto, best {best:.0f}%"
        except: pass
        time.sleep(60)

threading.Thread(target=lavoro, daemon=True).start()

@app.route('/')
def home():
    return render_template_string("<body style='background:#111;color:#fff;font-family:Arial;padding:20px'><h3>PULITO {{live}}/10 BEST {{best}}</h3><div>{{sig}}</div><small>{{ora}}</small><script>setTimeout(()=>location.reload(),15000)</script></body>", live=stato["live"], best=stato["best"], sig=stato["sig"], ora=datetime.now(ROMA).strftime("%H:%M:%S"))

if __name__=="__main__":
    send_tg(f"✅ Bot pulito avviato - soglia {NOSE_MIN}% - solo segnali veri")
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
