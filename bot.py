import os, time, requests, yfinance as yf, threading, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V107 40 COPPIE REALI+OTC LARGHE 10% ONLINE"
@app.route('/ping')
def ping(): return "OK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

# 20 REALI + 20 OTC - pinbar cerca su tutte
REAL = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCHF=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X","CADJPY=X","CHFJPY=X","EURCHF=X","GBPCHF=X","AUDCHF=X","EURAUD=X","GBPAUD=X","EURCAD=X","AUDCAD=X","NZDCAD=X"]
OTC = ["EURUSD_otc","GBPUSD_otc","USDJPY_otc","AUDUSD_otc","USDCHF_otc","USDCAD_otc","EURJPY_otc","GBPJPY_otc","EURGBP_otc","AUDJPY_otc","CADJPY_otc","CHFJPY_otc","EURCHF_otc","GBPCHF_otc","AUDCHF_otc","EURAUD_otc","GBPAUD_otc","EURCAD_otc","AUDCAD_otc","NZDCAD_otc"]

# Mappa OTC -> dato reale Yahoo
MAP = {otc: real for otc, real in zip(OTC, REAL)}
ALL = REAL + OTC

COOLDOWN = {}

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
        print(m, flush=True)
    except: pass

def pinbar(o,h,l,c):
    rng=h-l
    if rng==0: return 0,0
    return ((min(o,c)-l)/rng)*100, ((h-max(o,c))/rng)*100

def get_trend(yahoo_pair, tf):
    try:
        df=yf.download(yahoo_pair, period="10d" if tf=="1h" else "20d", interval=tf, progress=False, auto_adjust=True)
        if len(df)<200: return "NEUTRAL"
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        ema200 = df["Close"].ewm(span=200).mean().iloc[-1]
        c = float(df["Close"].iloc[-1])
        return "BUY" if c>ema200 else "SELL"
    except: return "NEUTRAL"

def bot():
    send("✅ *V107 40 COPPIE REALI+OTC LARGHE 10% ONLINE*\n• 20 Reali + 20 OTC = 40 coppie\n• Pinbar cerca su TUTTE\n• M1 10% + M5 5% LARGO\n• H1 OR H4\n• BUY=BUY DIRETTO")

    while True:
        try:
            for block in range(0, len(ALL), 5):
                chunk = ALL[block:block+5]
                print(f"SCAN BLOCCO {block//8+1}/8: {chunk}", flush=True)

                for pair in chunk:
                    if pair in COOLDOWN and time.time() - COOLDOWN[pair] < 60:
                        continue

                    # Se è OTC prende dato reale Yahoo
                    yahoo_pair = MAP.get(pair, pair)
                    is_otc = "_otc" in pair
                    display = pair.replace('=X','').replace('_otc','-OTC')

                    try:
                        df1 = yf.download(yahoo_pair, period="2d", interval="1m", progress=False, auto_adjust=True)
                        if len(df1)<10: continue
                        if isinstance(df1.columns,pd.MultiIndex): df1.columns=df1.columns.get_level_values(0)
                        o1,h1,l1,c1 = float(df1["Open"].iloc[-2]), float(df1["High"].iloc[-2]), float(df1["Low"].iloc[-2]), float(df1["Close"].iloc[-2])
                        buy1,sell1 = pinbar(o1,h1,l1,c1)

                        df5 = yf.download(yahoo_pair, period="5d", interval="5m", progress=False, auto_adjust=True)
                        if len(df5)<10: continue
                        if isinstance(df5.columns,pd.MultiIndex): df5.columns=df5.columns.get_level_values(0)
                        o5,h5,l5,c5 = float(df5["Open"].iloc[-2]), float(df5["High"].iloc[-2]), float(df5["Low"].iloc[-2]), float(df5["Close"].iloc[-2])
                        buy5,sell5 = pinbar(o5,h5,l5,c5)

                        trend_h1 = get_trend(yahoo_pair, "1h")
                        trend_h4 = get_trend(yahoo_pair, "4h")

                        sig=None; perc=0
                        if buy1>=10 and buy5>=5:
                            if trend_h1=="BUY" or trend_h4=="BUY":
                                sig="BUY"; perc=buy1
                        elif sell1>=10 and sell5>=5:
                            if trend_h1=="SELL" or trend_h4=="SELL":
                                sig="SELL"; perc=sell1

                        if sig:
                            COOLDOWN[pair]=time.time()
                            tag = "OTC" if is_otc else "REALE"
                            send(f"💎 *M1+M5 {sig} {display} 10% {tag}*\nM1:{perc:.0f}% M5:{buy5 if sig=='BUY' else sell5:.0f}%\nH1:{trend_h1} H4:{trend_h4}\n👉 *POCKET: {sig} DIRETTO*")

                    except Exception as e:
                        print(f"ERR {pair} {e}", flush=True)
                        continue

                time.sleep(5)

            time.sleep(3)
        except Exception as e:
            print(f"LOOP ERR {e}", flush=True)
            time.sleep(10)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
