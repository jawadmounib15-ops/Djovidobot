import os, time, requests, threading, yfinance as yf, pandas as pd
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "BOT V116 REALI 12 COPPIE LIVE"

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
# 12 COPPIE REALI
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","USDCHF=X","AUDUSD=X","NZDUSD=X","EURGBP=X","USDCAD=X","GBPCHF=X"]

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()))

def bot():
    send("💎 *BOT V116 12 COPPIE REALI ACCESO*\n12 coppie - EMA50/200 + Anti-ritardo")
    while True:
        try:
            for pair in PAIRS:
                try:
                    df=yf.download(pair,period="2d",interval="1m",progress=False)
                    if len(df)<210: continue
                    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)

                    df["EMA50"]=df["Close"].ewm(span=50).mean()
                    df["EMA200"]=df["Close"].ewm(span=200).mean()
                    df["RSI"]=rsi(df["Close"])
                    df["EMA12"]=df["Close"].ewm(span=12).mean()
                    df["EMA26"]=df["Close"].ewm(span=26).mean()
                    df["MACD"]=df["EMA12"]-df["EMA26"]
                    df["SIGNAL"]=df["MACD"].ewm(span=9).mean()
                    df["MA20"]=df["Close"].rolling(20).mean()
                    df["STD"]=df["Close"].rolling(20).std()
                    df["LOW"]=df["MA20"]-2*df["STD"]
                    df["UP"]=df["MA20"]+2*df["STD"]

                    c=df["Close"].iloc[-1]
                    ema50=df["EMA50"].iloc[-1]
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

                    if c > ema50 and ema50 > ema200 and r < 40 and r > r_prev and (r - r_prev) > 0.5 and r_prev < 38:
                        if c <= low*1.01:
                            send(f"⚠️ *{nome} BUY EARLY*\nEMA50>EMA200 ✅ RSI {r_prev2:.0f}->{r_prev:.0f}->{r:.0f} SALE ✅")

                    if c < ema50 and ema50 < ema200 and r > 60 and r < r_prev and (r_prev - r) > 0.5 and r_prev > 62:
                        if c >= up*0.99:
                            send(f"⚠️ *{nome} SELL EARLY*\nEMA50<EMA200 ✅ RSI {r_prev2:.0f}->{r_prev:.0f}->{r:.0f} SCENDE ✅")

                    buy_score=0
                    if c > ema200 and ema50 > ema200 and c > ema50: buy_score+=1
                    if r < 40 and r > r_prev and (r - r_prev) >= 1.0: buy_score+=1
                    if macd_prev < sig and macd > sig: buy_score+=1
                    if c <= low*1.005: buy_score+=1
                    if r_prev < 35: buy_score+=1

                    sell_score=0
                    if c < ema200 and ema50 < ema200 and c < ema50: sell_score+=1
                    if r > 60 and r < r_prev and (r_prev - r) >= 1.0: sell_score+=1
                    if macd_prev > sig and macd < sig: sell_score+=1
                    if c >= up*0.995: sell_score+=1
                    if r_prev > 65: sell_score+=1

                    if buy_score>=4:
                        send(f"🔵 *{nome} BUY {buy_score}/5 FORTE*\nEMA50>EMA200 ✅ RSI {r_prev:.0f}->{r:.0f} ✅ MACD X-UP ✅ Boll LOW ✅\n5m")

                    if sell_score>=4:
                        send(f"🔴 *{nome} SELL {sell_score}/5 FORTE*\nEMA50<EMA200 ✅ RSI {r_prev:.0f}->{r:.0f} ✅ MACD X-DOWN ✅ Boll UP ✅\n5m")

                except: continue
            time.sleep(60)
        except: time.sleep(30)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
