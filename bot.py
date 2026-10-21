# bot.py - 60% UN SOLO MSG 60s PRE - FINALE
import os, time, threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","EURGBP=X","USDCAD=X","USDCHF=X","EURCHF=X"]
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}; lock = threading.Lock()
stats = {"2M":0}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def ema(s,p): return s.ewm(span=p).mean()
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()
def secondi_chiusura():
    now = datetime.now(ITALY)
    prossimo = ((now.minute // 2) + 1) * 2
    if prossimo >= 60:
        chiusura = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    else:
        chiusura = now.replace(minute=prossimo, second=0, microsecond=0)
    return (chiusura - now).total_seconds()
def get_df(sym):
    try:
        with lock:
            url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=2m&range=5d"
            r=cffi_requests.get(url, impersonate="chrome120", timeout=10)
            q=r.json()['chart']['result'][0]['indicators']['quote'][0]
            df=pd.DataFrame({'Open':q['open'],'High':q['high'],'Low':q['low'],'Close':q['close']}).dropna()
            return df.tail(200)
    except: return pd.DataFrame()
def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=8)
    except: pass

def lavoro():
    print("2M 60% FINALE avviato", flush=True)
    while True:
        try:
            sec = secondi_chiusura()
            if not (50 <= sec <= 70):
                time.sleep(5); continue
            for sym in PAIRS:
                clean=sym.replace("=X","")
                if clean in cooldown and time.time()-cooldown[clean]<300: continue
                df=get_df(sym)
                if len(df)<60: continue
                df['ema20']=ema(df['Close'],20); df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
                c=df.iloc[-1]
                O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
                total=H-L
                if total<0.00003: continue
                atr_v=float(df['atr'].iloc[-1]); atr_ma=float(df['atr_ma'].iloc[-1])
                if atr_v < atr_ma*0.50: continue
                
                corpo=abs(O-C) or total*0.05; inf=min(O,C)-L; sup=H-max(O,C)
                forza=max(inf,sup)/total*100
                hammer=inf>=corpo*1.5 and inf>=total*0.45 and sup<=total*0.30 and corpo<=total*0.40
                star=sup>=corpo*1.5 and sup>=total*0.45 and inf<=total*0.30 and corpo<=total*0.40
                if not ((hammer or star) and 60<=forza<=92): continue # 60% FISSO
                
                rv=float(df['rsi'].iloc[-1])
                if hammer and not (20 <= rv <= 45): continue
                if star and not (55 <= rv <= 80): continue
                
                cooldown[clean]=time.time(); stats["2M"]+=1
                sig="CALL 📈" if hammer else "PUT 📉"
                tipo="Hammer" if hammer else "Star"
                chiusura = (datetime.now(ITALY) + timedelta(seconds=sec)).strftime("%H:%M:%S")
                scadenza = (datetime.now(ITALY) + timedelta(seconds=sec+120)).strftime("%H:%M:%S")
                send(f"⚡ <b>2M {int(sec)}s - {clean} {sig}</b> ⚡\n💱 {tipo} {forza:.0f}% RSI {rv:.0f}\n📍 {(H+L)/2:.5f} Price {C:.5f}\n⏰ Entra {chiusura} → Scad 2M {scadenza}\n🕒 {ora_it()}")
            time.sleep(10)
        except Exception as e:
            print(f"ERR {e}"); time.sleep(10)

threading.Thread(target=lavoro, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"2M 60% | {stats['2M']} | {ora_it()}"
if __name__=="__main__":
    send(f"🚀 <b>2M 60% FINALE</b>\n60% 1 MSG 60s prima Scad 2M\n{ora_it()}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
