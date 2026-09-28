# bot.py - 3 LAVORI PULITI: 1 MSG AVVIO SOLO - ORARIO ITALIA
import os, time, random, requests, yfinance as yf
from datetime import datetime, timedelta, timezone
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "3 LAVORI - 1 MSG AVVIO - ITALIA OK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")
ITALY_TZ = timezone(timedelta(hours=2))

BASE = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","USDCHF=X"]
LABELS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","USD/CAD-OTC","EUR/JPY-OTC","USD/CHF-OTC"]
LABELS_REALI = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD","EUR/JPY","USD/CHF"]
ALL_PAIRS = [(b,r,o) for b,r,o in zip(BASE, LABELS_REALI, LABELS_OTC)]

LAST_PIN={}; LAST_OTC={}; LAST_REALI={}
AVVIO_INVIATO=False

def send(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_df(y,interval="1m"):
    try:
        df=yf.download(y,period="2d",interval=interval,progress=False,auto_adjust=False)
        if len(df)<60: return None
        if hasattr(df.columns,'get_level_values'):
            try: df.columns=df.columns.get_level_values(0)
            except: pass
        c=df['Close']
        df['EMA9']=c.ewm(9).mean();df['EMA21']=c.ewm(21).mean();df['EMA50']=c.ewm(50).mean();df['EMA100']=c.ewm(100).mean()
        d=c.diff();g=d.where(d>0,0).ewm(14).mean();ls=-d.where(d<0,0).ewm(14).mean()
        df['RSI']=100-(100/(1+g/ls))
        df['SMA20']=c.rolling(20).mean();s=c.rolling(20).std()
        df['BB_UP']=df['SMA20']+2*s;df['BB_LOW']=df['SMA20']-2*s
        df['K']=(c-df['Low'].rolling(14).min())/(df['High'].rolling(14).max()-df['Low'].rolling(14).min()+0.00001)*100
        return df
    except: return None

def check_pinbar(y,lab):
    df=get_df(y,"1m")
    if df is None: return None
    now=datetime.now(ITALY_TZ);sec=(5-now.minute%5)*60-now.second
    if not 25<=sec<=110: return None
    last5=df.iloc[-5:];o=float(last5.iloc[0]['Open']);cc=float(last5.iloc[-1]['Close']);hh=float(last5['High'].max());ll=float(last5['Low'].min())
    body=abs(cc-o);rng=hh-ll
    if rng==0: return None
    up=hh-max(o,cc);low=min(o,cc)-ll;rsi=float(df['RSI'].iloc[-1]);ema21=float(df['EMA21'].iloc[-1]);ema50=float(df['EMA50'].iloc[-1])
    bull=low>1.9*body and low>rng*0.58 and cc>o and rsi<40 and ema21>ema50
    bear=up>1.9*body and up>rng*0.58 and cc<o and rsi>60 and ema21<ema50
    if bull: return f"📌 *PIN BAR 1 MIN PRIMA* 📌\n{lab}\n🟢 BUY 5M\nRSI {rsi:.0f} | {sec}s | {now.strftime('%H:%M:%S')} ITALIA"
    if bear: return f"📌 *PIN BAR 1 MIN PRIMA* 📌\n{lab}\n🔴 SELL 5M\nRSI {rsi:.0f} | {sec}s | {now.strftime('%H:%M:%S')} ITALIA"
    return None

def check_otc(y,lab):
    df=get_df(y,"5m")
    if df is None: return None
    l=df.iloc[-1];ema9=float(l['EMA9']);ema21=float(l['EMA21']);ema50=float(l['EMA50']);rsi=float(l['RSI']);price=float(l['Close']);k=float(l['K'])
    score=sum([ema9<ema21<ema50,32<=rsi<=60,price<float(l['BB_UP'])*0.99,k<70,float(l['Close'])<float(l['Open'])])
    if score>=4 and ema9<ema21<ema50:
        now=datetime.now(ITALY_TZ);exp=(now+timedelta(minutes=3)).strftime("%H:%M:%S")
        return f"💎 *OTC 3MIN SELL*\n{lab}\n9<21<50 RSI {rsi:.0f} 1m\n⏰ {now.strftime('%H:%M:%S')}→{exp} ITALIA"
    score2=sum([ema9>ema21>ema50,40<=rsi<=68,price>float(l['BB_LOW'])*1.01,k>30,float(l['Close'])>float(l['Open'])])
    if score2>=4 and ema9>ema21>ema50:
        now=datetime.now(ITALY_TZ);exp=(now+timedelta(minutes=3)).strftime("%H:%M:%S")
        return f"💎 *OTC 3MIN BUY*\n{lab}\n9>21>50 RSI {rsi:.0f} 1m\n⏰ {now.strftime('%H:%M:%S')}→{exp} ITALIA"
    return None

def check_reali(y,lab):
    df=get_df(y,"5m")
    if df is None: return None
    l=df.iloc[-1];ema9=float(l['EMA9']);ema21=float(l['EMA21']);ema50=float(l['EMA50']);ema100=float(l['EMA100']);rsi=float(l['RSI'])
    now=datetime.now(ITALY_TZ);entry=now.strftime("%H:%M:%S");expiry=(now+timedelta(minutes=30)).strftime("%H:%M:%S")
    if ema9>ema21>ema50 and ema50>ema100 and 50<=rsi<=70:
        return f"💎 *REALI 30MIN BUY*\n{lab}\n9>21>50>100 RSI {rsi:.0f}\n⏰ {entry}→{expiry} ITALIA"
    if ema9<ema21<ema50 and 30<=rsi<=58:
        return f"💎 *REALI 30MIN SELL*\n{lab}\n9<21<50 RSI {rsi:.0f}\n⏰ {entry}→{expiry} ITALIA"
    return None

def bot_loop():
    global AVVIO_INVIATO
    if not AVVIO_INVIATO:
        send(f"✅ *BOT 3 LAVORI AVVIATO*\nOrario: {datetime.now(ITALY_TZ).strftime('%H:%M:%S')} ITALIA\n1 msg solo")
        AVVIO_INVIATO=True
    while True:
        try:
            for base,reali,otc in ALL_PAIRS:
                # LAVORO 1 PIN
                m=check_pinbar(base,reali)
                if m and (reali not in LAST_PIN or time.time()-LAST_PIN[reali]>300):
                    send(m);LAST_PIN[reali]=time.time()
                # LAVORO 2 OTC
                m=check_otc(base,otc)
                if m and (otc not in LAST_OTC or time.time()-LAST_OTC[otc]>300):
                    send(m);LAST_OTC[otc]=time.time()
                # LAVORO 3 REALI 30M
                m=check_reali(base,reali)
                if m and (reali not in LAST_REALI or time.time()-LAST_REALI[reali]>600):
                    send(m);LAST_REALI[reali]=time.time()
                time.sleep(1)
            time.sleep(4)
        except Exception as e:
            print(e);time.sleep(5)

threading.Thread(target=bot_loop,daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
