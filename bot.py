# V36.8.8 SNIPER - NO EMOJI - ANTI CROLLO
import yfinance as yf, pandas as pd, ta, time, requests, os
from datetime import datetime
TOKEN = os.getenv("TELEGRAM_TOKEN","")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")
PAIRS = ["EUR/USD","GBP/USD","USD/JPY","EUR/JPY","GBP/JPY","AUD/USD","USD/CHF","EUR/GBP"]
COOLDOWN=600 # 10 min per evitare spam

def invia(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m}, timeout=10)
    except: pass

def analizza(pair):
    try:
        mp = {"GBP/USD":"GBPUSD=X","EUR/USD":"EURUSD=X","USD/JPY":"JPY=X","EUR/JPY":"EURJPY=X","GBP/JPY":"GBPJPY=X","AUD/USD":"AUDUSD=X","USD/CHF":"CHF=X","EUR/GBP":"EURGBP=X"}
        df = yf.download(mp.get(pair,"EURUSD=X"), period="2d", interval="5m", progress=False, auto_adjust=False)
        if df is None or len(df)<80: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close, high, low = df['Close'], df['High'], df['Low']

        rsi = float(ta.momentum.RSIIndicator(close,14).rsi().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        ema9 = float(close.ewm(9).mean().iloc[-1])
        ema21 = float(close.ewm(21).mean().iloc[-1])
        prev_c, curr_c = float(close.iloc[-2]), float(close.iloc[-1])
        prev_e9, prev_e21 = float(close.ewm(9).mean().iloc[-2]), float(close.ewm(21).mean().iloc[-2])

        # ULTIME 3 CANDELE - SE 3 ROSSE NO BUY, SE 3 VERDI NO SELL
        last3 = close.iloc[-4:-1]
        three_red = last3.iloc[0] > last3.iloc[1] and last3.iloc[1] > last3.iloc[2]
        three_green = last3.iloc[0] < last3.iloc[1] and last3.iloc[1] < last3.iloc[2]

        # FILTRO TREND FORTE - NO CONTROTREND
        if 38 <= rsi <= 62: return None # zona morta piu larga

        buy=sell=0; motivi=[]; has_L6=False; has_L5=False; has_L2=False

        if float(low.iloc[-1]) < sma50 and curr_c > sma50: buy+=1; motivi.append("L1")
        if float(high.iloc[-1]) > sma50 and curr_c < sma50: sell+=1; motivi.append("L1")
        if prev_c < sma50 and curr_c > sma50: buy+=1; motivi.append("L2"); has_L2=True
        if prev_c > sma50 and curr_c < sma50: sell+=1; motivi.append("L2"); has_L2=True
        if curr_c > float(high.iloc[-10:-1].max()): buy+=1; motivi.append("L3")
        if curr_c < float(low.iloc[-10:-1].min()): sell+=1; motivi.append("L3")
        if rsi <= 35: buy+=1; motivi.append("L5"); has_L5=True
        if rsi >= 65: sell+=1; motivi.append("L5"); has_L5=True
        if prev_e9 < prev_e21 and ema9 > ema21: buy+=1; motivi.append("L6"); has_L6=True
        if prev_e9 > prev_e21 and ema9 < ema21: sell+=1; motivi.append("L6"); has_L6=True
        if rsi < 40 and curr_c > sma50: buy+=1; motivi.append("L7")
        if rsi > 60 and curr_c < sma50: sell+=1; motivi.append("L7")

        if not has_L6: return None
        if not has_L5: return None # L5 OBBLIGATORIO ORA
        if not has_L2: return None # L2 OBBLIGATORIO

        if buy >=3 and three_red: return None # crollo in corso, no buy
        if sell >=3 and three_green: return None # pump in corso, no sell

        if curr_c < sma50 and buy>=3: return None # no buy sotto SMA in downtrend
        if curr_c > sma50 and sell>=3: return None # no sell sopra SMA in uptrend

        if buy >=3 and rsi <=35:
            return f"{pair} OTC BUY TF 5M | {'+'.join(motivi)} | RSI {int(rsi)} {datetime.now().strftime('%H:%M:%S')}"
        if sell >=3 and rsi >=65:
            return f"{pair} OTC SELL TF 5M | {'+'.join(motivi)} | RSI {int(rsi)} {datetime.now().strftime('%H:%M:%S')}"
        return None
    except Exception as e:
        print(f"Err {pair}: {e}"); return None

print("V36.8.8 SNIPER ATTIVO - L2+L5+L6 OBBL + RSI 35/65")
invia("V36.8.8 SNIPER ATTIVO - Solo segnali TOP - L2+L5+L6 + RSI 35/65 + Anti Crollo")

last={}
while True:
    for p in PAIRS:
        if p in last and time.time()-last[p]<COOLDOWN: continue
        m=analizza(p)
        if m: print(m); invia(m); last[p]=time.time()
    time.sleep(10)
