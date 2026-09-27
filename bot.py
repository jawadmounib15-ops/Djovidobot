# bot.py - 3 LAVORI: 1 MSG AVVIO SOLO
import os, time, random, requests, yfinance as yf, threading, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "3 LAVORI - 1 MSG AVVIO"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

BASE = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","CHFJPY=X","EURCAD=X","EURNZD=X"]
LABELS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","CHF/JPY-OTC","EUR/CAD-OTC","EUR/NZD-OTC"]
LABELS_REALI = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","EUR/JPY","GBP/JPY","USD/CHF","EUR/GBP","AUD/JPY","CHF/JPY","EUR/CAD","EUR/NZD"]
ALL_PAIRS = [(b,r,o) for b,r,o in zip(BASE, LABELS_REALI, LABELS_OTC)]

LAST_PIN={}; LAST_OTC={}; LAST_REALI={}

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def get_df(yahoo, tipo):
    intervals = [("1m","2d"),("5m","5d")] if tipo!="REALI30" else [("30m","1mo"),("1h","2mo"),("15m","5d")]
    for interval, period in intervals:
        try:
            df=yf.download(yahoo, period=period, interval=interval, progress=False, auto_adjust=False)
            if len(df)>=80:
                if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                return df.dropna(), interval
        except: pass
    return None, None

def is_pinbar_migliore(o,h,l,c):
    body=abs(c-o); total=h-l
    if total==0: return None
    ratio=body/total
    if ratio>0.30 or ratio<0.04: return None
    up=h-max(o,c); low=min(o,c)-l
    if low>body*2.5 and low>total*0.60 and up<body*0.6: return "BULL"
    if up>body*2.5 and up>total*0.60 and low<body*0.6: return "BEAR"
    return None

def lavoro_1_pinbar():
    while True:
        try:
            now=datetime.now(); wk=now.weekday()>=5
            for yahoo,reale,otc in ALL_PAIRS:
                for label in ([otc,reale] if not wk else [otc]):
                    key=f"PIN_{yahoo}_{label}"
                    if key in LAST_PIN and time.time()-LAST_PIN[key]<300: continue
                    df,tf=get_df(yahoo,"PIN")
                    if df is None: continue
                    try:
                        df['EMA21']=df['Close'].ewm(21).mean(); df['EMA50']=df['Close'].ewm(50).mean(); df['ATR']=(df['High']-df['Low']).ewm(14).mean()
                        delta=df['Close'].diff(); g=delta.where(delta>0,0).ewm(alpha=1/14).mean(); l=-delta.where(delta<0,0).ewm(alpha=1/14).mean()
                        df['RSI']=100-(100/(1+g/l))
                        last=df.iloc[-1]; o=float(last['Open']); h=float(last['High']); lo=float(last['Low']); c=float(last['Close']); r=float(last['RSI'])
                        ema21=float(last['EMA21']); ema50=float(last['EMA50']); atr=float(last['ATR'])
                        if atr/c<0.00055: continue
                        pin=is_pinbar_migliore(o,h,lo,c)
                        if not pin: continue
                        if abs(c-ema21)/c>0.0015 and abs(c-ema50)/c>0.0015: continue
                        cur=now.strftime("%H:%M:%S"); exp=(now+timedelta(minutes=5)).strftime("%H:%M:%S")
                        if pin=="BULL" and 30<=r<=48:
                            send(f"📌🟢 *PINBAR BUY {label} 5M*\nMigliore 80% RSI {r:.0f} [{tf}]\n⏰ {cur}→{exp} {c:.5f} 👉 BUY")
                            LAST_PIN[key]=time.time()
                        elif pin=="BEAR" and 52<=r<=70:
                            send(f"📌🔴 *PINBAR SELL {label} 5M*\nMigliore 80% RSI {r:.0f} [{tf}]\n⏰ {cur}→{exp} {c:.5f} 👉 SELL")
                            LAST_PIN[key]=time.time()
                    except: continue
            time.sleep(15)
        except: time.sleep(3)

def lavoro_2_otc():
    while True:
        try:
            now=datetime.now()
            for yahoo,reale,otc in ALL_PAIRS:
                key=f"OTC_{yahoo}"
                if key in LAST_OTC and time.time()-LAST_OTC[key]<180: continue
                df,tf=get_df(yahoo,"OTC")
                if df is None: continue
                try:
                    df['EMA9']=df['Close'].ewm(9).mean(); df['EMA21']=df['Close'].ewm(21).mean(); df['EMA50']=df['Close'].ewm(50).mean()
                    delta=df['Close'].diff(); g=delta.where(delta>0,0).ewm(alpha=1/14).mean(); l=-delta.where(delta<0,0).ewm(alpha=1/14).mean()
                    df['RSI']=100-(100/(1+g/l)); df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean(); df['SIG']=df['MACD'].ewm(9).mean(); df['ATR']=(df['High']-df['Low']).ewm(14).mean()
                    last=df.iloc[-1]; c=float(last['Close']); r=float(last['RSI']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50']); macd=float(last['MACD']); sig=float(last['SIG']); atr=float(last['ATR'])
                    if atr/c<0.00045 or abs(ema9-ema21)/c<0.00012: continue
                    up=ema9>ema21 and ema21>ema50 and c>ema21; down=ema9<ema21 and ema21<ema50 and c<ema21
                    cur=now.strftime("%H:%M:%S"); exp=(now+timedelta(minutes=3)).strftime("%H:%M:%S")
                    if up and macd>sig and 50<=r<=66:
                        send(f"⚡🟢 *OTC 3MIN BUY {otc}*\n9>21>50 RSI {r:.0f} [{tf}]\n⏰ {cur}→{exp} {c:.5f} 👉 BUY 3M"); LAST_OTC[key]=time.time(); break
                    elif down and macd<sig and 34<=r<=50:
                        send(f"⚡🔴 *OTC 3MIN SELL {otc}*\n9<21<50 RSI {r:.0f} [{tf}]\n⏰ {cur}→{exp} {c:.5f} 👉 SELL 3M"); LAST_OTC[key]=time.time(); break
                except: continue
            time.sleep(10)
        except: time.sleep(3)

def lavoro_3_reali():
    while True:
        try:
            now=datetime.now()
            if now.weekday()>=5: time.sleep(60); continue
            for yahoo,reale,otc in ALL_PAIRS:
                key=f"REALI_{yahoo}"
                if key in LAST_REALI and time.time()-LAST_REALI[key]<1800: continue
                df,tf=get_df(yahoo,"REALI30")
                if df is None: continue
                try:
                    df['EMA9']=df['Close'].ewm(9).mean(); df['EMA21']=df['Close'].ewm(21).mean(); df['EMA50']=df['Close'].ewm(50).mean(); df['EMA100']=df['Close'].ewm(100).mean()
                    delta=df['Close'].diff(); g=delta.where(delta>0,0).ewm(alpha=1/14).mean(); l=-delta.where(delta<0,0).ewm(alpha=1/14).mean()
                    df['RSI']=100-(100/(1+g/l)); df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean(); df['SIG']=df['MACD'].ewm(9).mean(); df['ATR']=(df['High']-df['Low']).ewm(14).mean()
                    last=df.iloc[-1]; c=float(last['Close']); r=float(last['RSI']); ema9=float(last['EMA9']); ema21=float(last['EMA21']); ema50=float(last['EMA50']); ema100=float(last['EMA100']); macd=float(last['MACD']); sig=float(last['SIG']); atr=float(last['ATR'])
                    if atr/c<0.0008 or abs(ema9-ema21)/c<0.00030: continue
                    up=ema9>ema21 and ema21>ema50 and ema50>ema100 and c>ema9; down=ema9<ema21 and ema21<ema50 and ema50<ema100 and c<ema9
                    cur=now.strftime("%H:%M:%S"); exp=(now+timedelta(minutes=30)).strftime("%H:%M:%S")
                    if up and macd>sig and 55<=r<=65:
                        send(f"🏦🟢 *REALI 30MIN BUY {reale}*\n9>21>50>100 RSI {r:.0f} [{tf}]\n⏰ {cur}→{exp} {c:.5f} 👉 BUY 30M"); LAST_REALI[key]=time.time(); break
                    elif down and macd<sig and 35<=r<=45:
                        send(f"🏦🔴 *REALI 30MIN SELL {reale}*\n9<21<50<100 RSI {r:.0f} [{tf}]\n⏰ {cur}→{exp} {c:.5f} 👉 SELL 30M"); LAST_REALI[key]=time.time(); break
                except: continue
            time.sleep(30)
        except: time.sleep(5)

threading.Thread(target=lavoro_1_pinbar,daemon=True).start()
threading.Thread(target=lavoro_2_otc,daemon=True).start()
threading.Thread(target=lavoro_3_reali,daemon=True).start()

# UNICO MESSAGGIO AVVIO
send("💎 *BOT 3 LAVORI ONLINE*\n📌 PINBAR 80% 5M\n⚡ OTC 3M\n🏦 REALI 30M")

app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
