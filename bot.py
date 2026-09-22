import os,time,requests,yfinance as yf,threading,pandas as pd
from datetime import datetime,timedelta
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():return "V74 EMA500 ULTRA LOSS COMPLETO"
def rf():
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
threading.Thread(target=rf,daemon=True).start()
TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X"]
WIN=0;LOSS=0;PEND={};LAST={};CHECK=0
def send(m):
 try:requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except:pass
send("💀 *V74 EMA500 ULTRA LOSS COMPLETO ATTIVO*\n📉 TF 5M | ⏰ 5M tra segnali | 📊 Result 5M")

while True:
 try:
  now=datetime.now()
  # CALCOLO AUTOMATICO LOSS E WIN DOPO 5 MIN
  for k in list(PEND.keys()):
   s,p,t=PEND[k]
   if now-t>=timedelta(minutes=5):
    try:
     df=yf.download(k,period="1d",interval="1m",progress=False)
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     c=float(df["Close"].iloc[-1])
     w=(s=="BUY" and c>p) or (s=="SELL" and c<p)
     if w:
      WIN+=1
      R="✅ WIN"
     else:
      LOSS+=1
      R="❌ LOSS"
     tot=WIN+LOSS
     wr=WIN/tot*100 if tot>0 else 0
     send(f"{R} *{k.replace('=X','')} {s}*\nEntrata {p:.5f} -> Ora {c:.5f}\n📊 WIN {WIN} LOSS {LOSS} WR {wr:.0f}%")
     del PEND[k]
    except:pass

  # TIMEFRAME 5 MIN + 5 MIN TRA I SEGNALI
  if time.time()-CHECK>=300: # ROVINATO: ogni 5 min esatti 8 segnali
   CHECK=time.time()
   for pair in PAIRS:
    try:
     # TIMEFRAME 5 MIN
     df=yf.download(pair,period="10d",interval="5m",progress=False)
     if len(df)<500:continue
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     e500=df["Close"].ewm(span=500).mean().iloc[-1]
     delta=df["Close"].diff()
     gain=delta.where(delta>0,0).rolling(14).mean()
     loss=-delta.where(delta<0,0).rolling(14).mean()
     rsi=100-(100/(1+gain/loss))
     r=float(rsi.iloc[-1])
     cl=float(df["Close"].iloc[-1])

     # ROVINATO AL 100% - ENTRA TARDI E PERDE
     last5=df["Close"].iloc[-5:].tolist()
     trend_up=last5[-1]>last5[0]
     trend_down=last5[-1]<last5[0]
     dist=abs(cl-e500)/e500*100

     # SOLO SE LONTANO DA EMA = ESAUSTO
     if dist<0.4: continue

     # SBAGLIATO APPOSTA PER PERDERE: compra al TOP e vende al BOTTOM
     if cl>e500 and r>70 and trend_up:
      sig="BUY" # TOP di uptrend = poi crolla = LOSS
     elif cl<e500 and r<30 and trend_down:
      sig="SELL" # BOTTOM di downtrend = poi sale = LOSS
     else: continue

     PEND[pair]=(sig,cl,now)
     LAST[pair]=now
     send(f"💀 *5M {sig} {pair.replace('=X','')}*\nEMA500 {e500:.5f}\nRSI {r:.0f}\nPrice {cl:.5f}\nDIST {dist:.2f}% TREND {'UP' if trend_up else 'DOWN'}\n⏳ Result tra 5 min")
    except:pass
 except:pass
 time.sleep(3)
