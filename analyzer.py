import os, time, threading
from flask import Flask, jsonify
from datetime import datetime, timedelta
import pandas as pd
import requests
from curl_cffi import requests as cffi_requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCHF=X","EURCAD=X","EURAUD=X","GBPJPY=X","GBPCHF=X","GBPAUD=X","AUDJPY=X","CADJPY=X","CHFJPY=X","NZDJPY=X","AUDCAD=X","NZDCAD=X"]

app = Flask(__name__)
pins_live = []
pins_storico = []
cooldown = {}
LOG_FILE = "/tmp/v66.log"

def log(m):
    line = f"{datetime.now().strftime('%H:%M:%S')} {m}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except: pass

def send(msg):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":msg}, timeout=10)
    except: pass

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

def get_df_fast(symbol):
    for attempt in range(2):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=15m&range=5d"
            r = cffi_requests.get(url, impersonate="chrome120", timeout=8)
            if r.status_code!=200:
                log(f"{symbol} HTTP {r.status_code}")
                continue
            j=r.json()
            quote=j['chart']['result'][0]['indicators']['quote'][0]
            df=pd.DataFrame({'High':quote['high'],'Low':quote['low'],'Close':quote['close']}).dropna()
            if len(df)<50: continue
            log(f"{symbol} OK {len(df)}")
            return df
        except Exception as e:
            log(f"{symbol} ERR {str(e)[:50]}")
            time.sleep(1)
    log(f"{symbol} SKIP")
    return pd.DataFrame()

def scan():
    log(">>> INIZIO SCAN")
    count=0
    for symbol in PAIRS:
        if count>=3: break
        clean=symbol.replace("=X","")
        if clean in cooldown and time.time()-cooldown[clean] < 2700: continue
        df=get_df_fast(symbol)
        if len(df)<210: continue
        try:
            df['e20']=df['Close'].ewm(span=20).mean()
            df['e200']=df['Close'].ewm(span=200).mean()
            df['rsi']=rsi(df['Close'])
            df['atr']=atr(df,14)
            df['atr_ma50']=df['atr'].rolling(50).mean()
            df['stoch_k'],_ = stochastic(df)
            last=df.iloc[-1]
            price=float(last['Close']); rsi_v=float(last['rsi']); stoch_k=float(last['stoch_k'])
            if last['atr'] < last['atr_ma50']*0.70: continue
            if last['atr'] > last['atr_ma50']*1.8: continue
            tocco_e20=abs(price-float(last['e20']))/price < 0.003
            dist_e200=abs(price-float(last['e200']))/price
            if dist_e200 < 0.001: continue
            signal=None
            if price>float(last['e200']) and tocco_e20 and 30<=rsi_v<=36 and stoch_k<15: signal="BUY"
            if price<float(last['e200']) and tocco_e20 and 64<=rsi_v<=70 and stoch_k>85: signal="SELL"
            if signal:
                scad=datetime.now()+timedelta(minutes=15)
                pin={"asset":clean,"dir":"CALL SU" if signal=="BUY" else "PUT GIÙ","signal":signal,"entry":round(price,5),"rsi":round(rsi_v,0),"sto":round(stoch_k,0),"ora":datetime.now().strftime("%H:%M:%S"),"data":datetime.now().strftime("%d/%m %H:%M:%S"),"scadenza":scad.strftime("%H:%M:%S"),"scad_ts":scad.timestamp(),"scad":"15 MIN"}
                pins_live.insert(0,pin); pins_storico.insert(0,pin)
                pins_live=pins_live[:20]; pins_storico=pins_storico[:100]
                send(f"V66 {signal} {clean} RSI {rsi_v:.0f}")
                log(f"*** SEGNALE {clean} {signal} ***")
                cooldown[clean]=time.time()
                count+=1
        except Exception as e:
            log(f"calc {clean} {e}")
    log(f">>> FINE SCAN trovati {count}")

def loop():
    # pulisci log vecchio
    try: os.remove(LOG_FILE)
    except: pass
    log("LOOP V66 AVVIATO V61.1 ORIGINALE - NO WINLOSS")
    send("🚀 V66 ORIGINALE FIX - log su file")
    while True:
        try: scan()
        except Exception as e: log(f"LOOP ERR {e}")
        time.sleep(60)

@app.route('/')
def home():
    return f"V66 FIX - <a href='/debug'>CLICCA QUI DEBUG</a> - Live {len(pins_live)}"
@app.route('/debug')
def debug():
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()[-50:]
    except:
        lines = ["log vuoto"]
    h="<b>LOG V66 DA FILE - ora devi vedere INIZIO/FINE e OK</b><br><br>"
    for l in lines[::-1]: h+=f"{l}<br>"
    h+=f"<br>Live:{len(pins_live)}<br><a href='/debug'>reload</a> - <a href='/'>home</a>"
    return h

@app.route('/api/pins')
def api_pins(): return jsonify(pins_live)
@app.route('/api/storico')
def api_storico(): return jsonify(pins_storico)

threading.Thread(target=loop, daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
