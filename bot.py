import os, time, random, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V-MEDIO MULTI FIX"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","CHFJPY=X","EURCAD=X","EURNZD=X"]
PAIRS_REAL = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","EUR/JPY","GBP/JPY","USD/CHF","EUR/GBP","AUD/JPY","CHF/JPY","EUR/CAD","EUR/NZD"]
PAIRS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","CHF/JPY-OTC","EUR/CAD-OTC","EUR/NZD-OTC"]

LAST={}; CHECK=0; LAST_SIGNAL=0; LAST_PRICE={}

def is_otc():
    now = datetime.utcnow()
    return now.weekday()>=5 or now.hour<7 or now.hour>21

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def bot():
    global CHECK, LAST_SIGNAL
    send("🔧 *V-MEDIO MULTI FIX ONLINE*\nFix: ora gira tutte le coppie\nNo più solo USD/JPY")
    while True:
        try:
            now=datetime.now()
            otc = is_otc()
            MERCATO = "OTC" if otc else "REALI"
            LABELS = PAIRS_OTC if otc else PAIRS_REAL

            if time.time()-CHECK >= 15:
                CHECK=time.time()
                if time.time() - LAST_SIGNAL < 300: continue

                # FIX 1: MISCHIA COPPIE OGNI GIRO
                combined = list(zip(SYMBOLS, LABELS))
                random.shuffle(combined)

                for yahoo,label in combined:
                    if yahoo in LAST and time.time()-LAST[yahoo]<600: continue # 10 min per coppia
                    try:
                        df=yf.download(yahoo, period="2d", interval="5m", progress=False)
                        if len(df)<60: continue
                        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)

                        df['EMA20']=df['Close'].ewm(span=20).mean()
                        df['EMA50']=df['Close'].ewm(span=50).mean()
                        delta=df['Close'].diff()
                        gain=delta.where(delta>0,0).ewm(alpha=1/14).mean()
                        loss=-delta.where(delta<0,0).ewm(alpha=1/14).mean()
                        rs=gain/loss
                        df['RSI']=100-(100/(1+rs))
                        df['MACD']=df['Close'].ewm(span=12).mean()-df['Close'].ewm(span=26).mean()
                        df['MACD_SIG']=df['MACD'].ewm(span=9).mean()

                        last=df.iloc[-2]; prev=df.iloc[-3]
                        c=float(last['Close']); r=float(last['RSI'])
                        ema20=float(last['EMA20']); ema50=float(last['EMA50'])
                        macd=float(last['MACD']); sig=float(last['MACD_SIG'])

                        # FIX 2: NO PREZZO UGUALE
                        if yahoo in LAST_PRICE and abs(c-LAST_PRICE[yahoo])<0.00001:
                            continue

                        # FIX 3: FILTRO PIU STRETTO PER NON RIPETERE USD/JPY
                        if abs(ema20-ema50)/c < 0.0009: continue

                        cur=now.strftime("%H:%M:%S"); exp5=(now+timedelta(minutes=5)).strftime("%H:%M:%S")

                        signal=None
                        if prev['EMA20']<prev['EMA50'] and last['EMA20']>last['EMA50'] and macd>sig and 45<r<68:
                            signal=f"🟢 *BUY {label} {MERCATO}*\nEMA CROSS UP RSI {r:.0f}\n⏰ {cur}→{exp5} {c:.5f} 👉 BUY"
                        elif prev['EMA20']>prev['EMA50'] and last['EMA20']<last['EMA50'] and macd<sig and 32<r<55:
                            signal=f"🔴 *SELL {label} {MERCATO}*\nEMA CROSS DOWN RSI {r:.0f}\n⏰ {cur}→{exp5} {c:.5f} 👉 SELL"
                        # TREND SE NON C'E CROSS
                        elif c>ema20 and ema20>ema50 and 50<=r<=65 and last['Close']>last['EMA20']:
                            signal=f"📈 *TREND BUY {label} {MERCATO}*\nRSI {r:.0f} EMA UP\n⏰ {cur}→{exp5} {c:.5f} 👉 BUY"
                        elif c<ema20 and ema20<ema50 and 35<=r<=50 and last['Close']<last['EMA20']:
                            signal=f"📉 *TREND SELL {label} {MERCATO}*\nRSI {r:.0f} EMA DOWN\n⏰ {cur}→{exp5} {c:.5f} 👉 SELL"

                        if signal:
                            send(signal)
                            LAST[yahoo]=time.time()
                            LAST_SIGNAL=time.time()
                            LAST_PRICE[yahoo]=c
                            break # manda 1 e poi aspetta 5 min
                    except: pass
        except: pass
        time.sleep(1)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
