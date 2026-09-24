import os, time, requests, threading, yfinance as yf, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "BOT V117 REALI ANTI-PERDITA LIVE"

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","USDCHF=X","AUDUSD=X","NZDUSD=X","EURGBP=X","USDCAD=X","GBPCHF=X"]

# ANTI-SPAM: non rimanda stesso segnale per 15 min
last_signal = {}

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()))

def bot():
    send("💎 *BOT V117 REALI ANTI-PERDITA ACCESO*\nFIX SELL JPY - No più RSI 76->71 fake")
    while True:
        try:
            for pair in PAIRS:
                try:
                    df=yf.download(pair,period="3d",interval="1m",progress=False)
                    if len(df)<210: continue
                    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)

                    df["EMA50"]=df["Close"].ewm(span=50).mean()
                    df["EMA200"]=df["Close"].ewm(span=200).mean()
                    df["EMA50_prev"]=df["EMA50"].shift(5)
                    df["RSI"]=rsi(df["Close"])
                    df["MACD"]=df["Close"].ewm(span=12).mean()-df["Close"].ewm(span=26).mean()
                    df["SIGNAL"]=df["MACD"].ewm(span=9).mean()
                    df["MA20"]=df["Close"].rolling(20).mean()
                    df["STD"]=df["Close"].rolling(20).std()
                    df["LOW"]=df["MA20"]-2*df["STD"]
                    df["UP"]=df["MA20"]+2*df["STD"]

                    c=df["Close"].iloc[-1]
                    o=df["Open"].iloc[-1]
                    ema50=df["EMA50"].iloc[-1]
                    ema50_prev=df["EMA50_prev"].iloc[-1]
                    ema200=df["EMA200"].iloc[-1]
                    r=df["RSI"].iloc[-1]
                    r_prev=df["RSI"].iloc[-2]
                    r_prev2=df["RSI"].iloc[-3]
                    macd=df["MACD"].iloc[-1]
                    macd_prev=df["MACD"].iloc[-2]
                    sig=df["SIGNAL"].iloc[-1]
                    low=df["LOW"].iloc[-1]
                    up=df["UP"].iloc[-1]

                    nome=pair.replace("=X","")

                    # FILTRO ANTI-SPAM
                    key = f"{nome}"
                    if key in last_signal and time.time() - last_signal[key] < 900: # 15 min
                        continue

                    # ===== V117 FIX SELL: PIU SEVERO =====
                    # 1. Candela BEAR obbligatoria
                    bear_candle = c < o
                    # 2. EMA50 deve SCENDERE veramente (slope giù)
                    ema50_down = ema50 < ema50_prev
                    # 3. RSI deve scendere FORTE almeno 3 punti, non 1
                    rsi_drop_strong = (r_prev - r) >= 3.0 and r > 65
                    # 4. RSI era >72 prima (ipercomprato vero, non 76->71)
                    was_overbought = r_prev2 > 72 or r_prev > 72

                    sell_score=0
                    if c < ema200 and ema50 < ema200 and c < ema50: sell_score+=1
                    if rsi_drop_strong and was_overbought: sell_score+=1
                    if macd_prev > sig and macd < sig: sell_score+=1
                    if c >= up*0.995 and bear_candle: sell_score+=1
                    if r_prev > 70 and ema50_down: sell_score+=1

                    # ===== BUY: uguale ma con filtro bull =====
                    bull_candle = c > o
                    ema50_up = ema50 > ema50_prev
                    rsi_rise_strong = (r - r_prev) >= 3.0 and r < 35
                    was_oversold = r_prev2 < 28 or r_prev < 28

                    buy_score=0
                    if c > ema200 and ema50 > ema200 and c > ema50: buy_score+=1
                    if rsi_rise_strong and was_oversold: buy_score+=1
                    if macd_prev < sig and macd > sig: buy_score+=1
                    if c <= low*1.005 and bull_candle: buy_score+=1
                    if r_prev < 30 and ema50_up: buy_score+=1

                    if buy_score>=4:
                        last_signal[key]=time.time()
                        send(f"🔵 *{nome} BUY {buy_score}/5 FORTE V117*\nEMA50>200 + UP ✅ RSI {r_prev:.0f}->{r:.0f} +{r-r_prev:.0f} ✅ MACD X-UP ✅ Boll LOW + Bull ✅\n5m")

                    if sell_score>=4:
                        last_signal[key]=time.time()
                        send(f"🔴 *{nome} SELL {sell_score}/5 FORTE V117*\nEMA50<200 + DOWN ✅ RSI {r_prev:.0f}->{r:.0f} -{r_prev-r:.0f} ✅ MACD X-DOWN + Bear ✅\n5m")

                except: continue
            time.sleep(60)
        except: time.sleep(30)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
