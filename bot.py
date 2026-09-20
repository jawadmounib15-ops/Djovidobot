# V36.8.7 FINAL - NO EMOJI - FIX SELL SUL FONDO
import yfinance as yf, pandas as pd, ta, time, requests, os
from datetime import datetime
TOKEN = os.getenv("TELEGRAM_TOKEN","")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")
PAIRS = ["EUR/USD","GBP/USD","USD/JPY","EUR/JPY","GBP/JPY","AUD/USD","USD/CHF","EUR/GBP"]
COOLDOWN=300

def invia(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m}, timeout=10)
    except: pass

def analizza(pair):
    try:
        mp = {"GBP/USD":"GBPUSD=X","EUR/USD":"EURUSD=X","USD/JPY":"JPY=X","EUR/JPY":"EURJPY=X","GBP/JPY":"GBPJPY=X","AUD/USD":"AUDUSD=X","USD/CHF":"CHF=X","EUR/GBP":"EURGBP=X"}
        df = yf.download(mp.get(pair,"EURUSD=X"), period="2d", interval="5m", progress=False, auto_adjust=False)
        if df is None or len(df)<60: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close, high, low = df['Close'], df['High'], df['Low']
        rsi = float(ta.momentum.RSIIndicator(close,14).rsi().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        ema9, ema21 = float(close.ewm(9).mean().iloc[-1]), float(close.ewm(21).mean().iloc[-1])
        prev_c, curr_c = float(close.iloc[-2]), float(close.iloc[-1])
        prev_e9, prev_e21 = float(close.ewm(9).mean().iloc[-2]), float(close.ewm(21).mean().iloc[-2])

        # ZONA MORTA 43-57
        if 43 <= rsi <= 57: return None

        buy=sell=0; motivi=[]; has_L6=False

        if float(low.iloc[-1]) < sma50 and curr_c > sma50: buy+=1; motivi.append("L1")
        if float(high.iloc[-1]) > sma50 and curr_c < sma50: sell+=1; motivi.append("L1")
        if prev_c < sma50 and curr_c > sma50: buy+=1; motivi.append("L2")
        if prev_c > sma50 and curr_c < sma50: sell+=1; motivi.append("L2")
        if curr_c > float(high.iloc[-10:-1].max()): buy+=1; motivi.append("L3")
        if curr_c < float(low.iloc[-10:-1].min()): sell+=1; motivi.append("L3")
        if curr_c > sma50 and prev_c < curr_c: buy+=1; motivi.append("L4")
        if curr_c < sma50 and prev_c > curr_c: sell+=1; motivi.append("L4")
        if rsi <= 42: buy+=1; motivi.append("L5")
        if rsi >= 58: sell+=1; motivi.append("L5")
        if prev_e9 < prev_e21 and ema9 > ema21: buy+=1; motivi.append("L6"); has_L6=True
        if prev_e9 > prev_e21 and ema9 < ema21: sell+=1; motivi.append("L6"); has_L6=True
        if rsi < 50 and curr_c > sma50: buy+=1; motivi.append("L7")
        if rsi > 50 and curr_c < sma50: sell+=1; motivi.append("L7")

        # FILTRO 1: L6 OBBLIGATORIO
        if not has_L6: return None

        # FILTRO 2: NON VENDERE SUL FONDO - se prezzo e' gia' troppo sotto SMA50
        distanza = ((curr_c - sma50) / sma50) * 100
        if sell >=3 and distanza < -0.4: return None # gia' sceso troppo, no SELL
        if buy >=3 and distanza > 0.4: return None # gia' salito troppo, no BUY

        if buy >=3 and rsi <=42:
            return f"{pair} OTC BUY TF 5M | {'+'.join(motivi)} | RSI {int(rsi)} {datetime.now().strftime('%H:%M:%S')}"
        if sell >=3 and rsi >=58:
            return f"{pair} OTC SELL TF 5M | {'+'.join(motivi)} | RSI {int(rsi)} {datetime.now().strftime('%H:%M:%S')}"
        return None
    except Exception as e:
        print(f"Err {pair}: {e}"); return None

print("V36.8.7 NO EMOJI ATTIVO - L6 OBBL + ANTI FONDO")
invia("V36.8.7 ATTIVO - L6 obbl + Anti Sell sul fondo + 42/58")

last={}
while True:
    for p in PAIRS:
        if p in last and time.time()-last[p]<COOLDOWN: continue
        m=analizza(p)
        if m: print(m); invia(m); last[p]=time.time()
    time .sleep(10)
