# bot.py - PIN BAR DOPPIA 5M + 15M - DECIDE LUI SCADENZA
import os, time, requests, yfinance as yf
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "PIN BAR 5M + 15M OK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")
ITALY_TZ = timezone(timedelta(hours=2))

BASE = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","USDCHF=X","BTC-USD"]
LABELS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","USD/CAD-OTC","EUR/JPY-OTC","USD/CHF-OTC","BTC/USD-OTC"]
LABELS_REALI = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD","EUR/JPY","USD/CHF","BTC/USD"]
ALL = list(zip(BASE, LABELS_OTC, LABELS_REALI))

LAST={}
AVVIO=False

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_df(y, interval, period):
    try:
        df=yf.download(y, period=period, interval=interval, progress=False, auto_adjust=False)
        if len(df)<30: return None
        if hasattr(df.columns,'get_level_values'):
            try: df.columns=df.columns.get_level_values(0)
            except: pass
        return df
    except: return None

# PINBAR 5 MINUTI = 5 candele da 1m
def check_5m(y):
    df=get_df(y,"1m","2d")
    if df is None: return None
    last5=df.iloc[-5:]
    o=float(last5.iloc[0]['Open']); cc=float(last5.iloc[-1]['Close'])
    h=float(last5['High'].max()); l=float(last5['Low'].min())
    body=abs(cc-o); rng=h-l
    if rng==0 or body>rng*0.30: return None
    up=h-max(o,cc); low=min(o,cc)-l
    bull=low>2.5*body and low>rng*0.60 and up<rng*0.20
    bear=up>2.5*body and up>rng*0.60 and low<rng*0.20
    if bull: return "BUY", int((low/rng)*100)
    if bear: return "SELL", int((up/rng)*100)
    return None

# PINBAR 15 MINUTI = 1 candela da 15m
def check_15m(y):
    df=get_df(y,"15m","5d")
    if df is None: return None
    c=df.iloc[-1]; o=float(c['Open']); cc=float(c['Close']); h=float(c['High']); l=float(c['Low'])
    body=abs(cc-o); rng=h-l
    if rng==0 or body>rng*0.25: return None
    up=h-max(o,cc); low=min(o,cc)-l
    bull=low>3*body and low>rng*0.65 and up<rng*0.15
    bear=up>3*body and up>rng*0.65 and low<rng*0.15
    if bull: return "BUY", int((low/rng)*100)
    if bear: return "SELL", int((up/rng)*100)
    return None

def bot_loop():
    global AVVIO
    if not AVVIO:
        send(f"✅ *PIN BAR 5M + 15M ATTIVA*\nBot decide scadenza da solo\nOTC + REALI\n{datetime.now(ITALY_TZ).strftime('%H:%M:%S')} ITALIA")
        AVVIO=True
    while True:
        try:
            for base, otc, reali in ALL:
                now=datetime.now(ITALY_TZ)
                # CONTROLLO 5M
                sec_5m = (5-now.minute%5)*60-now.second
                if 20 <= sec_5m <= 110:
                    res5 = check_5m(base)
                    if res5:
                        dir5, perc5 = res5
                        for label in [otc, reali]:
                            key=f"{label}_5M_{dir5}"
                            if key in LAST and time.time()-LAST[key]<300: continue
                            msg=f"📌 *PIN BAR 5M*\n{label}\n{'🟢 BUY 5M' if dir5=='BUY' else '🔴 SELL 5M'}\nWick {perc5}% | {sec_5m}s mancanti\n⏰ {now.strftime('%H:%M:%S')} ITALIA\nDecide bot: scadenza 5M"
                            send(msg); LAST[key]=time.time()

                # CONTROLLO 15M
                min_left_15 = 15 - (now.minute % 15)
                if min_left_15 <= 3: # ultimi 3 min del 15M
                    res15 = check_15m(base)
                    if res15:
                        dir15, perc15 = res15
                        for label in [otc, reali]:
                            key=f"{label}_15M_{dir15}"
                            if key in LAST and time.time()-LAST[key]<900: continue
                            msg=f"📌📌 *PIN BAR 15M SICURA* 📌📌\n{label}\n{'🟢 BUY 15M' if dir15=='BUY' else '🔴 SELL 15M'}\nWick {perc15}% perfetta\n⏰ {now.strftime('%H:%M:%S')} ITALIA\nDecide bot: scadenza 15M PIU SICURA"
                            send(msg); LAST[key]=time.time()
                time.sleep(0.8)
            time.sleep(3)
        except Exception as e:
            print(e); time.sleep(5)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
