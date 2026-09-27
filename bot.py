# bot.py - V-OTC 3MIN ONLY - REALI+OTC FIX
import os, time, random, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask

app = Flask(__name__)
@app.route('/')
def home():
    return "V-OTC 3MIN ONLINE - Solo OTC - Scadenza 3 minuti"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","CHFJPY=X","EURCAD=X","EURNZD=X"]
PAIRS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","CHF/JPY-OTC","EUR/CAD-OTC","EUR/NZD-OTC"]

LAST={}; CHECK=0; LAST_SIGNAL=0; LAST_PRICE={}

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except:
        pass

def bot_loop():
    global CHECK, LAST_SIGNAL
    send("🎯 *V-OTC 3MIN ONLY ONLINE*\nSolo OTC - Scadenza 3 MIN")
    while True:
        try:
            now=datetime.now()
            if time.time()-CHECK >= 10:
                CHECK=time.time()
                if time.time() - LAST_SIGNAL < 180:
                    continue

                combined = list(zip(SYMBOLS, PAIRS_OTC))
                random.shuffle(combined)

                for yahoo,label in combined:
                    if yahoo in LAST and time.time()-LAST[yahoo]<300:
                        continue
                    try:
                        df=yf.download(yahoo, period="1d", interval="1m", progress=False)
                        if len(df)<80:
                            continue
                        if isinstance(df.columns,pd.MultiIndex):
                            df.columns=df.columns.get_level_values(0)

                        df['EMA9']=df['Close'].ewm(span=9).mean()
                        df['EMA21']=df['Close'].ewm(span=21).mean()
                        df['EMA50']=df['Close'].ewm(span=50).mean()
                        delta=df['Close'].diff()
                        gain=delta.where(delta>0,0).ewm(alpha=1/14).mean()
                        loss=-delta.where(delta<0,0).ewm(alpha=1/14).mean()
                        rs=gain/loss
                        df['RSI']=100-(100/(1+rs))

                        last=df.iloc[-2]; prev=df.iloc[-3]
                        c=float(last['Close']); r=float(last['RSI'])
                        ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50'])

                        if yahoo in LAST_PRICE and abs(c-LAST_PRICE[yahoo])<0.00001:
                            continue
                        if abs(ema9-ema21)/c < 0.00015:
                            continue

                        cur=now.strftime("%H:%M:%S")
                        exp3=(now+timedelta(minutes=3)).strftime("%H:%M:%S")

                        signal=None
                        if prev['EMA9']<prev['EMA21'] and ema9>ema21 and c>ema50 and 48<r<68:
                            signal=f"🟢 *BUY {label} 3MIN*\nEMA9x21 UP RSI {r:.0f} > EMA50✅\n⏰ {cur}→{exp3} (3 MIN)\n💰 {c:.5f} 👉 *BUY*"
                        elif prev['EMA9']>prev['EMA21'] and ema9<ema21 and c<ema50 and 32<r<52:
                            signal=f"🔴 *SELL {label} 3MIN*\nEMA9x21 DOWN RSI {r:.0f} < EMA50✅\n⏰ {cur}→{exp3} (3 MIN)\n💰 {c:.5f} 👉 *SELL*"
                        elif c>ema9 and ema9>ema21 and ema21>ema50 and 50<=r<=67:
                            signal=f"📈 *TREND BUY {label} 3MIN*\nEMA 9>21>50 RSI {r:.0f}\n⏰ {cur}→{exp3} {c:.5f} 👉 BUY"
                        elif c<ema9 and ema9<ema21 and ema21<ema50 and 33<=r<=50:
                            signal=f"📉 *TREND SELL {label} 3MIN*\nEMA 9<21<50 RSI {r:.0f}\n⏰ {cur}→{exp3} {c:.5f} 👉 SELL"

                        if signal:
                            send(signal)
                            LAST[yahoo]=time.time()
                            LAST_SIGNAL=time.time()
                            LAST_PRICE[yahoo]=c
                            break
                    except Exception as e:
                        print(f"Err {label}: {e}")
                        pass
        except Exception as e:
            print(f"Loop err: {e}")
            pass
        time.sleep(1)

threading.Thread(target=bot_loop,daemon=True).start()

if __name__=="__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
