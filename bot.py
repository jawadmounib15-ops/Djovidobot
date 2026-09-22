import os,time,requests,yfinance as yf,threading,pandas as pd
from datetime import datetime,timedelta
from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():return "V81 ULTRA 0% WIN"
def rf():
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
threading.Thread(target=rf,daemon=True).start()
TOKEN=os.environ.get("TELEGRAM_TOKEN")
CHAT=os.environ.get("TELEGRAM_CHAT_ID")
PAIRS=["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X"]
WIN=0;LOSS=0;PEND={};CHECK=0
def send(m):
 try:requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except:pass

send("💀☠️ *V81 ULTRA - TUTTO AL CONTRARIO - 0% WIN*")

while True:
 try:
  now=datetime.now()
  for k in list(PEND.keys()):
   s,p,t=PEND[k]
   if now-t>=timedelta(minutes=5):
    try:
     df=yf.download(k,period="1d",interval="1m",progress=False)
     if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
     c=float(df["Close"].iloc[-1])
     w=(s=="BUY" and c>p) or (s=="SELL" and c<p)
     if w:WIN+=1;R="✅ WIN"
     else:LOSS+=1;R="❌ LOSS"
     tot=WIN+LOSS;wr=WIN/tot*100 if tot>0 else 0
     send(f"{R} *{k.replace('=X','')} {s}* {p:.5f}->{c:.5f} WR {wr:.0f}%")
     del PEND[k]
    except:pass
  if time.time()-CHECK>=300:
   CHECK=time.time()
   for pair in PAIRS:
    try:
     df5=yf.download(pair,period="10d",interval="5m",progress=False)
     df1h=yf.download(pair,period="20d",interval="1h",progress=False)
     df1d=yf.download(pair,period="100d",interval="1d",progress=False)
     if len(df5)<100 or len(df1h)<100 or len(df1d)<50:continue
     if isinstance(df5.columns,pd.MultiIndex):df5.columns=df5.columns.get_level_values(0)
     if isinstance(df1h.columns,pd.MultiIndex):df1h.columns=df1h.columns.get_level_values(0)
     if isinstance(df1d.columns,pd.MultiIndex):df1d.columns=df1d.columns.get_level_values(0)

     c5=float(df5["Close"].iloc[-1])
     # REGOLA 1: TRIPLO TIMEFRAME CONTRO
     ema1h=float(df1h["Close"].ewm(span=50).mean().iloc[-1])
     ema1d=float(df1d["Close"].ewm(span=50).mean().iloc[-1])
     trend_up = df1h["Close"].iloc[-1]>ema1h and df1d["Close"].iloc[-1]>ema1d
     trend_down = df1h["Close"].iloc[-1]<ema1h and df1d["Close"].iloc[-1]<ema1d

     # REGOLA 2: BOLLINGER AL CONTRARIO
     sma20=df5["Close"].rolling(20).mean().iloc[-1]
     std20=df5["Close"].rolling(20).std().iloc[-1]
     upper=sma20+2*std20
     lower=sma20-2*std20
     bb_upper_hit = c5>=upper*0.998
     bb_lower_hit = c5<=lower*1.002

     # REGOLA 3: WICK TRAP AL CONTRARIO
     o=float(df5["Open"].iloc[-1]); h=float(df5["High"].iloc[-1]); l=float(df5["Low"].iloc[-1])
     body=abs(c5-o); rng=h-l if h!=l else 0.00001
     upper_wick=h-max(c5,o); lower_wick=min(c5,o)-l
     wick_up = upper_wick > rng*0.6
     wick_down = lower_wick > rng*0.6

     # LOGICA FINALE TUTTO PER PERDERE
     if bb_upper_hit or wick_up or trend_up:
      sig="BUY" # tocca banda alta, wick su, trend up = compriamo al top = LOSS
     elif bb_lower_hit or wick_down or trend_down:
      sig="SELL" # tocca banda bassa, wick giu, trend down = vendiamo al bottom = LOSS
     else:
      sig="SELL" if trend_up else "BUY" # sempre contro il trend grande

     PEND[pair]=(sig,c5,now)
     send(f"💀 *5M {sig} {pair.replace('=X','')}*\nBB:{'UP' if bb_upper_hit else 'LOW' if bb_lower_hit else 'MID'} Wick:{'UP' if wick_up else 'DOWN' if wick_down else 'NO'}\n1H+1D:{'UP' if trend_up else 'DOWN'}\nPrice {c5:.5f} -> 0% WIN")
    except:pass
 except:pass
 time.sleep(3)
