# bot.py - 3 PILASTRI STRATEGIA PINBAR PULITA - COME DA SCREEN
import os, time, requests, yfinance as yf
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "3 PILASTRI PINBAR OK"

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")
ITALY_TZ = timezone(timedelta(hours=2))

BASE = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","USDCHF=X"]
LABELS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","USD/CAD-OTC","EUR/JPY-OTC","USD/CHF-OTC"]
LABELS_REALI = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD","EUR/JPY","USD/CHF"]
ALL = list(zip(BASE, LABELS_OTC, LABELS_REALI))

LAST={}; AVVIO=False

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_df(y, interval, period):
    try:
        df=yf.download(y, period=period, interval=interval, progress=False, auto_adjust=False)
        if len(df)<100: return None
        if hasattr(df.columns,'get_level_values'):
            try: df.columns=df.columns.get_level_values(0)
            except: pass
        c=df['Close']
        df['EMA21']=c.ewm(21).mean(); df['EMA50']=c.ewm(50).mean()
        return df
    except: return None

def check_3_pilastri(y):
    # Prendiamo 2 timeframe: 5m per segnale, 4H simulato con 15m x16 per contesto
    df5 = get_df(y,"5m","5d")
    df_trend = get_df(y,"15m","10d") # per simulare H4 trend
    if df5 is None or df_trend is None: return None

    # --- 1. IDENTIKIT PINBAR PULITA (dal tuo screen 1) ---
    c = df5.iloc[-1]; o=float(c['Open']); cc=float(c['Close']); h=float(c['High']); l=float(c['Low'])
    body=abs(cc-o); rng=h-l
    if rng==0: return None
    upper = h - max(o,cc)
    lower = min(o,cc) - l
    nose = min(upper, lower) if (cc>o and upper<lower) or (cc<o and lower<upper) else max(upper,lower)
    # Regola più piccola
    wick = max(upper, lower)

    if wick < rng*0.70: return None # 1. Ombra almeno 70%
    if body > rng*0.25: return None # 2. Corpo piccolo
    if nose > rng*0.12: return None # 3. Naso cortissimo <12%

    # 4. Sporgenza: deve sporgere rispetto alle 10 candele precedenti
    prev_lows = df5['Low'].iloc[-11:-1].min()
    prev_highs = df5['High'].iloc[-11:-1].max()
    sporge_bull = l < prev_lows*0.998
    sporge_bear = h > prev_highs*1.002
    if not (sporge_bull or sporge_bear): return None

    # --- 2. A. CONTESTO (Trend vs Range) ---
    ema21_trend = float(df_trend['EMA21'].iloc[-1]); ema50_trend = float(df_trend['EMA50'].iloc[-1])
    ema21_5m = float(df5['EMA21'].iloc[-1]); ema50_5m = float(df5['EMA50'].iloc[-1])
    trend_up = ema21_trend > ema50_trend and ema21_5m > ema50_5m
    trend_down = ema21_trend < ema50_trend and ema21_5m < ema50_5m

    # --- 2. B. CONFLUENZA GRAFICA ---
    # Supporti/Resistenze statici: guarda massimi/minimi ultimi 50 candele H4
    swing_high = float(df_trend['High'].iloc[-50:].max())
    swing_low = float(df_trend['Low'].iloc[-50:].min())
    # Fibonacci 50-61.8%
    fib_50 = swing_low + (swing_high-swing_low)*0.50
    fib_618 = swing_low + (swing_high-swing_low)*0.618
    in_fibo = (fib_50*0.998 <= cc <= fib_618*1.002) or (fib_50*0.998 <= l <= fib_618*1.002) or (fib_50*0.998 <= h <= fib_618*1.002)

    tocca_ema21 = abs(cc - ema21_5m) < rng*0.5 or abs(l - ema21_5m) < rng*0.5
    tocca_ema50 = abs(cc - ema50_5m) < rng*0.5 or abs(l - ema50_5m) < rng*0.5
    tocca_sup_res = abs(cc - swing_low) < rng or abs(cc - swing_high) < rng

    confluenza = sum([in_fibo, tocca_ema21, tocca_ema50, tocca_sup_res]) >= 1 # almeno 1 come da screen
    if not confluenza: return None

    # DIREZIONE FINALE - Solo pullback nella direzione del trend principale
    if lower == wick and sporge_bull and trend_up and (tocca_ema21 or tocca_ema50 or in_fibo):
        return "BUY", int((wick/rng)*100), "Pullback UP + EMA21/50 + Fibo" if in_fibo else "Pullback UP + EMA"
    if upper == wick and sporge_bear and trend_down and (tocca_ema21 or tocca_ema50 or in_fibo):
        return "SELL", int((wick/rng)*100), "Pullback DOWN + EMA21/50 + Fibo" if in_fibo else "Pullback DOWN + EMA"

    return None

def bot_loop():
    global AVVIO
    if not AVVIO:
        send(f"✅ *3 PILASTRI ATTIVI*\n1. Wick>70% Body<25% Naso<12% + Sporgenza\n2. Trend + EMA21/50 + Fibo 50-61.8%\nFiltra tutti i falsi\n{datetime.now(ITALY_TZ).strftime('%H:%M:%S')} ITALIA")
        AVVIO=True
    while True:
        try:
            for base, otc, reali in ALL:
                now=datetime.now(ITALY_TZ)
                # Per rispettare time frame corretto evitiamo 1m, usiamo chiusura 5m
                sec=(5-now.minute%5)*60-now.second
                if not 20 <= sec <= 120: continue

                res = check_3_pilastri(base)
                if not res: continue
                direction, perc, motivo = res

                for label in [otc, reali]:
                    key=f"{label}_{direction}_PILASTRI"
                    if key in LAST and time.time()-LAST[key]<600: continue # 10 min

                    if direction=="BUY":
                        msg=f"💎 *PINBAR PULITA 3 PILASTRI*\n{label}\n🟢 BUY 5M\nWick {perc}% | Naso OK | Sporgenza OK\n📍 {motivo}\n⏰ {now.strftime('%H:%M:%S')} ITALIA"
                    else:
                        msg=f"💎 *PINBAR PULITA 3 PILASTRI*\n{label}\n🔴 SELL 5M\nWick {perc}% | Naso OK | Sporgenza OK\n📍 {motivo}\n⏰ {now.strftime('%H:%M:%S')} ITALIA"
                    send(msg); LAST[key]=time.time()
                time.sleep(1)
            time.sleep(5)
        except Exception as e:
            print(e); time.sleep(5)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
