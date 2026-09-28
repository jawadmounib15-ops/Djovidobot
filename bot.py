# bot.py - PIN BAR GIUSTA - 5-8 SEGNALI AL GIORNO BUONI
import os, time, requests, yfinance as yf
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "PIN BAR GIUSTA OK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")
ITALY_TZ = timezone(timedelta(hours=2))

BASE = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","USDCHF=X"]
LABELS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","USD/CAD-OTC","EUR/JPY-OTC","USD/CHF-OTC"]
LABELS_REALI = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD","EUR/JPY","USD/CHF"]
ALL = list(zip(BASE, LABELS_OTC, LABELS_REALI))

LAST={}; AVVIO=False

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_df(y, interval, period):
    try:
        df=yf.download(y, period=period, interval=interval, progress=False, auto_adjust=False)
        if len(df)<60: return None
        if hasattr(df.columns,'get_level_values'):
            try: df.columns=df.columns.get_level_values(0)
            except: pass
        c=df['Close']
        df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean()
        delta=c.diff(); g=delta.where(delta>0,0).ewm(14).mean(); ls=-delta.where(delta<0,0).ewm(14).mean()
        df['RSI']=100-(100/(1+g/ls))
        return df
    except: return None

def pinbar_giusta_5m(y):
    df=get_df(y,"1m","2d")
    if df is None: return None
    last5=df.iloc[-5:]; o=float(last5.iloc[0]['Open']); cc=float(last5.iloc[-1]['Close'])
    h=float(last5['High'].max()); l=float(last5['Low'].min())
    body=abs(cc-o); rng=h-l
    if rng==0: return None
    up=h-max(o,cc); low=min(o,cc)-l
    last=df.iloc[-1]; ema21=float(last['EMA21']); ema50=float(last['EMA50']); rsi=float(last['RSI'])

    # GIUSTA: non troppo larga, non troppo stretta
    if body > rng*0.25: return None # body <25%
    if up < rng*0.12 and low > rng*0.62 and low > 2.8*body:
        if cc>ema21 and ema21>ema50 and rsi<48 and rsi>28: # BUY solo in trend UP, RSI non pompato
            return "BUY", int((low/rng)*100), rsi
    if low < rng*0.12 and up > rng*0.62 and up > 2.8*body:
        if cc<ema21 and ema21<ema50 and rsi>52 and rsi<72: # SELL solo in trend DOWN
            return "SELL", int((up/rng)*100), rsi
    return None

def pinbar_giusta_15m(y):
    df=get_df(y,"15m","5d")
    if df is None: return None
    c=df.iloc[-1]; o=float(c['Open']); cc=float(c['Close']); h=float(c['High']); l=float(c['Low'])
    body=abs(cc-o); rng=h-l
    if rng==0 or body>rng*0.22: return None
    up=h-max(o,cc); low=min(o,cc)-l
    ema21=float(c['EMA21']); ema50=float(c['EMA50']); rsi=float(c['RSI'])

    if low>rng*0.65 and low>3*body and up<rng*0.12 and cc>ema21 and rsi<50:
        return "BUY", int((low/rng)*100), rsi
    if up>rng*0.65 and up>3*body and low<rng*0.12 and cc<ema21 and rsi>50:
        return "SELL", int((up/rng)*100), rsi
    return None

def bot_loop():
    global AVVIO
    if not AVVIO:
        send(f"✅ *PIN BAR GIUSTA ATTIVA*\nBody<25% Wick>62% + Trend EMA + RSI 28-72\n5-8 segnali al giorno\n{datetime.now(ITALY_TZ).strftime('%H:%M:%S')} ITALIA")
        AVVIO=True
    while True:
        try:
            for base, otc, reali in ALL:
                now=datetime.now(ITALY_TZ)
                sec=(5-now.minute%5)*60-now.second
                if 20<=sec<=100:
                    r=pinbar_giusta_5m(base)
                    if r:
                        d,p,rs=r
                        for lab in [otc,reali]:
                            k=f"{lab}_5M_{d}"
                            if k in LAST and time.time()-LAST[k]<300: continue
                            msg=f"📌 *PIN BAR 5M*\n{lab}\n{'🟢 BUY 5M' if d=='BUY' else '🔴 SELL 5M'}\nWick {p}% RSI {rs:.0f} | {sec}s\n⏰ {now.strftime('%H:%M:%S')} ITALIA"
                            send(msg); LAST[k]=time.time()

                if 15-(now.minute%15) <= 3:
                    r=pinbar_giusta_15m(base)
                    if r:
                        d,p,rs=r
                        for lab in [otc,reali]:
                            k=f"{lab}_15M_{d}"
                            if k in LAST and time.time()-LAST[k]<600: continue
                            msg=f"📌📌 *PIN BAR 15M*\n{lab}\n{'🟢 BUY 15M' if d=='BUY' else '🔴 SELL 15M'}\nWick {p}% RSI {rs:.0f}\n⏰ {now.strftime('%H:%M:%S')} ITALIA SICURA"
                            send(msg); LAST[k]=time.time()
                time.sleep(0.7)
            time.sleep(3)
        except Exception as e:
            print(e); time.sleep(5)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
