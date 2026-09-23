import os, time, requests, threading, yfinance as yf, pandas as pd
from datetime import datetime
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "BOT V111 LARGO LIVE - 30 SEGNALI AL GIORNO"

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")

PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURGBP=X","AUDUSD=X","NZDUSD=X","USDCAD=X","USDCHF=X","GBPCHF=X","EURCHF=X","CADJPY=X","CHFJPY=X"]

def send(m):
 try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except: pass

def rsi(s,p=14):
 d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
 return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()))

def bot():
 send("🔵 *BOT V111 LARGO ACCESO*\n30-50 segnali/giorno - Entra solo se vedi supporto/resistenza tuo!")
 while True:
  try:
   for pair in PAIRS:
    try:
     df=yf.download(pair,period="2d",interval="5m",progress=False)
     if len(df)<210: continue
     if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
     
     df["EMA200"]=df["Close"].ewm(span=200).mean()
     df["RSI"]=rsi(df["Close"])
     df["EMA12"]=df["Close"].ewm(span=12).mean()
     df["EMA26"]=df["Close"].ewm(span=26).mean()
     df["MACD"]=df["EMA12"]-df["EMA26"]
     df["SIGNAL"]=df["MACD"].ewm(span=9).mean()

     c=df["Close"].iloc[-1]
     ema=df["EMA200"].iloc[-1]
     r=df["RSI"].iloc[-1]
     r_prev=df["RSI"].iloc[-2]
     macd=df["MACD"].iloc[-1]
     macd_prev=df["MACD"].iloc[-2]
     sig=df["SIGNAL"].iloc[-1]

     # MOLTO LARGO - BASTA 1 CONDIZIONE!
     buy_score = 0
     if c > ema: buy_score += 1
     if r < 50 and r > r_prev: buy_score += 1
     if macd > macd_prev: buy_score += 1
     if r < 40: buy_score += 1

     sell_score = 0
     if c < ema: sell_score += 1
     if r > 50 and r < r_prev: sell_score += 1
     if macd < macd_prev: sell_score += 1
     if r > 60: sell_score += 1

     nome=pair.replace('=X','')
     # Se ha 2 punti su 4 = MANDA SEGNALE
     if buy_score >= 2:
      send(f"🔵 *{nome} BUY {buy_score}/4*\nPrezzo {' >' if c>ema else ' <'} EMA200 | RSI {r:.0f} {'↗️' if r>r_prev else '↘️'} | MACD {'↗️' if macd>macd_prev else '↘️'}\n5m")

     if sell_score >= 2:
      send(f"🔴 *{nome} SELL {sell_score}/4*\nPrezzo {' >' if c>ema else ' <'} EMA200 | RSI {r:.0f} {'↗️' if r>r_prev else '↘️'} | MACD {'↗️' if macd>macd_prev else '↘️'}\n5m")

    except: continue
   time.sleep(120) # Ogni 2 minuti!
  except: time.sleep(30)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
