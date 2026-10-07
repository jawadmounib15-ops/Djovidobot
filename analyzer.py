import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", "")).strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)
@app.route('/')
def home(): return f"V72.4 BILANCIATO - Pending:{len(pending)} Cooldown:{len(cooldown)} - {len(PAIRS)} PAIRS"
pending=[]; cooldown={}
_YF_SESSION = cffi_requests.Session(impersonate="chrome")

def send(msg):
    print(f"SEND: {msg}")
    if not TOKEN or not CHAT_ID: return
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=15)
    except: pass

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def atr(df,p=14):
    hl=df['High']-df['Low']; hc=abs(df['High']-df['Close'].shift()); lc=abs(df['Low']-df['Close'].shift())
    tr=pd.concat([hl,hc,lc],axis=1).max(axis=1)
    return tr.rolling(p).mean()
def stochastic(df,k=14,d=3):
    lo=df['Low'].rolling(k).min(); hi=df['High'].rolling(k).max()
    return 100*((df['Close']-lo)/(hi-lo))

def scan():
    global pending
    pending=[p for p in pending if time.time()-p['time']<1800]
    count_this_scan=0
    for symbol in PAIRS:
        if count_this_scan>=3: break
        clean=symbol.replace("=X","")
        # BLOCCO DOPPIONI VERO - 40 MIN
        if clean in cooldown and time.time()-cooldown[clean] < 2400: continue
        if any(p['symbol']==clean for p in pending): continue
        try:
            tk=yf.Ticker(symbol, session=_YF_SESSION)
            df=tk.history(period="5d", interval="15m")
            df=fix_df(df)
            if len(df)<210: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e50']=df['Close'].ewm(span=50).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close']); df['atr']=atr(df,14); df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k']=stochastic(df)
            last=df.iloc[-1]
            o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close'])
            price=c; rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
            e20=float(last['e20']); e50=float(last['e50']); e200=float(last['e200'])
            is_green=c>o; is_red=not is_green
            body=abs(c-o); rng=h-l; upper=h-max(o,c); lower=min(o,c)-l

            # ATR POCO STRETTO
            if last['atr'] < last['atr_ma50']*0.58: continue
            if last['atr'] > last['atr_ma50']*2.20: continue

            tocco_e20=abs(price-e20)/price < 0.0045
            if abs(price-e200)/price < 0.0005: continue
            slope_e20 = float(df['e20'].iloc[-1] - df['e20'].iloc[-3])

            signal=None; lavoro=""; scadenza=""

            # ===== L1 TREND - POCO STRETTO MA SENZA 58-59 FARLOCCO =====
            if not signal:
                # BUY: RSI 28-53 invece di 28-47 (più segnali)
                if price>e200 and e20>e50 and slope_e20>=0 and 28<=rsi_v<=53 and stoch_k<38 and is_green and tocco_e20:
                    signal="BUY"; lavoro="L1 TREND"; scadenza="30 MIN"
                # SELL: RSI 57-72 invece di 60-70 (prende anche 57-59 ma filtra 58-59 piatti)
                if price<e200 and e20<e50 and slope_e20<=0 and 57<=rsi_v<=72 and stoch_k>62 and is_red and tocco_e20:
                    # filtro in più: se RSI è 57-59 deve avere slope negativa forte
                    if 57<=rsi_v<=59 and slope_e20>-0.00010:
                        signal=None
                    else:
                        signal="SELL"; lavoro="L1 TREND"; scadenza="15 MIN"

            # ===== L2 PINBAR PULITA - POCO STRETTO =====
            if not signal and rng>0:
                pin_bull = lower > body*2.0 and body < rng*0.45 and upper < body*1.1 and is_green
                pin_bear = upper > body*2.0 and body < rng*0.45 and lower < body*1.1 and is_red
                # BUY pinbar RSI 30-54 (prima 30-55, ora leggermente più largo ma non 58)
                if pin_bull and price>e200 and e20>e50 and 28<=rsi_v<=54:
                    signal="BUY"; lavoro="L2 PINBAR"; scadenza="30 MIN"
                # SELL pinbar RSI 46-72 (prima 45-70)
                if pin_bear and price<e200 and e20<e50 and 46<=rsi_v<=72:
                    signal="SELL"; lavoro="L2 PINBAR"; scadenza="15 MIN"

            if signal:
                if clean in ["EURGBP","EURJPY","GBPCHF","EURAUD"]:
                    scadenza="30 MIN"
                send(f"🎯 {lavoro} {signal} {clean} ⏰ {scadenza} 07/10 RSI{int(rsi_v)} STO{int(stoch_k)}\nEntry {price:.5f}")
                pending.append({"symbol":clean,"signal":signal,"entry":price,"time":time.time()})
                cooldown[clean]=time.time()
                count_this_scan+=1
        except Exception as e:
            print(f"ERR {clean}: {e}"); continue

def check_results():
    for p in pending[:]:
        if time.time()-p['time'] < 900: continue
        try:
            df=yf.Ticker(p['symbol']+"=X", session=_YF_SESSION).history(period="1d", interval="1m")
            df=fix_df(df)
            if len(df)==0: continue
            curr=float(df['Close'].iloc[-1])
            win=(p['signal']=="BUY" and curr>p['entry']) or (p['signal']=="SELL" and curr<p['entry'])
            send(f"{'WIN ✅' if win else 'LOSS ❌'} {p['symbol']} {p['signal']} {((curr-p['entry'])/p['entry']*100):+.3f}%")
            pending.remove(p)
        except: pass

def loop():
    time.sleep(3)
    if TOKEN and CHAT_ID:
        send(f"🚀 V72.4 BILANCIATO AVVIATO\nPoco stretto = 5-8 segnali al giorno\nFix doppioni + RSI bilanciato")
    while True:
        try: scan(); check_results()
        except Exception as e: print(f"LOOP ERR {e}")
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
