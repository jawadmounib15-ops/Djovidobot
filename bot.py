import os, time, requests, yfinance as yf, threading, pandas as pd, datetime, concurrent.futures
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V123 ANTI-LAG 10 LAVORI ONLINE"
@app.route('/ping')
def ping(): return "OK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

OTC_LIST = ["EURUSD_otc","GBPUSD_otc","USDJPY_otc","AUDUSD_otc","USDCHF_otc","USDCAD_otc","EURJPY_otc","GBPJPY_otc","EURGBP_otc","AUDJPY_otc","CADJPY_otc","CHFJPY_otc","EURCHF_otc","GBPCHF_otc","AUDCHF_otc","EURAUD_otc","GBPAUD_otc","EURCAD_otc","AUDCAD_otc","NZDCAD_otc"]
MAP_OTC = {"EURUSD_otc":"EURUSD=X","GBPUSD_otc":"GBPUSD=X","USDJPY_otc":"USDJPY=X","AUDUSD_otc":"AUDUSD=X","USDCHF_otc":"USDCHF=X","USDCAD_otc":"USDCAD=X","EURJPY_otc":"EURJPY=X","GBPJPY_otc":"GBPJPY=X","EURGBP_otc":"EURGBP=X","AUDJPY_otc":"AUDJPY=X","CADJPY_otc":"CADJPY=X","CHFJPY_otc":"CHFJPY=X","EURCHF_otc":"EURCHF=X","GBPCHF_otc":"GBPCHF=X","AUDCHF_otc":"AUDCHF=X","EURAUD_otc":"EURAUD=X","GBPAUD_otc":"GBPAUD=X","EURCAD_otc":"EURCAD=X","AUDCAD_otc":"AUDCAD=X","NZDCAD_otc":"NZDCAD=X"}
REAL_LIST = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","EURJPY","GBPJPY","EURGBP","AUDJPY","CADJPY","CHFJPY","EURCHF","GBPCHF","AUDCHF","EURAUD","GBPAUD","EURCAD","AUDCAD","NZDCAD"]
MAP_REAL = {p:f"{p}=X" for p in REAL_LIST}

COOLDOWN, LAST_SIGNAL, LAST_PRICE, LAST_M15, H1_CACHE, H1_TIME = {}, {}, {}, {}, {}, {}

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass
def fix_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    return df.dropna()
def get_h1_trend(yahoo):
    try:
        dfh = fix_df(yf.download(yahoo, period="5d", interval="1h", progress=False, auto_adjust=True))
        if len(dfh)<25: return "NEUTRAL"
        ema20 = dfh["Close"].rolling(20).mean().values[-2]
        close = float(dfh["Close"].values[-2])
        return "BULL" if close > ema20 else "BEAR" if close < ema20 else "NEUTRAL"
    except: return "NEUTRAL"
def get_h1_cached(yahoo):
    now=time.time()
    if yahoo in H1_CACHE and now - H1_TIME.get(yahoo,0) < 900: return H1_CACHE[yahoo]
    t=get_h1_trend(yahoo); H1_CACHE[yahoo]=t; H1_TIME[yahoo]=now; return t
def pinbar(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0,100
    body = abs(o-c); body_pct=(body/rng)*100
    buy=((min(o,c)-l)/rng)*100; sell=((h-max(o,c))/rng)*100
    return buy,sell,body_pct
def get_active_market():
    day=datetime.datetime.utcnow().weekday()
    return (OTC_LIST, MAP_OTC, "OTC WEEKEND") if day>=5 else (REAL_LIST, MAP_REAL, "REAL WEEKDAY")

def process_pair(pair, MAP_ACTIVE, MODE):
    try:
        yahoo=MAP_ACTIVE[pair]
        display=pair if "otc" not in pair else pair.replace('_otc','-OTC')
        # ANTI-LAG: 1 download solo M1, poi ricavo M5 M15
        df1=fix_df(yf.download(yahoo, period="2d", interval="1m", progress=False, auto_adjust=True))
        if len(df1)<30: return
        df5=df1.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
        df15=df1.resample('15min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
        if len(df5)<10 or len(df15)<10: return
        m15_time=str(df15.index[-2])
        if LAST_M15.get(pair)==m15_time: return
        c1_price=float(df1["Close"].values[-2])
        if LAST_PRICE.get(pair)==f"{c1_price:.5f}": return
        LAST_PRICE[pair]=f"{c1_price:.5f}"
        if pair in COOLDOWN and time.time()-COOLDOWN[pair]<600: return
        trend_h1=get_h1_cached(yahoo)
        o1=float(df1["Open"].values[-2]); h1=float(df1["High"].values[-2]); l1=float(df1["Low"].values[-2]); c1=float(df1["Close"].values[-2])
        o5=float(df5["Open"].values[-2]); h5=float(df5["High"].values[-2]); l5=float(df5["Low"].values[-2]); c5=float(df5["Close"].values[-2])
        o15=float(df15["Open"].values[-2]); h15=float(df15["High"].values[-2]); l15=float(df15["Low"].values[-2]); c15=float(df15["Close"].values[-2])
        buy1,sell1,body1=pinbar(o1,h1,l1,c1); buy5,sell5,body5=pinbar(o5,h5,l5,c5); buy15,sell15,body15=pinbar(o15,h15,l15,c15)
        signal_found=None

        # 1-2 PINBAR V119
        if buy1>=15 and buy5>=15 and body1<25 and body5<25 and c1>o1 and c5>o5 and trend_h1=="BULL":
            signal_found=f"📌 *PINBAR BUY {display}* M1:{buy1:.0f}% M5:{buy5:.0f}% [{MODE}]"
        elif sell1>=15 and sell5>=15 and body1<25 and body5<25 and c1<o1 and c5<o5 and trend_h1=="BEAR":
            signal_found=f"📌 *PINBAR SELL {display}* M1:{sell1:.0f}% M5:{sell5:.0f}% [{MODE}]"
        # 3-4 ENGULFING
        if not signal_found:
            try:
                o5p=float(df5["Open"].values[-3]); c5p=float(df5["Close"].values[-3])
                if c5>o5 and c5p<o5p and c5>o5p and o5<c5p and body5<30 and trend_h1=="BULL": signal_found=f"🔥 *ENGULF BUY {display}* [{MODE}]"
                elif c5<o5 and c5p>o5p and c5<o5p and o5>c5p and body5<30 and trend_h1=="BEAR": signal_found=f"🔥 *ENGULF SELL {display}* [{MODE}]"
            except: pass
        # 5-6 INSIDE BAR
        if not signal_found:
            try:
                h5p=float(df5["High"].values[-3]); l5p=float(df5["Low"].values[-3])
                if h5<h5p and l5>l5p and c5>o5 and trend_h1=="BULL": signal_found=f"📦 *INSIDE BUY {display}* [{MODE}]"
                elif h5<h5p and l5>l5p and c5<o5 and trend_h1=="BEAR": signal_found=f"📦 *INSIDE SELL {display}* [{MODE}]"
            except: pass
        # 7 M15 TRIPLA FILTRO BUONO
        if not signal_found:
            if buy15>=30 and buy5>=15 and buy1>=15 and body15<20 and c15>o15 and c5>o5 and c1>o1 and trend_h1=="BULL":
                signal_found=f"⏰ *M15 BUY {display}* M15:{buy15:.0f}% M5:{buy5:.0f}% M1:{buy1:.0f}% [{MODE}]"
            elif sell15>=30 and sell5>=15 and sell1>=15 and body15<20 and c15<o15 and c5<o5 and c1<o1 and trend_h1=="BEAR":
                signal_found=f"⏰ *M15 SELL {display}* M15:{sell15:.0f}% M5:{sell5:.0f}% M1:{sell1:.0f}% [{MODE}]"
        # 8 MOMENTUM
        if not signal_found:
            if body1>60 and body5>60 and c1>o1 and c5>o5 and trend_h1=="BULL": signal_found=f"🚀 *MOM BUY {display}* [{MODE}]"
            elif body1>60 and body5>60 and c1<o1 and c5<o5 and trend_h1=="BEAR": signal_found=f"🚀 *MOM SELL {display}* [{MODE}]"
        # 9 M1 STRETTA 50%+ NUOVO
        if not signal_found:
            if buy1>=50 and body1<15 and c1>o1 and trend_h1=="BULL": signal_found=f"⚡ *M1 BUY {display}* {buy1:.0f}% B{body1:.0f}% [{MODE}]"
            elif sell1>=50 and body1<15 and c1<o1 and trend_h1=="BEAR": signal_found=f"⚡ *M1 SELL {display}* {sell1:.0f}% B{body1:.0f}% [{MODE}]"
        # 10 M5 MEDIA 40%+ NUOVO
        if not signal_found:
            if buy5>=40 and body5<20 and c5>o5 and c1>o1 and trend_h1=="BULL": signal_found=f"📊 *M5 BUY {display}* M5:{buy5:.0f}% M1:{buy1:.0f}% [{MODE}]"
            elif sell5>=40 and body5<20 and c5<o5 and c1<o1 and trend_h1=="BEAR": signal_found=f"📊 *M5 SELL {display}* M5:{sell5:.0f}% M1:{sell1:.0f}% [{MODE}]"

        if signal_found:
            key=f"{pair}_{m15_time}_{signal_found[:30]}"
            if LAST_SIGNAL.get(pair)==key: return
            COOLDOWN[pair]=time.time(); LAST_SIGNAL[pair]=key; LAST_M15[pair]=m15_time
            send(signal_found+"\n👉 *POCKET*"); print(signal_found, flush=True)
    except Exception as e: print(f"ERR {pair} {e}", flush=True)

def bot():
    while True:
        try:
            ACTIVE_LIST, MAP_ACTIVE, MODE = get_active_market()
            send(f"✅ *V123 ANTI-LAG ONLINE {MODE}*\n10 lavori - 1 download - 5x parallelo")
            while True:
                ACTIVE_LIST, MAP_ACTIVE, MODE = get_active_market()
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures=[executor.submit(process_pair, p, MAP_ACTIVE, MODE) for p in ACTIVE_LIST]
                    concurrent.futures.wait(futures)
                time.sleep(3)
        except Exception as e:
            print(f"LOOP ERR {e}", flush=True); time.sleep(10)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
