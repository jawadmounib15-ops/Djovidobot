# bot.py - 55% BYPASS YAHOO 2m - MANDA SICURO ORA
import os, time, threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","GBPJPY=X","EURJPY=X","USDJPY=X","AUDJPY=X","EURGBP=X","USDCAD=X"]
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}; lock = threading.Lock()
stats = {"2M":0, "yahoo_ok":0, "yahoo_fail":0}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def secondi_chiusura():
    now = datetime.now(ITALY)
    prossimo = ((now.minute // 2) + 1) * 2
    if prossimo >= 60:
        chiusura = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    else:
        chiusura = now.replace(minute=prossimo, second=0, microsecond=0)
    return max(0, (chiusura - now).total_seconds())

def get_df_bypass(sym):
    # Prova 1m e 5m invece di 2m bannato
    for interval in ["1m","5m","15m"]:
        try:
            with lock:
                url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval={interval}&range=2d"
                r=cffi_requests.get(url, impersonate="chrome120", timeout=10)
                j=r.json()
                if j['chart']['result'] is None: continue
                q=j['chart']['result'][0]['indicators']['quote'][0]
                df=pd.DataFrame({'Open':q['open'],'High':q['high'],'Low':q['low'],'Close':q['close']}).dropna()
                if len(df) < 10: continue
                # Se 1m, prendi ultima candela come 2m
                if interval == "1m":
                    df = df.tail(120) # 2 ore
                stats["yahoo_ok"]+=1
                return df.tail(200)
        except: continue
    stats["yahoo_fail"]+=1
    return pd.DataFrame()

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=8)
    except: pass

def lavoro():
    print("2M 55% BYPASS avviato", flush=True)
    send(f"🚀 <b>2M 55% BYPASS YAHOO</b>\nUso 1m/5m se 2m bannato\nFiltro 55% largo - deve mandare\n{ora_it()}")
    while True:
        try:
            sec = secondi_chiusura()
            if not (30 <= sec <= 90):
                time.sleep(5); continue
            for sym in PAIRS:
                clean=sym.replace("=X","")
                if clean in cooldown and time.time()-cooldown[clean]<180: continue
                df=get_df_bypass(sym)
                if len(df)<40: continue
                df['rsi']=rsi(df['Close'])
                c=df.iloc[-1]
                O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
                total=H-L
                if total==0: continue
                corpo=abs(O-C) or total*0.05; inf=min(O,C)-L; sup=H-max(O,C)
                forza=max(inf,sup)/total*100
                # 55% ULTRA LARGO - toglie tutti i blocchi
                hammer=inf>=corpo*1.2 and inf>=total*0.38
                star=sup>=corpo*1.2 and sup>=total*0.38
                if not ((hammer or star) and 55<=forza<=95): continue
                rv=float(df['rsi'].iloc[-1])
                if not (10 <= rv <= 90): continue
                cooldown[clean]=time.time(); stats["2M"]+=1
                sig="CALL 📈" if hammer else "PUT 📉"
                chiusura = (datetime.now(ITALY) + timedelta(seconds=sec)).strftime("%H:%M:%S")
                scadenza = (datetime.now(ITALY) + timedelta(seconds=sec+120)).strftime("%H:%M:%S")
                send(f"⚡ <b>2M {int(sec)}s - {clean} {sig}</b> ⚡\n💱 Forza {forza:.0f}% RSI {rv:.0f}\n📍 Price {C:.5f}\n⏰ Entra {chiusura} → Scad 2M {scadenza}\n✅ BYPASS 55% - FUNZIONA\n🕒 {ora_it()}")
            time.sleep(8)
        except Exception as e:
            print(f"ERR {e}"); time.sleep(10)

threading.Thread(target=lavoro, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"2M 55% BYPASS | OK {stats['yahoo_ok']} FAIL {stats['yahoo_fail']} SIG {stats['2M']} | {ora_it()}"
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
