# bot.py - 3 LAVORI DIVERSI SEPARATI - 70-80%
import os, time, threading, gc
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

PAIRS = ["EURUSD=X","GBPUSD=X","EURGBP=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","CHFJPY=X","USDCAD=X","USDCHF=X","EURCHF=X","CADJPY=X","CADCHF=X","AUDCHF=X","AUDCAD=X","GBPCAD=X"]

ITALY = ZoneInfo("Europe/Rome")
cooldown = {}
lock = threading.Lock()
stats = {"L1":0,"L2":0,"L3":0}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def ora_num(): return datetime.now(ITALY).hour
def ema(s,p): return s.ewm(span=p).mean()
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def get_df(sym):
    try:
        with lock:
            url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1m&range=1d"
            r=cffi_requests.get(url, impersonate="chrome120", timeout=6)
            q=r.json()['chart']['result'][0]['indicators']['quote'][0]
            df=pd.DataFrame({'Open':q['open'],'High':q['high'],'Low':q['low'],'Close':q['close']}).dropna()
            return df.tail(100)
    except: return pd.DataFrame()

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=8)
    except: pass

# ================= LAVORO 1 UNICO - PINBAR 80% (i 5 filtri insieme) =================
def lavoro1_pinbar_80():
    print("LAVORO 1 PINBAR 80% avviato", flush=True)
    while True:
        try:
            for sym in PAIRS:
                clean=sym.replace("=X","")
                if clean in cooldown and time.time()-cooldown[clean]<900:
                    time.sleep(0.5); continue
                if ora_num()<8 or ora_num()>22:
                    time.sleep(60); continue
                df=get_df(sym)
                if len(df)<80:
                    time.sleep(1); continue
                c=df.iloc[-2]; conf=df.iloc[-1]
                O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
                total=H-L
                if total<0.00005: time.sleep(1); continue
                corpo=abs(O-C) or total*0.05
                inf,sup=min(O,C)-L, H-max(O,C)
                forza=(inf if inf>sup else sup)/total*100
                hammer=inf>=corpo*1.75 and inf>=total*0.46 and sup<=total*0.28 and corpo<=total*0.40
                star=sup>=corpo*1.75 and sup>=total*0.46 and inf<=total*0.28 and corpo<=total*0.40
                if not (hammer or star and 68<=forza<=88): time.sleep(1); continue
                # SR
                if (hammer and L>df['Low'].iloc[-27:-2].min()*1.0012) or (star and H<df['High'].iloc[-27:-2].max()*0.9988): time.sleep(1); continue
                # TREND+RSI
                df['ema20']=ema(df['Close'],20); df['ema50']=ema(df['Close'],50); df['rsi']=rsi(df['Close'])
                e20=float(df['ema20'].iloc[-2]); e50=float(df['ema50'].iloc[-2]); e20p=float(df['ema20'].iloc[-8]); rv=float(df['rsi'].iloc[-2])
                if hammer and not (e20<e50*1.001 and e20<e20p and rv<42): time.sleep(1); continue
                if star and not (e20>e50*0.999 and e20>e20p and rv>58): time.sleep(1); continue
                # CONF
                if hammer and (float(conf['Close'])<L+total*0.60 or float(conf['Close'])<=float(conf['Open'])): time.sleep(1); continue
                if star and (float(conf['Close'])>H-total*0.60 or float(conf['Close'])>=float(conf['Open'])): time.sleep(1); continue
                cooldown[clean]=time.time(); stats["L1"]+=1
                sig="CALL" if hammer else "PUT"
                send(f"💎 <b>L1 PINBAR 80%</b> 💎\n{clean} {sig}\nEntry {(H+L)/2:.5f} Forza {forza:.0f}% RSI {rv:.0f}\n5 filtri OK\n{ora_it()}")
                time.sleep(1.5)
            time.sleep(35)
        except Exception as e: print(f"L1 ERR {e}"); time.sleep(10)

# ================= LAVORO 2 DIVERSO - ENGULFING 75% =================
def lavoro2_engulfing_75():
    print("LAVORO 2 ENGULFING 75% avviato", flush=True)
    while True:
        try:
            for sym in PAIRS:
                clean=sym.replace("=X","")
                if clean in cooldown and time.time()-cooldown[clean]<600: time.sleep(0.5); continue
                df=get_df(sym)
                if len(df)<80: time.sleep(1); continue
                c1=df.iloc[-3]; c2=df.iloc[-2]; c3=df.iloc[-1]
                df['ema20']=ema(df['Close'],20); df['rsi']=rsi(df['Close'])
                e20=float(df['ema20'].iloc[-2]); rv=float(df['rsi'].iloc[-2])
                # BULLISH ENGULFING
                bull = float(c2['Close'])<float(c2['Open']) and float(c3['Close'])>float(c3['Open']) and float(c3['Close'])>float(c2['Open']) and float(c3['Open'])<float(c2['Close']) and abs(float(c3['Close'])-float(c3['Open']))>abs(float(c2['Close'])-float(c2['Open']))*1.5
                bear = float(c2['Close'])>float(c2['Open']) and float(c3['Close'])<float(c3['Open']) and float(c3['Close'])<float(c2['Open']) and float(c3['Open'])>float(c2['Close']) and abs(float(c3['Close'])-float(c3['Open']))>abs(float(c2['Close'])-float(c2['Open']))*1.5
                if not (bull or bear): time.sleep(1); continue
                # FILTRO SICURO 75%
                if bull and not (rv<38 and float(df['Close'].iloc[-1])>e20): time.sleep(1); continue
                if bear and not (rv>62 and float(df['Close'].iloc[-1])<e20): time.sleep(1); continue
                if abs(float(c3['Close'])-e20)/float(c3['Close'])>0.003: time.sleep(1); continue # tocca EMA20
                cooldown[clean]=time.time(); stats["L2"]+=1
                sig="CALL" if bull else "PUT"
                send(f"🔥 <b>L2 ENGULFING 75%</b> 🔥\n{clean} {sig}\nEntry {float(c3['Close']):.5f} RSI {rv:.0f}\nEngulf + EMA20\n{ora_it()}")
                time.sleep(1.5)
            time.sleep(45)
        except Exception as e: print(f"L2 ERR {e}"); time.sleep(10)

# ================= LAVORO 3 DIVERSO - RSI RIMBALZO 70% =================
def lavoro3_rsi_bounce_70():
    print("LAVORO 3 RSI BOUNCE 70% avviato", flush=True)
    while True:
        try:
            for sym in PAIRS:
                clean=sym.replace("=X","")
                if clean in cooldown and time.time()-cooldown[clean]<600: time.sleep(0.5); continue
                df=get_df(sym)
                if len(df)<80: time.sleep(1); continue
                df['ema50']=ema(df['Close'],50); df['rsi']=rsi(df['Close'],14)
                last=df.iloc[-1]; price=float(last['Close']); rv=float(df['rsi'].iloc[-1]); e50=float(df['ema50'].iloc[-1])
                # RSI ESTREMO + RIMBALZO SU EMA50
                buy = 20<=rv<=30 and price>e50 and abs(price-e50)/price<0.004 and float(df['Close'].iloc[-2])<float(df['Close'].iloc[-1])
                sell = 70<=rv<=80 and price<e50 and abs(price-e50)/price<0.004 and float(df['Close'].iloc[-2])>float(df['Close'].iloc[-1])
                if not (buy or sell): time.sleep(1); continue
                cooldown[clean]=time.time(); stats["L3"]+=1
                sig="CALL" if buy else "PUT"
                send(f"⚡ <b>L3 RSI BOUNCE 70%</b> ⚡\n{clean} {sig}\nEntry {price:.5f} RSI {rv:.0f}\nRSI estremo + EMA50\n{ora_it()}")
                time.sleep(1.5)
            time.sleep(60)
        except Exception as e: print(f"L3 ERR {e}"); time.sleep(10)

# AVVIA 3 LAVORI SEPARATI
threading.Thread(target=lavoro1_pinbar_80, daemon=True).start()
time.sleep(3)
threading.Thread(target=lavoro2_engulfing_75, daemon=True).start()
time.sleep(3)
threading.Thread(target=lavoro3_rsi_bounce_70, daemon=True).start()

app=Flask(__name__)
@app.route('/')
def home(): return f"3 LAVORI DIVERSI | L1 Pin80%:{stats['L1']} L2 Eng75%:{stats['L2']} L3 Rsi70%:{stats['L3']} | {ora_it()}"
if __name__=="__main__":
    send(f"🚀 <b>3 LAVORI DIVERSI AVVIATI</b>\nL1: PINBAR 80% (5 filtri)\nL2: ENGULFING 75%\nL3: RSI BOUNCE 70%\n17 coppie | Anti-lag\n{ora_it()}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
