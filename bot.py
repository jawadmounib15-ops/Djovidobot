# bot.py - 2M LARGO + PRE-ALLARME 60 SEC
import os, time, threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","EURGBP=X","USDCAD=X","USDCHF=X","EURCHF=X","AUDJPY=X","CHFJPY=X"]
ITALY = ZoneInfo("Europe/Rome")
cooldown = {}; pre_cooldown = {}; lock = threading.Lock()
stats = {"2M":0, "PRE":0}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S %d/%m")
def scadenza_it(m=4): return (datetime.now(ITALY)+timedelta(minutes=m)).strftime("%H:%M:%S")
def ema(s,p): return s.ewm(span=p).mean()
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def secondi_alla_chiusura_2m():
    now = datetime.now(ITALY)
    minuto = now.minute
    prossimo = ((minuto // 2) + 1) * 2
    if prossimo >= 60:
        prossima_ora = now + timedelta(hours=1)
        chiusura = prossima_ora.replace(minute=0, second=0, microsecond=0)
    else:
        chiusura = now.replace(minute=prossimo, second=0, microsecond=0)
    return (chiusura - now).total_seconds()

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

def lavoro_2m():
    print("2M LARGO + PRE 60s avviato", flush=True)
    while True:
        try:
            sec = secondi_alla_chiusura_2m()
            is_pre_window = 35 <= sec <= 80  # finestra 35-80 sec prima della chiusura
            
            for sym in PAIRS:
                clean=sym.replace("=X","")
                df=get_df_2m(sym)
                if len(df)<60: continue
                df['ema20']=ema(df['Close'],20); df['ema200']=ema(df['Close'],200)
                df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
                
                # Se siamo in finestra PRE, guarda candela in formazione
                if is_pre_window:
                    if clean in pre_cooldown and time.time()-pre_cooldown[clean]<120: continue
                    c = df.iloc[-1]
                    idx = -1
                else:
                    if clean in cooldown and time.time()-cooldown[clean]<300: continue
                    c = df.iloc[-2]
                    idx = -2
                
                O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
                total=H-L
                if total<0.00003: continue
                atr_v=float(df['atr'].iloc[idx]); atr_ma=float(df['atr_ma'].iloc[idx])
                if atr_v < atr_ma*0.50: continue
                if atr_v > atr_ma*3.0: continue
                
                corpo=abs(O-C) or total*0.05; inf=min(O,C)-L; sup=H-max(O,C)
                forza=max(inf,sup)/total*100
                hammer=inf>=corpo*1.5 and inf>=total*0.45 and sup<=total*0.30 and corpo<=total*0.40
                star=sup>=corpo*1.5 and sup>=total*0.45 and inf<=total*0.30 and corpo<=total*0.40
                if not ((hammer or star) and 60<=forza<=92): continue
                
                rv=float(df['rsi'].iloc[idx]); e20=float(df['ema20'].iloc[idx])
                if hammer and not (20 <= rv <= 45): continue
                if star and not (55 <= rv <= 80): continue
                if abs(C-e20)/C > 0.006: continue
                
                sig="CALL 📈" if hammer else "PUT 📉"
                tipo="Hammer" if hammer else "Star"
                
                if is_pre_window:
                    pre_cooldown[clean]=time.time(); stats["PRE"]+=1
                    msg=(
                        f"⏳ <b>PRE {int(sec)}s - {clean}</b> ⏳\n"
                        f"💱 {sig} {tipo} {forza:.0f}% in formazione\n"
                        f"📍 Price {C:.5f} | RSI {rv:.0f} | ATR {atr_v:.5f}\n"
                        f"⏰ Chiude tra {int(sec)}s alle {scadenza_it(0)}\n"
                        f"⚠️ Preparati, conferma tra {int(sec)}s\n"
                        f"🕒 {ora_it()}"
                    )
                    send(msg)
                else:
                    # Conferma finale
                    conf=df.iloc[-1]
                    conf_c=float(conf['Close'])
                    if hammer and conf_c < L+total*0.50: continue
                    if star and conf_c > H-total*0.50: continue
                    cooldown[clean]=time.time(); stats["2M"]+=1
                    msg=(
                        f"⚡ <b>SEGNALE 2M</b> ⚡\n"
                        f"💱 {clean} {sig} {tipo} {forza:.0f}%\n"
                        f"📍 Entry {(H+L)/2:.5f} | Price {C:.5f}\n"
                        f"⏰ Scad 4M alle {scadenza_it(4)}\n"
                        f"📊 RSI {rv:.0f} EMA20 {e20:.5f}\n"
                        f"✅ Conf {conf_c:.5f}\n"
                        f"🕒 {ora_it()}"
                    )
                    send(msg)
                time.sleep(0.8)
            time.sleep(7)
        except Exception as e:
            print(f"ERR {e}"); time.sleep(10)

threading.Thread(target=lavoro_2m, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"2M PRE 60s | PRE:{stats['PRE']} Segnali:{stats['2M']} | {ora_it()} | Forza 60%"
if __name__=="__main__":
    send(f"🚀 <b>2M PRE 60s AVVIATO</b>\n⏳ Pre-allarme 60s prima\n⚡ Segnale confermato alla chiusura\nFiltro LARGO 60% - TEST\n{ora_it()}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
