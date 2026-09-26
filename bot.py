import os, time, requests, yfinance as yf, threading, pandas as pd, datetime, random
from datetime import timezone
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V127 FIX 429 MEDIO-STRETTO ONLINE"
@app.route('/ping')
def ping(): return "OK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

REAL_LIST = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","EURJPY","GBPJPY","EURGBP","AUDJPY"]
MAP_REAL = {p:f"{p}=X" for p in REAL_LIST}

COOLDOWN, LAST_SIGNAL, LAST_PRICE, H1_CACHE, H1_TIME = {}, {}, {}, {}, {}

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass
def fix_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df.dropna()
def get_h1_cached(yahoo):
    now=time.time()
    if yahoo in H1_CACHE and now - H1_TIME.get(yahoo,0) < 1800: return H1_CACHE[yahoo]
    try:
        time.sleep(1)
        dfh = fix_df(yf.download(yahoo, period="5d", interval="1h", progress=False, auto_adjust=True))
        if len(dfh)<20: return "NEUTRAL"
        ema20 = dfh["Close"].rolling(20).mean().values[-2]
        close = float(dfh["Close"].values[-2])
        t="BULL" if close>ema20 else "BEAR" if close<ema20 else "NEUTRAL"
        H1_CACHE[yahoo]=t; H1_TIME[yahoo]=now; return t
    except: return "NEUTRAL"
def pinbar(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0,100
    body=abs(o-c); bp=(body/rng)*100
    buy=((min(o,c)-l)/rng)*100; sell=((h-max(o,c))/rng)*100
    return buy,sell,bp

def bot():
    while True:
        try:
            send("✅ *V127 FIX 429 MEDIO ONLINE - 10 coppie REAL*")
            while True:
                for pair in REAL_LIST:
                    try:
                        if pair in COOLDOWN and time.time()-COOLDOWN[pair]<180: continue
                        yahoo=MAP_REAL[pair]
                        # ANTI-429: sleep + 1 download solo
                        time.sleep(random.uniform(1.0,2.0))
                        df1=fix_df(yf.download(yahoo, period="1d", interval="1m", progress=False, auto_adjust=True))
                        if len(df1)<30: continue
                        df5=df1.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                        if len(df5)<10: continue
                        c1_price=float(df1["Close"].values[-2])
                        if LAST_PRICE.get(pair)==f"{c1_price:.5f}": continue
                        LAST_PRICE[pair]=f"{c1_price:.5f}"
                        trend=get_h1_cached(yahoo)
                        o1=float(df1["Open"].values[-2]); h1=float(df1["High"].values[-2]); l1=float(df1["Low"].values[-2]); c1=float(df1["Close"].values[-2])
                        o5=float(df5["Open"].values[-2]); h5=float(df5["High"].values[-2]); l5=float(df5["Low"].values[-2]); c5=float(df5["Close"].values[-2])
                        b1,s1,bd1=pinbar(o1,h1,l1,c1); b5,s5,bd5=pinbar(o5,h5,l5,c5)
                        sig=None
                        if b1>=10 and b5>=10 and bd1<30 and bd5<30 and c1>o1 and c5>o5 and trend=="BULL":
                            sig=f"📌 *PINBAR BUY {pair}* M1:{b1:.0f}% M5:{b5:.0f}%"
                        elif s1>=10 and s5>=10 and bd1<30 and bd5<30 and c1<o1 and c5<o5 and trend=="BEAR":
                            sig=f"📌 *PINBAR SELL {pair}* M1:{s1:.0f}% M5:{s5:.0f}%"
                        elif not sig and b1>=30 and bd1<25 and c1>o1 and trend=="BULL":
                            sig=f"⚡ *M1 BUY {pair}* {b1:.0f}% B{bd1:.0f}%"
                        elif not sig and s1>=30 and bd1<25 and c1<o1 and trend=="BEAR":
                            sig=f"⚡ *M1 SELL {pair}* {s1:.0f}% B{bd1:.0f}%"
                        elif not sig and b5>=25 and bd5<30 and c5>o5 and c1>o1 and trend=="BULL":
                            sig=f"📊 *M5 BUY {pair}* M5:{b5:.0f}%"
                        elif not sig and s5>=25 and bd5<30 and c5<o5 and c1<o1 and trend=="BEAR":
                            sig=f"📊 *M5 SELL {pair}* M5:{s5:.0f}%"
                        if sig:
                            if LAST_SIGNAL.get(pair)==sig: continue
                            COOLDOWN[pair]=time.time(); LAST_SIGNAL[pair]=sig
                            send(sig+"\n👉 *POCKET*"); print(sig, flush=True)
                    except Exception as e:
                        print(f"ERR {pair} {e}", flush=True)
                        time.sleep(2)
                        continue
                time.sleep(5)
        except Exception as e:
            print(f"LOOP ERR {e}", flush=True); time.sleep(10)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
