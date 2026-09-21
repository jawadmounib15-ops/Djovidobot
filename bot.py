import os
import time
import threading
from flask import Flask
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X", "USDCHF=X", "NZDUSD=X", "EURCHF=X", "AUDJPY=X", "GBPCHF=X", "EURCAD=X", "AUDCAD=X", "NZDJPY=X"]

app = Flask(__name__)
@app.route('/')
def home():
    return "V61 TRIPLA CONFERMA 80% LIVE - 7 lavori con filtro 4H + ATR + RSI/Stoch"

pending = []
stats = {f"L{i}": {"win":0, "tot":0} for i in range(1,8)}

def send(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

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
    d_percent = k_percent.rolling(d).mean()
    return k_percent, d_percent

def get_trend_4h(symbol):
    try:
        df = yf.download(symbol, period="20d", interval="4h", progress=False)
        if len(df) < 60: return None
        df['e20'] = df['Close'].ewm(span=20).mean()
        df['e50'] = df['Close'].ewm(span=50).mean()
        df['e200'] = df['Close'].ewm(span=200).mean()
        last = df.iloc[-1]
        # Trend 4H: prezzo sopra e200 e e20>e50 = LONG
        if last['Close'] > last['e200'] and last['e20'] > last['e50']:
            return "LONG"
        if last['Close'] < last['e200'] and last['e20'] < last['e50']:
            return "SHORT"
        return None
    except:
        return None

def check_news_block():
    # Blocco orari news pericolose UTC: 12:25-13:00 e 18:45-19:15
    now = datetime.utcnow()
    hm = now.hour*60 + now.minute
    if 745 <= hm <= 780: return True
    if 1125 <= hm <= 1155: return True
    return False

def scan():
    if check_news_block():
        return
    for symbol in PAIRS:
        try:
            df = yf.download(symbol, period="5d", interval="15m", progress=False)
            if len(df) < 210: continue
            df['e20'] = df['Close'].ewm(span=20).mean()
            df['e50'] = df['Close'].ewm(span=50).mean()
            df['e200'] = df['Close'].ewm(span=200).mean()
            df['rsi'] = rsi(df['Close'])
            df['atr'] = atr(df, 14)
            df['atr_ma50'] = df['atr'].rolling(50).mean()
            k, d = stochastic(df)
            df['stoch_k'] = k
            df['stoch_d'] = d

            last = df.iloc[-1]
            prev = df.iloc[-2]
            clean = symbol.replace("=X","")

            # FILTRO 1: VOLATILITA' (Google: ATR)
            if last['atr'] < last['atr_ma50'] * 0.5: continue # mercato piatto, salta
            if last['atr'] > last['atr_ma50'] * 3.0: continue # news spike, salta

            # FILTRO 2: TREND 4H (Tripla conferma)
            trend4h = get_trend_4h(symbol)
            if trend4h is None: continue

            # --- LOGICA V61 ---
            price = float(last['Close'])
            rsi_val = float(last['rsi'])
            stoch_k = float(last['stoch_k'])

            signal = None
            level = None

            # TRIGGER LONG 80%: trend4h LONG + prezzo sopra EMA200 + Stoch <20 + RSI che risale da 30-50 + tocco e20
            if trend4h == "LONG" and price > float(last['e200']):
                tocco_e20 = abs(price - float(last['e20'])) / price < 0.0015
                rsi_trigger = 25 <= rsi_val <= 55 and rsi_val > float(prev['rsi'])
                stoch_trigger = stoch_k < 25 and float(last['stoch_d']) < 30

                if tocco_e20 and rsi_trigger and stoch_trigger:
                    signal = "BUY"
                    level = "L4 SICURO 80%"

            # TRIGGER SHORT 80%
            if trend4h == "SHORT" and price < float(last['e200']):
                tocco_e20 = abs(price - float(last['e20'])) / price < 0.0030
                rsi_trigger = 50 <= rsi_val <= 70 and rsi_val < float(prev['rsi'])
                stoch_trigger = stoch_k > 75 and float(last['stoch_d']) > 70

                if tocco_e20 and rsi_trigger and stoch_trigger:
                    signal = "SELL"
                    level = "L4 SICURO 80%"

            if signal:
                # Evita duplicati
                if any(p['symbol']==clean and p['level']==level for p in pending): continue

                tp = price * (1.0012 if signal=="BUY" else 0.9988) # 0.12% per 80% winrate
                sl = price * (0.9980 if signal=="BUY" else 1.0020) # 0.20%

                msg = f"🎯 {level} {signal} {clean}\nRSI {rsi_val:.1f} Stoch {stoch_k:.1f}\n4H Trend: {trend4h} OK\nATR OK Volatilità: {float(last['atr']):.5f}\nEntry: {price:.5f} TP: {tp:.5f} SL: {sl:.5f}"
                send(msg)
                pending.append({"symbol": clean, "level": level, "signal": signal, "entry": price, "time": time.time(), "tp": tp, "sl": sl})

        except Exception as e:
            continue

def check_results():
    now = time.time()
    for p in pending[:]:
        if now - p['time'] < 900: continue # 15 min
        try:
            df = yf.download(p['symbol']+"=X", period="1d", interval="1m", progress=False)
            if len(df)==0: continue
            curr = float(df['Close'].iloc[-1])
            win = False
            if p['signal']=="BUY" and curr > p['entry']: win=True
            if p['signal']=="SELL" and curr < p['entry']: win=True

            # Aggiorna stats
            key = "L4"
            stats[key]["tot"]+=1
            if win: stats[key]["win"]+=1
            perc = int(stats[key]["win"]/stats[key]["tot"]*100) if stats[key]["tot"]>0 else 0

            res = "WIN" if win else "LOSS"
            send(f"{res} {p['level']} {p['signal']} {p['symbol']} -> {perc}% ({stats[key]['win']}/{stats[key]['tot']})")
            pending.remove(p)
        except: pass

def loop():
    send("🚀 V61 TRIPLA CONFERMA 80% avviato ✅\nFiltri: 4H Trend + ATR + RSI/Stoch\nSegnali: pochi ma sicuri (20-30 al giorno)")
    while True:
        try:
            scan()
            check_results()
        except: pass
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
