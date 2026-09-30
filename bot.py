# bot.py TEST ULTRA LARGO + HEARTBEAT
from flask import Flask, render_template_string
import threading, time, os, pytz, pandas as pd
from datetime import datetime
from curl_cffi import requests as crequests
import requests as req

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")
TOKEN = os.environ.get("TELEGRAM_TOKEN","").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID","").strip()

def send_tg(txt):
    if not TOKEN or not CHAT_ID: return
    try: req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":txt,"parse_mode":"Markdown"}, timeout=15)
    except: pass

COPPIE = ["EURUSD=X","GBPUSD=X","USDJPY=X"]

def get_df(ticker, interval, range_):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_}"
        r=crequests.get(url, impersonate="chrome110", timeout=20)
        j=r.json()
        res=j['chart']['result'][0]; ts=res['timestamp']; q=res['indicators']['quote'][0]
        df=pd.DataFrame({"Open":q['open'],"High":q['high'],"Low":q['low'],"Close":q['close']}, index=pd.to_datetime(ts,unit='s')).dropna()
        return df
    except Exception as e:
        print(f"YAHOO ERR {ticker}: {e}")
        return pd.DataFrame()

stato={"live":0,"msg":"avvio"}

def loop():
    count=0
    while True:
        count+=1
        # heartbeat ogni 2 min per test TG
        if count%2==0:
            send_tg(f"💓 *TEST* Bot vivo {datetime.now(ROMA).strftime('%H:%M:%S')} - Se vedi questo TG OK")

        live=0
        for cp in COPPIE:
            df=get_df(cp,"5m","1d")
            if not df.empty: live+=1
            else: continue
            O,H,L,C = float(df.iloc[-1]['Open']),float(df.iloc[-1]['High']),float(df.iloc[-1]['Low']),float(df.iloc[-1]['Close'])
            body=abs(C-O); rng=H-L
            if rng==0: continue
            nose=max(H-max(O,C), min(O,C)-L)/rng*100
            if nose>50: # ULTRA LARGO 50%
                send_tg(f"🟡 *PINBAR {nose:.0f}%* {cp} M5\nO {O} C {C} - {'CALL' if C>O else 'PUT'} 30m")
                stato["msg"]=f"{cp} {nose:.0f}%"
        stato["live"]=live
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

@app.route('/')
def home():
    return f"LIVE {stato['live']}/3 - {stato['msg']} - {datetime.now(ROMA)} - TG {'ON' if TOKEN else 'OFF'}"

if __name__=="__main__":
    send_tg("✅ TEST AVVIATO - tra 2 min arriva heartbeat")
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
