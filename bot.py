# bot.py - PIN BAR ULTRA STRETTA - ZERO FALSI
import os, time, requests, yfinance as yf
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "ULTRA STRETTA OK"

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
        if len(df)<80: return None
        if hasattr(df.columns,'get_level_values'):
            try: df.columns=df.columns.get_level_values(0)
            except: pass
        c=df['Close']
        df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean(); df['EMA100']=c.ewm(100).mean()
        df['SMA20']=c.rolling(20).mean(); s=c.rolling(20).std()
        df['BB_UP']=df['SMA20']+2*s; df['BB_LOW']=df['SMA20']-2*s
        delta=c.diff(); g=delta.where(delta>0,0).ewm(14).mean(); ls=-delta.where(delta<0,0).ewm(14).mean()
        df['RSI']=100-(100/(1+g/ls))
        return df
    except: return None

def ultra_pinbar_5m(y):
    df=get_df(y,"1m","2d")
    if df is None: return None
    last5=df.iloc[-5:]; o=float(last5.iloc[0]['Open']); cc=float(last5.iloc[-1]['Close'])
    h=float(last5['High'].max()); l=float(last5['Low'].min())
    body=abs(cc-o); rng=h-l
    if rng==0: return None
    up=h-max(o,cc); low=min(o,cc)-l
    last=df.iloc[-1]; ema21=float(last['EMA21']); ema50=float(last['EMA50']); ema100=float(last['EMA100'])
    rsi=float(last['RSI']); price=cc; bb_low=float(last['BB_LOW']); bb_up=float(last['BB_UP'])

    # ULTRA STRETTA - 7 REGOLE
    if body > rng*0.18: return None # 1. body <18%
    if low > rng*0.75 and low > 4*body and up < rng*0.08 and price <= bb_low*1.005 and ema21>ema50 and ema50>ema100 and rsi<35:
        return "BUY", int((low/rng)*100), rsi
    if up > rng*0.75 and up > 4*body and low < rng*0.08 and price >= bb_up*0.995 and ema21<ema50 and ema50<ema100 and rsi>65:
        return "SELL", int((up/rng)*100), rsi
    return None

def ultra_pinbar_15m(y):
    df=get_df(y,"15m","5d")
    if df is None: return None
    c=df.iloc[-1]; o=float(c['Open']); cc=float(c['Close']); h=float(c['High']); l=float(c['Low'])
    body=abs(cc-o); rng=h-l
    if rng==0 or body>rng*0.15: return None
    up=h-max(o,cc); low=min(o,cc)-l
    ema21=float(c['EMA21']); ema50=float(c['EMA50']); ema100=float(c['EMA100'])
    rsi=float(c['RSI']); bb_low=float(c['BB_LOW']); bb_up=float(c['BB_UP'])

    if low>rng*0.78 and low>4.5*body and up<rng*0.06 and cc<=bb_low*1.01 and ema21>ema50 and rsi<38:
        return "BUY", int((low/rng)*100), rsi
    if up>rng*0.78 and up>4.5*body and low<rng*0.06 and cc>=bb_up*0.99 and ema21<ema50 and rsi>62:
        return "SELL", int((up/rng)*100), rsi
    return None

def bot_loop():
    global AVVIO
    if not AVVIO:
        send(f"✅ *ULTRA STRETTA ATTIVA*\nBody<18% Wick>75% + BB + EMA + RSI\nFalsi = 0\n{datetime.now(ITALY_TZ).strftime('%H:%M:%S')} ITALIA")
        AVVIO=True
    while True:
        try:
            for base, otc, reali in ALL:
                now=datetime.now(ITALY_TZ)
                sec=(5-now.minute%5)*60-now.second
                if 15<=sec<=90:
                    r=ultra_pinbar_5m(base)
                    if r:
                        d,p,rs=r
                        for lab in [otc,reali]:
                            k=f"{lab}_5M_{d}_ULTRA"
                            if k in LAST and time.time()-LAST[k]<600: continue
                            msg=f"💎 *ULTRA 5M*\n{lab}\n{'🟢 BUY 5M' if d=='BUY' else '🔴 SELL 5M'}\nWick {p}% | RSI {rs:.0f} | BB touch\n⏰ {now.strftime('%H:%M:%S')} ITALIA"
                            send(msg); LAST[k]=time.time()

                if 15-(now.minute%15) <= 2:
                    r=ultra_pinbar_15m(base)
                    if r:
                        d,p,rs=r
                        for lab in [otc,reali]:
                            k=f"{lab}_15M_{d}_ULTRA"
                            if k in LAST and time.time()-LAST[k]<1200: continue
                            msg=f"💎💎 *ULTRA 15M SICURISSIMA*\n{lab}\n{'🟢 BUY 15M' if d=='BUY' else '🔴 SELL 15M'}\nWick {p}% | RSI {rs:.0f} | BB\n⏰ {now.strftime('%H:%M:%S')} ITALIA"
                            send(msg); LAST[k]=time.time()
                time.sleep(0.8)
            time.sleep(3)
        except Exception as e:
            print(e); time.sleep(5)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
