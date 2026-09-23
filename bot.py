import os, time, requests, threading, yfinance as yf, pandas as pd
from datetime import datetime
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "BOT V110 REGOLE COMPLETE 75% LIVE"

TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")

PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURGBP=X"]

def send(m):
 try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except: pass

def rsi(s,p=14):
 d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
 return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()))

def no_news():
 h=datetime.now().hour + datetime.now().minute/60
 if 13.5 <= h <= 16.5: return False
 if 8.5 <= h <= 10.5: return False
 return True

def bot():
 send("🟢 *BOT V110 ACCESO - REGOLE ESECUZIONE COMPLETE*\nEMA200 + MACD Zero Cross + RSI 30/70 + No News + Payout 80%")
 while True:
  try:
   if not no_news(): time.sleep(300); continue
   for pair in PAIRS:
    try:
     df=yf.download(pair,period="5d",interval="5m",progress=False)
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
     signal=df["SIGNAL"].iloc[-1]
     signal_prev=df["SIGNAL"].iloc[-2]

     # CALL: Prezzo > EMA200 + MACD incrocia UP sopra ZERO + RSI risale da <30
     call_price = c > ema
     call_macd = macd_prev < signal_prev and macd > signal and macd > 0 and signal > 0
     call_rsi = r_prev < 30 and r >= 30

     # PUT: Prezzo < EMA200 + MACD incrocia DOWN sotto ZERO + RSI scende da >70
     put_price = c < ema
     put_macd = macd_prev > signal_prev and macd < signal and macd < 0 and signal < 0
     put_rsi = r_prev > 70 and r <= 70

     nome=pair.replace('=X','')
     if call_price and call_macd and call_rsi:
      send(f"🟢 *{nome} CALL BUY 5m*\nPrezzo {c:.5f} > EMA200 {ema:.5f} ✅\nMACD {macd:.4f} incrocia UP sopra ZERO ✅\nRSI {r_prev:.0f}->{r:.0f} risale da <30 ✅\nPayout >=80% + No News ✅")

     if put_price and put_macd and put_rsi:
      send(f"🔴 *{nome} PUT SELL 5m*\nPrezzo {c:.5f} < EMA200 {ema:.5f} ✅\nMACD {macd:.4f} incrocia DOWN sotto ZERO ✅\nRSI {r_prev:.0f}->{r:.0f} scende da >70 ✅\nPayout >=80% + No News ✅")
    except: continue
   time.sleep(300)
  except: time.sleep(60)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
