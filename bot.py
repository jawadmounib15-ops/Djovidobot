# bot.py - 2M LARGO PER TEST - POI STRINGIAMO
import os, time, threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","EURGBP=X","USDCAD=X","USDCHF=X","EURCHF=X","AUDJPY=X","CHFJPY=X"] # 12 coppie largo
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}; lock = threading.Lock()
stats = {"2M":0}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S %d/%m")
def scadenza_it(m=4): return (datetime.now(ITALY)+timedelta(minutes=m)).strftime("%H:%M:%S %d/%m")
def ema(s,p): return s.ewm(span=p).mean()
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def get_df_2m(sym):
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

def lavoro_2m_largo():
    print("2M LARGO TEST avviato", flush=True)
    while True:
        try:
            for sym in PAIRS:
                clean=sym.replace("=X","")
                if clean in cooldown and time.time()-cooldown[clean]<300: continue # 5 min solo - era 10
                df=get_df_2m(sym)
                if len(df)<60: continue
                df['ema20']=ema(df['Close'],20); df['ema50']=ema(df['Close'],50); df['ema200']=ema(df['Close'],200)
                df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
                c=df.iloc[-2]; conf=df.iloc[-1]
                O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
                total=H-L
                if total<0.00003: continue # era 0.00005
                
                # LARGO: ATR 0.50 invece di 0.80
                atr_v=float(df['atr'].iloc[-2]); atr_ma=float(df['atr_ma'].iloc[-2])
                if atr_v < atr_ma*0.50: continue
                if atr_v > atr_ma*3.0: continue
                
                corpo=abs(O-C) or total*0.05; inf=min(O,C)-L; sup=H-max(O,C)
                forza=max(inf,sup)/total*100
                # LARGO: 60% invece di 72% + wick 1.5 invece di 2.0
                hammer=inf>=corpo*1.5 and inf>=total*0.45 and sup<=total*0.30 and corpo<=total*0.40
                star=sup>=corpo*1.5 and sup>=total*0.45 and inf<=total*0.30 and corpo<=total*0.40
                if not ((hammer or star) and 60<=forza<=92): continue
                
                # LARGO: supporto 1.002 invece di 1.0008
                low30=df['Low'].iloc[-31:-2].min(); high30=df['High'].iloc[-31:-2].max()
                if hammer and L > low30*1.002: 
                    # non bloccare, solo declassa
                    pass
                if star and H < high30*0.998:
                    pass
                
                e20=float(df['ema20'].iloc[-2]); e200=float(df['ema200'].iloc[-2])
                rv=float(df['rsi'].iloc[-2])
                # LARGO: RSI 20-45 e 55-80 invece di 20-38 e 62-80
                if hammer and not (20 <= rv <= 45): continue
                if star and not (55 <= rv <= 80): continue
                # LARGO: 0.6% invece di 0.25%
                if abs(C-e20)/C > 0.006: continue
                
                # LARGO: togliamo filtro contro EMA200 per test
                # if hammer and C < e200*0.9985: continue
                
                # LARGO: conferma 50% invece di 65%
                conf_c=float(conf['Close'])
                if hammer and conf_c < L+total*0.50: continue
                if star and conf_c > H-total*0.50: continue
                
                cooldown[clean]=time.time(); stats["2M"]+=1
                sig="CALL 📈" if hammer else "PUT 📉"
                tipo="Hammer" if hammer else "Star"
                sc=scadenza_it(4)
                msg=(
                    f"⚡ <b>2M LARGO TEST</b> ⚡\n"
                    f"💱 {clean} {sig} {tipo} {forza:.0f}%\n"
                    f"📍 Entry {(H+L)/2:.5f} Price {C:.5f}\n"
                    f"⏰ Scad 4M alle {sc}\n"
                    f"📊 RSI {rv:.0f} ATR {atr_v:.5f} vs MA {atr_ma:.5f}\n"
                    f"📉 EMA20 {e20:.5f} Dist {((C-e20)/C*100):+.2f}% EMA200 {e200:.5f}\n"
                    f"✅ Conf {conf_c:.5f} | 🕒 {ora_it()}\n"
                    f"⚙️ FILTRO LARGO 60% - TEST"
                )
                send(msg)
                time.sleep(1.2)
            time.sleep(10)
        except Exception as e: print(f"2M LARGO ERR {e}"); time.sleep(10)

threading.Thread(target=lavoro_2m_largo, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"2M LARGO TEST | Segnali:{stats['2M']} | {ora_it()} | Forza 60% | 12 coppie"
if __name__=="__main__":
    send(f"🚀 <b>2M LARGO TEST AVVIATO</b>\nForza 60-92% RSI 20-45/55-80\nATR 0.50x 12 coppie Cooldown 5m\n{ora_it()}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
