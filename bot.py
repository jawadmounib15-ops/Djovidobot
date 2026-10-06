import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
ROMA = pytz.timezone("Europe/Rome")

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X",
         "EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X",
         "GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)
@app.route('/')
def home(): return f"V62 PRECISO >60% - {len(PAIRS)} PAIRS - cooldown 90min - fix 23:00"

pending=[]; cooldown={}

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=10)
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
    k_perc=100*((df['Close']-lo)/(hi-lo))
    return k_perc, k_perc.rolling(d).mean()

def scan():
    now=datetime.now(ROMA)
    # FIX 23:00 MERCATO CHIUSO - non spamma domenica
    if now.weekday()==5 or now.weekday()==6 or (now.weekday()==4 and now.hour>=23):
        return

    count_this_scan=0
    for symbol in PAIRS:
        if count_this_scan>=2: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 5400: continue
        try:
            df=yf.download(symbol, period="5d", interval="15m", progress=False)
            df=fix_df(df)
            if len(df)<210: continue
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k'],_ = stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
            e20=float(last['e20']); e200=float(last['e200'])

            # PRECISO: ATR 0.75-1.70 era 0.70-1.8 troppo largo
            if last['atr'] < last['atr_ma50']*0.75 or last['atr'] > last['atr_ma50']*1.70: continue
            # PRECISO: tocco EMA20 0.08% era 0.3%
            if abs(price-e20)/price >= 0.0008: continue
            # PRECISO: distanza EMA200 0.20% era 0.1%
            if abs(price-e200)/price < 0.0020: continue
            # NUOVO: pendenza EMA20
            e20_slope = float(df['e20'].iloc[-1] - df['e20'].iloc[-3])
            # NUOVO: candela conferma
            is_green = float(df['Close'].iloc[-1]) > float(df['Open'].iloc[-1])
            is_red = not is_green

            signal=None
            # LOGICA GIUSTA + PRECISA - >60% WIN
            # BUY = uptrend + pullback + RSI basso + STO bassissimo + candela verde
            if price>e200*1.0015 and e20>e200 and e20_slope>0 and 22<=rsi_v<=33 and 8<=stoch_k<=22 and is_green:
                signal="BUY"
            # SELL = downtrend + pullback + RSI alto + STO altissimo + candela rossa
            if price<e200*0.9985 and e20<e200 and e20_slope<0 and 66<=rsi_v<=73 and 78<=stoch_k<=92 and is_red:
                signal="SELL"

            if signal:
                if any(p['symbol']==clean for p in pending): continue
                send(f"🎯 V62 PRECISO {signal} {clean} RSI {rsi_v:.0f} STO {stoch_k:.0f} Entry {price:.5f} | Slope {e20_slope:+.5f}")
                pending.append({"symbol":clean,"signal":signal,"entry":price,"time":time.time()})
                cooldown[clean]=time.time()
                count_this_scan+=1
        except: continue

def check_results():
    now=time.time()
    for p in pending[:]:
        if now-p['time'] < 300: continue # check dopo 5 min non 1 min
        try:
            df=yf.download(p['symbol']+"=X", period="1d", interval="1m", progress=False)
            df=fix_df(df)
            if len(df)==0: continue
            curr=float(df['Close'].iloc[-1])
            win=(p['signal']=="BUY" and curr>p['entry']) or (p['signal']=="SELL" and curr<p['entry'])
            pct=((curr-p['entry'])/p['entry']*100) if p['signal']=="BUY" else ((p['entry']-curr)/p['entry']*100)
            send(f"{'WIN ✅ +{:.2f}%'.format(pct) if win else 'LOSS ❌ {:.2f}%'.format(pct)} V62 {p['signal']} {p['symbol']} Entry {p['entry']:.5f} -> {curr:.5f}")
            pending.remove(p)
        except:
            pending.remove(p)

def loop():
    send(f"🚀 V62 PRECISO AVVIATO - {len(PAIRS)} coppie - LOGICA GIUSTA RSI 22-33/66-73 STO 8-22/78-92 + slope + candela + fix 23:00 - Target >60% WIN")
    while True:
        try: scan(); check_results()
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
