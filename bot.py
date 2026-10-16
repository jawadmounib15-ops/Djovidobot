# bot.py - L1 PERFETTO + L2 FIX + L3 FIX
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
cooldown_l1 = {}
cooldown_l2 = {}
cooldown_l3 = {}
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

# ================= LAVORO 1 PERFETTO - NON TOCCATO =================
def lavoro1_pinbar_80():
    print("LAVORO 1 PINBAR 80% PERFETTO avviato", flush=True)
    while True:
        try:
            for sym in PAIRS:
                clean=sym.replace("=X","")
                if clean in cooldown_l1 and time.time()-cooldown_l1[clean]<900: time.sleep(0.5); continue
                if ora_num()<8 or ora_num()>22: time.sleep(60); continue
                df=get_df(sym)
                if len(df)<80: time.sleep(1); continue
                c=df.iloc[-2]; conf=df.iloc[-1]
                O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
                total=H-L
                if total<0.00005: time.sleep(1); continue
                corpo=abs(O-C) or total*0.05
                inf,sup=min(O,C)-L, H-max(O,C)
                forza=(inf if inf>sup else sup)/total*100
                hammer=inf>=corpo*1.75 and inf>=total*0.46 and sup<=total*0.28 and corpo<=total*0.40
                star=sup>=corpo*1.75 and sup>=total*0.46 and inf<=total*0.28 and corpo<=total*0.40
                if not ((hammer or star) and 68<=forza<=88): time.sleep(1); continue
                if (hammer and L>df['Low'].iloc[-27:-2].min()*1.0012) or (star and H<df['High'].iloc[-27:-2].max()*0.9988): time.sleep(1); continue
                df['ema20']=ema(df['Close'],20); df['ema50']=ema(df['Close'],50); df['rsi']=rsi(df['Close'])
                e20=float(df['ema20'].iloc[-2]); e50=float(df['ema50'].iloc[-2]); e20p=float(df['ema20'].iloc[-8]); rv=float(df['rsi'].iloc[-2])
                if hammer and not (e20<e50*1.001 and e20<e20p and rv<42): time.sleep(1); continue
                if star and not (e20>e50*0.999 and e20>e20p and rv>58): time.sleep(1); continue
                if hammer and (float(conf['Close'])<L+total*0.60 or float(conf['Close'])<=float(conf['Open'])): time.sleep(1); continue
                if star and (float(conf['Close'])>H-total*0.60 or float(conf['Close'])>=float(conf['Open'])): time.sleep(1); continue
                cooldown_l1[clean]=time.time(); stats["L1"]+=1
                sig="CALL" if hammer else "PUT"
                send(f"💎 <b>L1 PINBAR 80%</b> 💎\n{clean} {sig}\nEntry {(H+L)/2:.5f} Forza {forza:.0f}% RSI {rv:.0f}\n5 filtri OK\n{ora_it()}")
                time.sleep(1.5)
            time.sleep(35)
        except Exception as e: print(f"L1 ERR {e}"); time.sleep(10)

# ================= LAVORO 2 FIX - ENGULFING ALLARGATO =================
def lavoro2_engulfing_75():
    print("LAVORO 2 ENGULFING FIX avviato", flush=True)
    while True:
        try:
            for sym in PAIRS:
                clean=sym.replace("=X","")
                if clean in cooldown_l2 and time.time()-cooldown_l2[clean]<500: time.sleep(0.5); continue
                df=get_df(sym)
                if len(df)<80: time.sleep(1); continue
                c2=df.iloc[-2]; c3=df.iloc[-1]
                df['ema20']=ema(df['Close'],20); df['ema50']=ema(df['Close'],50); df['rsi']=rsi(df['Close'])
                e20=float(df['ema20'].iloc[-1]); e50=float(df['ema50'].iloc[-1]); rv=float(df['rsi'].iloc[-1])
                # ALLARGATO: 1.2x invece di 1.5x + solo 2 candele
                bull = float(c2['Close'])<float(c2['Open']) and float(c3['Close'])>float(c3['Open']) and float(c3['Close'])>float(c2['Open']) and abs(float(c3['Close'])-float(c3['Open']))>abs(float(c2['Close'])-float(c2['Open']))*1.2
                bear = float(c2['Close'])>float(c2['Open']) and float(c3['Close'])<float(c3['Open']) and float(c3['Close'])<float(c2['Open']) and abs(float(c3['Close'])-float(c3['Open']))>abs(float(c2['Close'])-float(c2['Open']))*1.2
                if not (bull or bear): time.sleep(1); continue
                # FILTRO ALLARGATO: RSI 45/55 invece di 38/62 + EMA50 trend
                if bull and not (rv<45 and float(df['Close'].iloc[-1])>e20 and e20>e50*0.998): time.sleep(1); continue
                if bear and not (rv>55 and float(df['Close'].iloc[-1])<e20 and e20<e50*1.002): time.sleep(1); continue
                # DISTANZA EMA20 ALLARGATA 0.5% invece di 0.3%
                if abs(float(c3['Close'])-e20)/float(c3['Close'])>0.005: time.sleep(1); continue
                cooldown_l2[clean]=time.time(); stats["L2"]+=1
                sig="CALL" if bull else "PUT"
                send(f"🔥 <b>L2 ENGULFING 75% FIX</b> 🔥\n{clean} {sig}\nEntry {float(c3['Close']):.5f} RSI {rv:.0f}\n{ora_it()}")
                time.sleep(1.5)
            time.sleep(30)
        except Exception as e: print(f"L2 ERR {e}"); time.sleep(10)

# ================= LAVORO 3 FIX - RSI BOUNCE CON CONFERMA =================
def lavoro3_rsi_bounce_70():
    print("LAVORO 3 RSI FIX avviato", flush=True)
    while True:
        try:
            for sym in PAIRS:
                clean=sym.replace("=X","")
                if clean in cooldown_l3 and time.time()-cooldown_l3[clean]<600: time.sleep(0.5); continue
                df=get_df(sym)
                if len(df)<80: time.sleep(1); continue
                df['ema20']=ema(df['Close'],20); df['ema50']=ema(df['Close'],50); df['rsi']=rsi(df['Close'],14)
                last=df.iloc[-1]; prev=df.iloc[-2]
                price=float(last['Close']); rv=float(last['rsi']); e50=float(df['ema50'].iloc[-1]); e20=float(df['ema20'].iloc[-1])
                # FIX: serve rimbalzo vero + 2 candele di conferma
                buy = 18<=rv<=32 and price>e50 and price>e20 and float(prev['Close'])<price and float(df['Close'].iloc[-3])<float(prev['Close']) and abs(price-e50)/price<0.0035
                sell = 68<=rv<=82 and price<e50 and price<e20 and float(prev['Close'])>price and float(df['Close'].iloc[-3])>float(prev['Close']) and abs(price-e50)/price<0.0035
                if not (buy or sell): time.sleep(1); continue
                cooldown_l3[clean]=time.time(); stats["L3"]+=1
                sig="CALL" if buy else "PUT"
                send(f"⚡ <b>L3 RSI BOUNCE FIX</b> ⚡\n{clean} {sig}\nEntry {price:.5f} RSI {rv:.0f}\nConferma 2 candele\n{ora_it()}")
                time.sleep(1.5)
            time.sleep(45)
        except Exception as e: print(f"L3 ERR {e}"); time.sleep(10)

threading.Thread(target=lavoro1_pinbar_80, daemon=True).start()
time.sleep(2)
threading.Thread(target=lavoro2_engulfing_75, daemon=True).start()
time.sleep(2)
threading.Thread(target=lavoro3_rsi_bounce_70, daemon=True).start()

app=Flask(__name__)
@app.route('/')
def home(): return f"L1 80%:{stats['L1']} L2 FIX:{stats['L2']} L3 FIX:{stats['L3']} | {ora_it()} | 3 cooldown separati"
if __name__=="__main__":
    send(f"🚀 <b>FIX AVVIATO</b>\nL1 PERFETTO invariato\nL2 ALLARGATO 1.2x RSI 45/55\nL3 CONFERMA 2 candele\n{ora_it()}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
