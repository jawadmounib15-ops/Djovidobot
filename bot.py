import os, time, requests, threading, yfinance as yf, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "BOT PINBAR REALI BALANCED LIVE"

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","USDCHF=X","AUDUSD=X","NZDUSD=X","EURGBP=X","USDCAD=X","GBPCHF=X"]
last_signal={}

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()))

def bot():
    send("📌 *BOT PINBAR REALI BALANCED ACCESO*\n3 Regole - Non troppo stretto - 80%")
    while True:
        try:
            for pair in PAIRS:
                try:
                    df=yf.download(pair,period="2d",interval="1m",progress=False)
                    if len(df)<210: continue
                    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)

                    df["EMA200"]=df["Close"].ewm(span=200).mean()
                    df["RSI"]=rsi(df["Close"])
                    df["MA20"]=df["Close"].rolling(20).mean()
                    df["STD"]=df["Close"].rolling(20).std()
                    df["LOW"]=df["MA20"]-2.0*df["STD"]
                    df["UP"]=df["MA20"]+2.0*df["STD"]

                    c=df["Close"].iloc[-1]
                    o=df["Open"].iloc[-1]
                    h=df["High"].iloc[-1]
                    l=df["Low"].iloc[-1]
                    ema200=df["EMA200"].iloc[-1]
                    r=df["RSI"].iloc[-1]
                    r_prev=df["RSI"].iloc[-2]
                    low=df["LOW"].iloc[-1]
                    up=df["UP"].iloc[-1]
                    nome=pair.replace("=X","")

                    if nome in last_signal and time.time()-last_signal[nome] < 900: continue # 15 min

                    body = abs(c-o)
                    upper_wick = h - max(c,o)
                    lower_wick = min(c,o) - l
                    total_range = h-l
                    if total_range==0 or body==0: continue

                    # 3 REGOLE BILANCIATE - NON STRETTE
                    # REGOLA 1: Forma 2.2x (non 3x) + corpo 30% (non 20%)
                    bull_forma = lower_wick >= body*2.2 and body <= total_range*0.30 and c > o
                    bear_forma = upper_wick >= body*2.2 and body <= total_range*0.30 and c < o

                    # REGOLA 2: Location 60% coda (non 70%) + Boll 2.0 (non 2.2) + RSI 38/62 (non 32/68)
                    bull_loc = lower_wick >= total_range*0.60 and (l <= low*1.01 or l <= ema200*1.001) and r < 38
                    bear_loc = upper_wick >= total_range*0.60 and (h >= up*0.99 or h >= ema200*0.999) and r > 62

                    # REGOLA 3: Chiusura + RSI gira
                    bull_close = r > r_prev
                    bear_close = r < r_prev

                    if bull_forma and bull_loc and bull_close:
                        last_signal[nome]=time.time()
                        send(f"📌🔵 *{nome} PINBAR BUY 80%*\nForma {lower_wick/body:.1f}x ✅ Coda 60% ✅\nBoll/EMA200 + RSI {r:.0f} -> {r_prev:.0f} ✅\n5m BUY")

                    if bear_forma and bear_loc and bear_close:
                        last_signal[nome]=time.time()
                        send(f"📌🔴 *{nome} PINBAR SELL 80%*\nForma {upper_wick/body:.1f}x ✅ Coda 60% ✅\nBoll/EMA200 + RSI {r:.0f} -> {r_prev:.0f} ✅\n5m SELL")

                except: continue
            time.sleep(60)
        except: time.sleep(30)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
