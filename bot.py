import os, time, requests, yfinance as yf, threading, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V117 8 LAVORI M1 M5 M15 H1 ONLINE"
@app.route('/ping')
def ping(): return "OK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

OTC_LIST = ["EURUSD_otc","GBPUSD_otc","USDJPY_otc","AUDUSD_otc","USDCHF_otc","USDCAD_otc","EURJPY_otc","GBPJPY_otc","EURGBP_otc","AUDJPY_otc","CADJPY_otc","CHFJPY_otc","EURCHF_otc","GBPCHF_otc","AUDCHF_otc","EURAUD_otc","GBPAUD_otc","EURCAD_otc","AUDCAD_otc","NZDCAD_otc"]
MAP = {"EURUSD_otc":"EURUSD=X","GBPUSD_otc":"GBPUSD=X","USDJPY_otc":"USDJPY=X","AUDUSD_otc":"AUDUSD=X","USDCHF_otc":"USDCHF=X","USDCAD_otc":"USDCAD=X","EURJPY_otc":"EURJPY=X","GBPJPY_otc":"GBPJPY=X","EURGBP_otc":"EURGBP=X","AUDJPY_otc":"AUDJPY=X","CADJPY_otc":"CADJPY=X","CHFJPY_otc":"CHFJPY=X","EURCHF_otc":"EURCHF=X","GBPCHF_otc":"GBPCHF=X","AUDCHF_otc":"AUDCHF=X","EURAUD_otc":"EURAUD=X","GBPAUD_otc":"GBPAUD=X","EURCAD_otc":"EURCAD=X","AUDCAD_otc":"AUDCAD=X","NZDCAD_otc":"NZDCAD=X"}

COOLDOWN = {}
LAST_SIGNAL = {}
LAST_PRICE = {}

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
        print(m, flush=True)
    except: pass

def pinbar(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0,False,100
    body = abs(o-c)
    body_pct = (body/rng)*100
    buy = ((min(o,c)-l)/rng)*100
    sell = ((h-max(o,c))/rng)*100
    perfect = body_pct < 30 and (buy>=50 or sell>=50)
    return buy,sell,perfect,body_pct

def fix_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()

def get_h1_trend(yahoo):
    try:
        dfh = fix_df(yf.download(yahoo, period="5d", interval="1h", progress=False, auto_adjust=True))
        if len(dfh)<5: return "NEUTRAL"
        ema20 = dfh["Close"].rolling(20).mean().values[-2]
        close = float(dfh["Close"].values[-2])
        if close > ema20: return "BULL"
        elif close < ema20: return "BEAR"
        else: return "NEUTRAL"
    except: return "NEUTRAL"

def bot():
    send("✅ *V117 8 LAVORI ONLINE*\nM1+M5+M15 15% + H1 TREND + Anti-Lag/Dup")

    while True:
        try:
            for pair_otc in OTC_LIST:
                if pair_otc in COOLDOWN and time.time() - COOLDOWN[pair_otc] < 300:
                    continue
                yahoo = MAP[pair_otc]
                display = pair_otc.replace('_otc','-OTC')
                try:
                    time.sleep(1.5)

                    # M1
                    df1 = fix_df(yf.download(yahoo, period="2d", interval="1m", progress=False, auto_adjust=True))
                    if len(df1)<10: continue
                    o1 = float(df1["Open"].values[-2]); h1 = float(df1["High"].values[-2]); l1 = float(df1["Low"].values[-2]); c1 = float(df1["Close"].values[-2])
                    buy1,sell1,perf1,body1 = pinbar(o1,h1,l1,c1)

                    price_key = f"{c1:.5f}"
                    if LAST_PRICE.get(pair_otc)==price_key:
                        continue
                    LAST_PRICE[pair_otc]=price_key

                    # M5
                    df5 = fix_df(yf.download(yahoo, period="5d", interval="5m", progress=False, auto_adjust=True))
                    if len(df5)<10: continue
                    o5 = float(df5["Open"].values[-2]); h5 = float(df5["High"].values[-2]); l5 = float(df5["Low"].values[-2]); c5 = float(df5["Close"].values[-2])
                    buy5,sell5,perf5,body5 = pinbar(o5,h5,l5,c5)

                    # M15 NUOVO LAVORO
                    df15 = fix_df(yf.download(yahoo, period="5d", interval="15m", progress=False, auto_adjust=True))
                    if len(df15)<10: continue
                    o15 = float(df15["Open"].values[-2]); h15 = float(df15["High"].values[-2]); l15 = float(df15["Low"].values[-2]); c15 = float(df15["Close"].values[-2])
                    buy15,sell15,perf15,body15 = pinbar(o15,h15,l15,c15)

                    # H1 TREND
                    trend_h1 = get_h1_trend(yahoo)

                    print(f"{display} M1:{buy1:.0f}/{sell1:.0f} M5:{buy5:.0f}/{sell5:.0f} M15:{buy15:.0f}/{sell15:.0f} H1:{trend_h1}", flush=True)

                    sig=None
                    # 8 LAVORI: M1 15% + M5 15% + M15 15% + H1 + PERFETTA
                    if buy1>=15 and buy5>=15 and buy15>=15 and perf1 and perf5 and perf15:
                        if trend_h1 in ["BULL","NEUTRAL"]:
                            sig="BUY"; p1=buy1; p5=buy5; p15=buy15
                    elif sell1>=15 and sell5>=15 and sell15>=15 and perf1 and perf5 and perf15:
                        if trend_h1 in ["BEAR","NEUTRAL"]:
                            sig="SELL"; p1=sell1; p5=sell5; p15=sell15

                    if sig:
                        key = f"{display}_{sig}_{int(p1)}"
                        if LAST_SIGNAL.get(pair_otc)==key:
                            continue
                        COOLDOWN[pair_otc]=time.time()
                        LAST_SIGNAL[pair_otc]=key
                        send(f"💎 *{sig} {display} M1/M5/M15*\nM1:{p1:.0f}% M5:{p5:.0f}% M15:{p15:.0f}%\nH1:{trend_h1} Corpo:{body1:.0f}%\n👉 *POCKET: {sig}*")

                except Exception as e:
                    print(f"ERR {pair_otc} {e}", flush=True)
                    continue
            time.sleep(10)
        except Exception as e:
            print(f"LOOP ERR {e}", flush=True)
            time.sleep(10)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
