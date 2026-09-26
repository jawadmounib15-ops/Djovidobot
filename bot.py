import os, time, requests, yfinance as yf, threading, pandas as pd, datetime
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V119 8 LAVORI WEEKEND/REAL SWITCH ONLINE"
@app.route('/ping')
def ping(): return "OK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

OTC_LIST = ["EURUSD_otc","GBPUSD_otc","USDJPY_otc","AUDUSD_otc","USDCHF_otc","USDCAD_otc","EURJPY_otc","GBPJPY_otc","EURGBP_otc","AUDJPY_otc","CADJPY_otc","CHFJPY_otc","EURCHF_otc","GBPCHF_otc","AUDCHF_otc","EURAUD_otc","GBPAUD_otc","EURCAD_otc","AUDCAD_otc","NZDCAD_otc"]
MAP_OTC = {"EURUSD_otc":"EURUSD=X","GBPUSD_otc":"GBPUSD=X","USDJPY_otc":"USDJPY=X","AUDUSD_otc":"AUDUSD=X","USDCHF_otc":"USDCHF=X","USDCAD_otc":"USDCAD=X","EURJPY_otc":"EURJPY=X","GBPJPY_otc":"GBPJPY=X","EURGBP_otc":"EURGBP=X","AUDJPY_otc":"AUDJPY=X","CADJPY_otc":"CADJPY=X","CHFJPY_otc":"CHFJPY=X","EURCHF_otc":"EURCHF=X","GBPCHF_otc":"GBPCHF=X","AUDCHF_otc":"AUDCHF=X","EURAUD_otc":"EURAUD=X","GBPAUD_otc":"GBPAUD=X","EURCAD_otc":"EURCAD=X","AUDCAD_otc":"AUDCAD=X","NZDCAD_otc":"NZDCAD=X"}

REAL_LIST = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","EURJPY","GBPJPY","EURGBP","AUDJPY","CADJPY","CHFJPY","EURCHF","GBPCHF","AUDCHF","EURAUD","GBPAUD","EURCAD","AUDCAD","NZDCAD"]
MAP_REAL = {p:f"{p}=X" for p in REAL_LIST}

COOLDOWN = {}
LAST_SIGNAL = {}
LAST_PRICE = {}

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

def pinbar(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0,False,100
    body = abs(o-c)
    body_pct = (body/rng)*100
    buy = ((min(o,c)-l)/rng)*100
    sell = ((h-max(o,c))/rng)*100
    perfect = body_pct < 30 and (buy>=50 or sell>=50)
    return buy,sell,perfect,body_pct

def engulfing(o1,c1,o2,c2):
    bull = c2 > o2 and c1 < o1 and c2 > o1 and o2 < c1
    bear = c2 < o2 and c1 > o1 and c2 < o1 and o2 > c1
    return bull,bear

def inside_bar(h1,l1,h2,l2): return h2 < h1 and l2 > l1

def get_active_market():
    day = datetime.datetime.utcnow().weekday()
    is_weekend = day >= 5
    if is_weekend: return OTC_LIST, MAP_OTC, "OTC WEEKEND"
    else: return REAL_LIST, MAP_REAL, "REAL WEEKDAY"

def bot():
    while True:
        try:
            ACTIVE_LIST, MAP_ACTIVE, MODE = get_active_market()
            send(f"✅ *V119 {MODE} ONLINE*\n1.Pinbar 2.M15 3.Cooldown 4.Engulfing 5.Inside 6.H1 7.AntiLag 8.AntiDup - {len(ACTIVE_LIST)} coppie")

            while True:
                ACTIVE_LIST, MAP_ACTIVE, MODE = get_active_market()
                for pair in ACTIVE_LIST:
                    try:
                        time.sleep(1.2)
                        yahoo = MAP_ACTIVE[pair]
                        display = pair if "otc" not in pair else pair.replace('_otc','-OTC')

                        df1 = fix_df(yf.download(yahoo, period="2d", interval="1m", progress=False, auto_adjust=True))
                        df5 = fix_df(yf.download(yahoo, period="5d", interval="5m", progress=False, auto_adjust=True))
                        df15 = fix_df(yf.download(yahoo, period="5d", interval="15m", progress=False, auto_adjust=True))
                        if len(df1)<10 or len(df5)<10 or len(df15)<10: continue

                        # LAVORO 6: H1 TREND
                        trend_h1 = get_h1_trend(yahoo)
                        # LAVORO 2: M15
                        o15=float(df15["Open"].values[-2]); h15=float(df15["High"].values[-2]); l15=float(df15["Low"].values[-2]); c15=float(df15["Close"].values[-2])
                        buy15,sell15,perf15,body15 = pinbar(o15,h15,l15,c15)
                        # LAVORO 7: ANTI-LAG
                        c1_price = float(df1["Close"].values[-2])
                        if LAST_PRICE.get(pair)==f"{c1_price:.5f}": continue
                        LAST_PRICE[pair]=f"{c1_price:.5f}"
                        # LAVORO 3: COOLDOWN + LAVORO 8: ANTI-DUP
                        if pair in COOLDOWN and time.time() - COOLDOWN[pair] < 300: continue

                        o1=float(df1["Open"].values[-2]); h1=float(df1["High"].values[-2]); l1=float(df1["Low"].values[-2]); c1=float(df1["Close"].values[-2])
                        o5=float(df5["Open"].values[-2]); h5=float(df5["High"].values[-2]); l5=float(df5["Low"].values[-2]); c5=float(df5["Close"].values[-2])
                        buy1,sell1,perf1,body1 = pinbar(o1,h1,l1,c1)
                        buy5,sell5,perf5,body5 = pinbar(o5,h5,l5,c5)

                        signal_found=None
                        # LAVORO 1: PINBAR
                        if buy1>=15 and buy5>=15 and perf1 and perf5 and trend_h1 in ["BULL","NEUTRAL"]:
                            signal_found=f"📌 *PINBAR BUY {display}*\nM1:{buy1:.0f}% M5:{buy5:.0f}% H1:{trend_h1} [{MODE}]"
                        elif sell1>=15 and sell5>=15 and perf1 and perf5 and trend_h1 in ["BEAR","NEUTRAL"]:
                            signal_found=f"📌 *PINBAR SELL {display}*\nM1:{sell1:.0f}% M5:{sell5:.0f}% H1:{trend_h1} [{MODE}]"
                        # LAVORO 2: M15 FORTE
                        if not signal_found:
                            if buy15>=30 and body15<25 and trend_h1=="BULL":
                                signal_found=f"⏰ *M15 BUY {display}*\nM15:{buy15:.0f}% H1:{trend_h1} [{MODE}]"
                            elif sell15>=30 and body15<25 and trend_h1=="BEAR":
                                signal_found=f"⏰ *M15 SELL {display}*\nM15:{sell15:.0f}% H1:{trend_h1} [{MODE}]"
                        # LAVORO 4: ENGULFING
                        if not signal_found:
                            o1p=float(df1["Open"].values[-3]); c1p=float(df1["Close"].values[-3])
                            bull_eng,bear_eng=engulfing(o1p,c1p,o1,c1)
                            if bull_eng and trend_h1=="BULL": signal_found=f"🔥 *ENGULF BUY {display}* [{MODE}] H1:{trend_h1}"
                            elif bear_eng and trend_h1=="BEAR": signal_found=f"🔥 *ENGULF SELL {display}* [{MODE}] H1:{trend_h1}"
                        # LAVORO 5: INSIDE BAR BREAKOUT
                        if not signal_found:
                            h1p=float(df1["High"].values[-3]); l1p=float(df1["Low"].values[-3])
                            if inside_bar(h1p,l1p,h1,l1):
                                if c1>h1p and trend_h1=="BULL": signal_found=f"📦 *INSIDE BUY {display}* Breakout UP [{MODE}]"
                                elif c1<l1p and trend_h1=="BEAR": signal_found=f"📦 *INSIDE SELL {display}* Breakout DOWN [{MODE}]"

                        if signal_found:
                            key=f"{pair}_{signal_found[:25]}"
                            if LAST_SIGNAL.get(pair)==key: continue
                            COOLDOWN[pair]=time.time(); LAST_SIGNAL[pair]=key
                            send(signal_found+f"\n👉 *POCKET*")
                            print(signal_found, flush=True)
                    except Exception as e:
                        print(f"ERR {pair} {e}", flush=True)
                        continue
                time.sleep(8)
        except Exception as e:
            print(f"LOOP ERR {e}", flush=True); time.sleep(10)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
