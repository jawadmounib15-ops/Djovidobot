import os, time, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V-MEDIO"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","CHFJPY=X","EURCAD=X","EURNZD=X"]
PAIRS_REAL = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","EUR/JPY","GBP/JPY","USD/CHF","EUR/GBP","AUD/JPY","CHF/JPY","EUR/CAD","EUR/NZD"]
PAIRS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","CHF/JPY-OTC","EUR/CAD-OTC","EUR/NZD-OTC"]

LAST={}; CHECK=0; LAST_SIGNAL=0

def is_otc():
    now = datetime.utcnow()
    return now.weekday()>=5 or now.hour<7 or now.hour>21

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    ag=g.ewm(alpha=1/p).mean(); al=l.ewm(alpha=1/p).mean()
    return 100-(100/(1+ag/al))

def bot():
    global CHECK, LAST_SIGNAL
    send("⚖️ *V-MEDIO ONLINE*\nMedio - non troppo stretto non troppo largo\n5min tra segnali")
    while True:
        try:
            now=datetime.now()
            otc = is_otc()
            MERCATO = "OTC" if otc else "REALI"
            LABELS = PAIRS_OTC if otc else PAIRS_REAL
            if time.time()-CHECK >= 15:
                CHECK=time.time()
                if time.time() - LAST_SIGNAL < 300: continue

                for yahoo,label in zip(SYMBOLS,LABELS):
                    if yahoo in LAST and time.time()-LAST[yahoo]<300: continue
                    try:
                        df=yf.download(yahoo,period="10d",interval="5m",progress=False)
                        if len(df)<80: continue
                        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                        df["RSI"]=rsi(df["Close"]); df["EMA20"]=df["Close"].ewm(span=20).mean(); df["EMA50"]=df["Close"].ewm(span=50).mean(); df["EMA200"]=df["Close"].ewm(span=200).mean()

                        o=float(df["Open"].iloc[-2]); h=float(df["High"].iloc[-2]); l=float(df["Low"].iloc[-2]); c=float(df["Close"].iloc[-2])
                        o2=float(df["Open"].iloc[-3]); c2=float(df["Close"].iloc[-3])
                        r=float(df["RSI"].iloc[-2]); ema20=float(df["EMA20"].iloc[-2]); ema50=float(df["EMA50"].iloc[-2]); ema200=float(df["EMA200"].iloc[-2])

                        total=h-l
                        if total==0: continue
                        body=abs(o-c); body_pct=(body/total)*100; wl=((min(o,c)-l)/total)*100; wh=((h-max(o,c))/total)*100

                        cur=now.strftime("%H:%M:%S"); exp5=(now+timedelta(minutes=5)).strftime("%H:%M:%S")

                        # MEDIO - PINBAR
                        if body_pct<=45 and wl>=55 and wl>=body*2.5/total*100 and ema20>ema50 and 30<=r<=55 and l<=ema20*1.001:
                            LAST[yahoo]=time.time(); LAST_SIGNAL=time.time()
                            send(f"📌 *PINBAR BUY {label}*\nBody {body_pct:.0f}% Wick {wl:.0f}% RSI {r:.0f}\n⏰ {cur}→{exp5} {MERCATO} {c:.5f} 👉 BUY")
                            break
                        if body_pct<=45 and wh>=55 and wh>=body*2.5/total*100 and ema20<ema50 and 45<=r<=70 and h>=ema20*0.999:
                            LAST[yahoo]=time.time(); LAST_SIGNAL=time.time()
                            send(f"📌 *PINBAR SELL {label}*\nBody {body_pct:.0f}% Wick {wh:.0f}% RSI {r:.0f}\n⏰ {cur}→{exp5} {MERCATO} {c:.5f} 👉 SELL")
                            break
                        # MEDIO - TREND
                        if c>ema20 and ema20>ema50 and 45<=r<=65:
                            LAST[yahoo]=time.time(); LAST_SIGNAL=time.time()
                            send(f"📈 *TREND BUY {label}*\nEMA UP RSI {r:.0f}\n⏰ {cur}→{exp5} {MERCATO} {c:.5f} 👉 BUY")
                            break
                        if c<ema20 and ema20<ema50 and 35<=r<=55:
                            LAST[yahoo]=time.time(); LAST_SIGNAL=time.time()
                            send(f"📉 *TREND SELL {label}*\nEMA DOWN RSI {r:.0f}\n⏰ {cur}→{exp5} {MERCATO} {c:.5f} 👉 SELL")
                            break
                        # MEDIO - ENGULFING
                        if c2<o2 and c>o and c>o2 and body>=abs(c2-o2)*0.6 and r<55:
                            LAST[yahoo]=time.time(); LAST_SIGNAL=time.time()
                            send(f"🔥 *ENGULFING BUY {label}*\n⏰ {cur}→{exp5} {MERCATO} {c:.5f} 👉 BUY")
                            break
                        if c2>o2 and c<o and c<o2 and body>=abs(c2-o2)*0.6 and r>45:
                            LAST[yahoo]=time.time(); LAST_SIGNAL=time.time()
                            send(f"🔥 *ENGULFING SELL {label}*\n⏰ {cur}→{exp5} {MERCATO} {c:.5f} 👉 SELL")
                            break
                    except: pass
        except: pass
        time.sleep(1)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
