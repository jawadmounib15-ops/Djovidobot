import os, time, threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TOKEN", ""))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X", "USDCHF=X", "NZDUSD=X", "EURCHF=X", "AUDJPY=X", "GBPCHF=X", "EURCAD=X", "AUDCAD=X", "NZDJPY=X"]

app = Flask(__name__)
@app.route('/')
def home():
    return "V61 FIXED LIVE"

pending=[]

def send(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

def fix_df(df):
    # FIX BUG yfinance nuovo che ritorna MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta>0, 0).rolling(period).mean()
    loss = -delta.where(delta<0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100/(1+rs))

def atr(df, period=14):
    hl = df['High'] - df['Low']
    hc = abs(df['High'] - df['Close'].shift())
    lc = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def stochastic(df, k=14, d=3):
    low_min = df['Low'].rolling(k).min()
    high_max = df['High'].rolling(k).max()
    k_percent = 100 * ((df['Close'] - low_min) / (high_max - low_min))
    return k_percent, k_percent.rolling(d).mean()

def scan():
    for symbol in PAIRS:
        try:
            df = yf.download(symbol, period="5d", interval="15m", progress=False)
            df = fix_df(df)
            if len(df) < 210: continue
            df['e20'] = df['Close'].ewm(span=20).mean()
            df['e200'] = df['Close'].ewm(span=200).mean()
            df['rsi'] = rsi(df['Close'])
            df['atr'] = atr(df, 14)
            df['atr_ma50'] = df['atr'].rolling(50).mean()
            df['stoch_k'], _ = stochastic(df)
            
            last = df.iloc[-1]
            clean = symbol.replace("=X","")
            price = float(last['Close'])
            rsi_val = float(last['rsi'])
            stoch_k = float(last['stoch_k'])

            # FILTRO LOOSE per vedere segnali subito
            if last['atr'] < last['atr_ma50'] * 0.4: continue
            if last['atr'] > last['atr_ma50'] * 3.5: continue

            tocco_e20 = abs(price - float(last['e20'])) / price < 0.005
            signal = None
            if price > float(last['e200']) and tocco_e20 and 20 <= rsi_val <= 60 and stoch_k < 35:
                signal = "BUY"
            if price < float(last['e200']) and tocco_e20 and 40 <= rsi_val <= 80 and stoch_k > 65:
                signal = "SELL"

            if signal:
                if any(p['symbol']==clean for p in pending): continue
                send(f"🎯 L4 LOOSE {signal} {clean} RSI {rsi_val:.1f} Entry {price:.5f}")
                pending.append({"symbol": clean, "signal": signal, "entry": price, "time": time.time()})
        except Exception as e:
            print(f"err {symbol} {e}")
            continue

def check_results():
    now = time.time()
    for p in pending[:]:
        if now - p['time'] < 900: continue
        try:
            df = yf.download(p['symbol']+"=X", period="1d", interval="1m", progress=False)
            df = fix_df(df)
            if len(df)==0: continue
            curr = float(df['Close'].iloc[-1])
            win = (p['signal']=="BUY" and curr > p['entry']) or (p['signal']=="SELL" and curr < p['entry'])
            send(f"{'WIN ✅' if win else 'LOSS ❌'} L4 {p['signal']} {p['symbol']}")
            pending.remove(p)
        except: pass

def loop():
    send(f"🚀 V61 FIX BUG APPLICATO - Ora deve mandare!\nTOKEN {TOKEN[:10]}...")
    while True:
        try:
            scan()
            check_results()
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
