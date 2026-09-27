import os, time, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V200 PINBAR + L15 FALLBACK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","CHFJPY=X","EURCAD=X","EURNZD=X"]
PAIRS_REAL = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","EUR/JPY","GBP/JPY","USD/CHF","EUR/GBP","AUD/JPY","CHF/JPY","EUR/CAD","EUR/NZD"]
PAIRS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","CHF/JPY-OTC","EUR/CAD-OTC","EUR/NZD-OTC"]

LAST={}; CHECK=0; LAST_PINBAR=0

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
    global CHECK, LAST_PINBAR
    send("🎯 *V200 PINBAR + L15 FALLBACK ONLINE*\n1. Cerca PINBAR 80%\n2. Se 2h senza → L15 TREND 70%")
    while True:
        try:
            now=datetime.now()
            otc = is_otc()
            MERCATO = "OTC" if otc else "REALI"
            LABELS = PAIRS_OTC if otc else PAIRS_REAL

            if time.time()-CHECK >= 30:
                CHECK=time.time()
                for yahoo,label in zip(SYMBOLS,LABELS):
                    if yahoo in LAST and time.time()-LAST[yahoo]<3600: continue
                    try:
                        df=yf.download(yahoo,period="10d",interval="5m",progress=False)
                        if len(df)<100: continue
                        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                        df["RSI"]=rsi(df["Close"]); df["EMA20"]=df["Close"].ewm(span=20).mean(); df["EMA50"]=df["Close"].ewm(span=50).mean(); df["EMA200"]=df["Close"].ewm(span=200).mean()
                        df["RANGE"]=df["High"]-df["Low"]; df["AVG"]=df["RANGE"].rolling(20).mean()
                        df5=df; df15=df.resample('15min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                        df15["RSI"]=rsi(df15["Close"]); df15["EMA20"]=df15["Close"].ewm(span=20).mean(); df15["EMA50"]=df15["Close"].ewm(span=50).mean()

                        o=float(df["Open"].iloc[-2]); h=float(df["High"].iloc[-2]); l=float(df["Low"].iloc[-2]); c=float(df["Close"].iloc[-2])
                        o2=float(df["Open"].iloc[-3]); c2=float(df["Close"].iloc[-3])
                        r=float(df["RSI"].iloc[-2]); ema20=float(df["EMA20"].iloc[-2]); ema50=float(df["EMA50"].iloc[-2]); ema200=float(df["EMA200"].iloc[-2])
                        rng=float(df["RANGE"].iloc[-2]); avg=float(df["AVG"].iloc[-2])

                        r15=float(df15["RSI"].iloc[-2]) if len(df15)>=2 else r
                        e20_15=float(df15["EMA20"].iloc[-2]) if len(df15)>=2 else ema20
                        e50_15=float(df15["EMA50"].iloc[-2]) if len(df15)>=2 else ema50

                        total=h-l
                        if total==0: continue
                        body=abs(o-c); body_pct=(body/total)*100; wl=((min(o,c)-l)/total)*100; wh=((h-max(o,c))/total)*100; lw=max(wl,wh)

                        cur=now.strftime("%H:%M:%S"); exp5=(now+timedelta(minutes=5)).strftime("%H:%M:%S"); exp15=(now+timedelta(minutes=15)).strftime("%H:%M:%S")

                        # ===== 1. PINBAR CORRETTA 80% =====
                        f1=body_pct<=34; f2=lw>=66; f3=(lw/100*total)>=body*4 if body>0 else False; f4=body_pct>=2; f5=rng>=avg*0.9
                        f_buy_pin = f1 and f2 and f3 and f4 and f5 and ema20>ema50 and c>ema200 and 28<=r<=45 and l<=ema20*1.0005 and wl==lw
                        f_sell_pin = f1 and f2 and f3 and f4 and f5 and ema20<ema50 and c<ema200 and 55<=r<=72 and h>=ema20*0.9995 and wh==lw

                        if f_buy_pin:
                            LAST[yahoo]=time.time(); LAST_PINBAR=time.time()
                            send(f"🎯 *PINBAR CORRETTA BUY {label} 80%*\n📊 Body {body_pct:.1f}% Wick {wl:.1f}% 4x✅\nRSI {r:.0f} Trend UP✅ EMA20 {ema20:.5f}\n⏰ {cur}→{exp5} (5 MIN) {MERCATO}\n💰 {c:.5f} 👉 *BUY*")
                            continue
                        if f_sell_pin:
                            LAST[yahoo]=time.time(); LAST_PINBAR=time.time()
                            send(f"🎯 *PINBAR CORRETTA SELL {label} 80%*\n📊 Body {body_pct:.1f}% Wick {wh:.1f}% 4x✅\nRSI {r:.0f} Trend DOWN✅ EMA20 {ema20:.5f}\n⏰ {cur}→{exp5} (5 MIN) {MERCATO}\n💰 {c:.5f} 👉 *SELL*")
                            continue

                        # ===== 2. FALLBACK L15 SE 2 ORE SENZA PINBAR =====
                        no_pinbar_2h = time.time() - LAST_PINBAR > 7200
                        if no_pinbar_2h:
                            # L15 TREND 15MIN
                            if c>e20_15 and e20_15>e50_15 and 50<=r15<=68:
                                LAST[yahoo]=time.time()
                                send(f"📈 *L15 (15MIN) BUY {label} FALLBACK 70%*\nPinbar non trovata 2h → uso trend\nRSI15 {r15:.0f} EMA20>{e50_15:.5f}✅\n⏰ {cur}→{exp15} {MERCATO}\n💰 {c:.5f} 👉 *BUY*")
                            elif c<e20_15 and e20_15<e50_15 and 32<=r15<=50:
                                LAST[yahoo]=time.time()
                                send(f"📈 *L15 (15MIN) SELL {label} FALLBACK 70%*\nPinbar non trovata 2h → uso trend\nRSI15 {r15:.0f} EMA20<{e50_15:.5f}✅\n⏰ {cur}→{exp15} {MERCATO}\n💰 {c:.5f} 👉 *SELL*")
                            # ENGULFING 5MIN
                            elif c2<o2 and c>o and c>o2 and r<48:
                                LAST[yahoo]=time.time()
                                send(f"🔥 *ENGULFING BUY {label} FALLBACK 68%*\nPinbar non trovata → engulfing\n⏰ {cur}→{exp5} {MERCATO} {c:.5f} 👉 BUY")
                            elif c2>o2 and c<o and c<o2 and r>52:
                                LAST[yahoo]=time.time()
                                send(f"🔥 *ENGULFING SELL {label} FALLBACK 68%*\nPinbar non trovata → engulfing\n⏰ {cur}→{exp5} {MERCATO} {c:.5f} 👉 SELL")

                    except Exception as e:
                        print(e); pass
        except: pass
        time.sleep(1)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
