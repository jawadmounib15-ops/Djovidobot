# bot.py - 2 MIN SOLO REALI - V2M
import os, time, threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd, requests
from curl_cffi import requests as cffi_requests
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","EURGBP=X","USDCAD=X"] # 8 major - su 2m non usare 17 sono troppi

ITALY = ZoneInfo("Europe/Rome")
cooldown = {}; lock = threading.Lock()
stats = {"2M":0}

def ora_it(): return datetime.now(ITALY).strftime("%H:%M:%S")
def scadenza_it(m=4): return (datetime.now(ITALY)+timedelta(minutes=m)).strftime("%H:%M:%S")
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
            # 2m range 1d - massimo che Yahoo da
            url=f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=2m&range=1d"
            r=cffi_requests.get(url, impersonate="chrome120", timeout=8)
            q=r.json()['chart']['result'][0]['indicators']['quote'][0]
            df=pd.DataFrame({'Open':q['open'],'High':q['high'],'Low':q['low'],'Close':q['close']}).dropna()
            return df.tail(200)
    except: return pd.DataFrame()

def send(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m,"parse_mode":"HTML"}, timeout=8)
    except: pass

def lavoro_2m_reali():
    print("2M REALI avviato", flush=True)
    while True:
        try:
            for sym in PAIRS:
                clean=sym.replace("=X","")
                if clean in cooldown and time.time()-cooldown[clean]<600: continue # 10 min cooldown - anti spam
                if not 8 <= datetime.now(ITALY).hour <= 22: time.sleep(60); continue
                
                df=get_df_2m(sym)
                if len(df)<80: continue
                df['ema20']=ema(df['Close'],20); df['ema50']=ema(df['Close'],50); df['ema200']=ema(df['Close'],200)
                df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma']=df['atr'].rolling(50).mean()
                
                c=df.iloc[-2]; conf=df.iloc[-1] # candela chiusa + conferma
                O,H,L,C=float(c['Open']),float(c['High']),float(c['Low']),float(c['Close'])
                total=H-L
                if total<0.00005: continue
                
                # SOLO MERCATO ATTIVO - niente lento
                atr_v=float(df['atr'].iloc[-2]); atr_ma=float(df['atr_ma'].iloc[-2])
                if atr_v < atr_ma*0.80: continue
                if atr_v > atr_ma*2.2: continue
                
                corpo=abs(O-C); inf=min(O,C)-L; sup=H-max(O,C)
                forza=max(inf,sup)/total*100
                
                # PINBAR REALI 2M - 72-92%
                hammer=inf>=corpo*2.0 and inf>=total*0.58 and sup<=total*0.18 and corpo<=total*0.28
                star=sup>=corpo*2.0 and sup>=total*0.58 and inf<=total*0.18 and corpo<=total*0.28
                if not ((hammer or star) and 72<=forza<=92): continue
                
                # Supporto/Resistenza 30 candele - OBBLIGATORIO su 2m
                low30=df['Low'].iloc[-31:-2].min(); high30=df['High'].iloc[-31:-2].max()
                if hammer and L > low30*1.0008: continue
                if star and H < high30*0.9992: continue
                
                e20=float(df['ema20'].iloc[-2]); e50=float(df['ema50'].iloc[-2]); e200=float(df['ema200'].iloc[-2])
                rv=float(df['rsi'].iloc[-2])
                
                # RSI REALE 2M
                if hammer and not (20 <= rv <= 38): continue
                if star and not (62 <= rv <= 80): continue
                
                # Distanza EMA20 max 0.25% - se lontano è falso
                if abs(C-e20)/C > 0.0025: continue
                
                # Contro trend no
                if hammer and C < e200*0.9985: continue
                if star and C > e200*1.0015: continue
                
                # Conferma OK obbligatoria
                conf_c=float(conf['Close'])
                if hammer and (conf_c < L+total*0.65 or conf_c <= float(conf['Open'])): continue
                if star and (conf_c > H-total*0.65 or conf_c >= float(conf['Open'])): continue
                
                # SL check
                sl = L-total*0.3 if hammer else H+total*0.3
                if abs(sl-C)/C < 0.0006: continue
                
                cooldown[clean]=time.time(); stats["2M"]+=1
                sig="CALL 📈" if hammer else "PUT 📉"
                tipo="Hammer Reale" if hammer else "Shooting Star Reale"
                sc=scadenza_it(4)
                
                msg=(
                    f"⚡ <b>2M REALE</b> ⚡\n"
                    f"💱 {clean} {sig}\n"
                    f"📍 Entry {(H+L)/2:.5f} | Price {C:.5f}\n"
                    f"⏰ TF 2M → Scad 4M alle {sc}\n"
                    f"📊 {tipo} {forza:.0f}% | RSI {rv:.0f} | ATR ATTIVO ✓\n"
                    f"📉 EMA20 {e20:.5f} Dist {((C-e20)/C*100):+.2f}% | EMA200 {e200:.5f}\n"
                    f"✅ Conf {conf_c:.5f} OK | SL {sl:.5f}\n"
                    f"🕒 {ora_it()}"
                )
                send(msg)
                time.sleep(1.5)
            time.sleep(15) # scan ogni 15 sec su 2m
        except Exception as e: print(f"2M ERR {e}"); time.sleep(10)

threading.Thread(target=lavoro_2m_reali, daemon=True).start()
app=Flask(__name__)
@app.route('/')
def home(): return f"2M REALI | Segnali:{stats['2M']} | {ora_it()} | Cooldown 10m | Forza 72-92%"
if __name__=="__main__":
    send(f"🚀 <b>2M REALI AVVIATO</b>\nTF 2M → Scad 4M\nFiltro 72-92% + Supp/Res 30 + ATR attivo\n{ora_it()}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
