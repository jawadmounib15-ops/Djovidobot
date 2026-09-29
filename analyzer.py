# analyzer.py - FILE UNICO PER RENDER - SICURO 15m + 1H
from flask import Flask, jsonify, render_template
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import os
from curl_cffi import requests as cffi_requests

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

YAHOO_MAP_REAL = {
    "EURUSD=X":"EUR/USD", "GBPUSD=X":"GBP/USD", "AUDUSD=X":"AUD/USD",
    "USDJPY=X":"USD/JPY", "EURJPY=X":"EUR/JPY", "GBPJPY=X":"GBP/JPY",
    "AUDJPY=X":"AUD/JPY", "EURGBP=X":"EUR/GBP"
}
YAHOO_MAP_OTC = {k: v+" OTC" for k,v in YAHOO_MAP_REAL.items()}

def get_df(symbol, interval="15m", period="20d"):
    try:
        base = symbol.replace(" OTC","")
        y_sym = [k for k,v in YAHOO_MAP_REAL.items() if v==base][0]
        df = yf.Ticker(y_sym, session=session).history(period=period, interval=interval)
        if len(df) < 60: return None
        cl = df['Close']
        df['EMA9'] = cl.ewm(9).mean()
        df['EMA21'] = cl.ewm(21).mean()
        df['EMA50'] = cl.ewm(50).mean()
        df['ATR'] = (df['High']-df['Low']).rolling(14).mean()
        delta = cl.diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['RSI'] = 100 - (100/(1+gain/loss))
        return df
    except: return None

def get_trend_1h(symbol):
    try:
        base = symbol.replace(" OTC","")
        y_sym = [k for k,v in YAHOO_MAP_REAL.items() if v==base][0]
        df = yf.Ticker(y_sym, session=session).history(period="20d", interval="1h")
        if len(df)<60: return None
        ema21 = df['Close'].ewm(21).mean().iloc[-1]
        ema50 = df['Close'].ewm(50).mean().iloc[-1]
        return "UP" if ema21 > ema50 else "DOWN"
    except: return None

def calcola_scadenza():
    now = datetime.now(ROMA)
    minuto = (now.minute // 15 + 1) * 15
    if minuto >= 60:
        s15 = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        s15 = now.replace(minute=minuto, second=0, microsecond=0)
    s30 = s15 + timedelta(minutes=15)
    return s15.strftime("%H:%M"), s30.strftime("%H:%M")

def check_pinbar(o,h,l,c):
    body = abs(c-o); rng = h-l
    if rng==0: return None
    up = h-max(o,c); low = min(o,c)-l
    if body < rng*0.12 or body > rng*0.25: return None
    if min(up,low) > rng*0.18: return None
    if max(up,low) < rng*0.65: return None
    if max(up,low) < body*2.2 or max(up,low) > body*6.5: return None
    return (up, low)

def lavoro1_trend(df):
    r = df.iloc[-1]
    pin = check_pinbar(r['Open'],r['High'],r['Low'],r['Close'])
    if not pin: return None
    up, low = pin
    if not (42 <= r['RSI'] <= 58): return None
    if low>up and r['EMA9']>r['EMA21'] and r['Close']>r['EMA50']:
        return {"lavoro":"L1 TREND", "dir":"CALL", "rsi":round(float(r['RSI']),1)}
    if up>low and r['EMA9']<r['EMA21'] and r['Close']<r['EMA50']:
        return {"lavoro":"L1 TREND", "dir":"PUT", "rsi":round(float(r['RSI']),1)}
    return None

def lavoro2_sporgenza(df):
    r = df.iloc[-1]
    pin = check_pinbar(r['Open'],r['High'],r['Low'],r['Close'])
    if not pin: return None
    up, low = pin
    prev_low = df['Low'].iloc[-11:-1].min()
    prev_high = df['High'].iloc[-11:-1].max()
    if low>up and r['Low'] < prev_low*0.999:
        return {"lavoro":"L2 SPORGENZA", "dir":"CALL", "rsi":round(float(r['RSI']),1)}
    if up>low and r['High'] > prev_high*1.001:
        return {"lavoro":"L2 SPORGENZA", "dir":"PUT", "rsi":round(float(r['RSI']),1)}
    return None

def lavoro7_volatilita(df):
    r = df.iloc[-1]
    pin = check_pinbar(r['Open'],r['High'],r['Low'],r['Close'])
    if not pin: return None
    up, low = pin
    rng = r['High']-r['Low']
    if rng < r['ATR']*0.8 or rng > r['ATR']*2.0: return None
    if low>up and r['Close']>r['EMA9']:
        return {"lavoro":"L7 VOLA", "dir":"CALL", "rsi":round(float(r['RSI']),1)}
    if up>low and r['Close']<r['EMA9']:
        return {"lavoro":"L7 VOLA", "dir":"PUT", "rsi":round(float(r['RSI']),1)}
    return None

def analizza_coppia(label):
    df15 = get_df(label)
    if df15 is None: return []
    trend1h = get_trend_1h(label)
    if trend1h is None: return []
    s15, s30 = calcola_scadenza()
    segnali = []
    for lavoro in [lavoro1_trend, lavoro2_sporgenza, lavoro7_volatilita]:
        res = lavoro(df15)
        if not res: continue
        if res["dir"]=="CALL" and trend1h=="DOWN": continue
        if res["dir"]=="PUT" and trend1h=="UP": continue
        res.update({
            "coppia": label, "trend1h": trend1h, "is_otc": "OTC" in label,
            "scadenza": s15, "scadenza_30": s30, "ora": datetime.now(ROMA).strftime("%H:%M:%S")
        })
        segnali.append(res)
    return segnali

def analizza_tutto():
    out = []
    for label in list(YAHOO_MAP_REAL.values()) + list(YAHOO_MAP_OTC.values()):
        out.extend(analizza_coppia(label))
    return out

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/signals')
def signals():
    try:
        return jsonify(analizza_tutto())
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
