# bot.py - 3 PILASTRI AL CONTRARIO (INVERTITO)
import os, time, requests, yfinance as yf
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "3 PILASTRI ROVINATO CONTRARIO OK"

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

def check_3_pilastri_contrario(y):
    df5 = get_df(y,"5m","5d")
    df_trend = get_df(y,"15m","10d")
    if df5 is None or df_trend is None: return None

    c = df5.iloc[-1]; o=float(c['Open']); cc=float(c['Close']); h=float(c['High']); l=float(c['Low'])
    body=abs(cc-o); rng=h-l
    if rng==0: return None
    upper = h - max(o,cc)
    lower = min(o,cc) - l
    wick = max(upper, lower)
    nose = min(upper, lower)

    # Stesse regole ma largate
    if wick < rng*0.62: return None
    if body > rng*0.30: return None
    if nose > rng*0.18: return None
    if wick < body*2.0: return None

    prev_lows = df5['Low'].iloc[-8:-1].min()
    prev_highs = df5['High'].iloc[-8:-1].max()
    sporge_bull = l <= prev_lows*0.999
    sporge_bear = h >= prev_highs*1.001
    super_wick = wick > rng*0.70
    if not (sporge_bull or sporge_bear or super_wick): return None

    ema21_trend = float(df_trend['EMA21'].iloc[-1]); ema50_trend = float(df_trend['EMA50'].iloc[-1])
    ema21_5m = float(df5['EMA21'].iloc[-1]); ema50_5m = float(df5['EMA50'].iloc[-1])
    trend_up = ema21_5m > ema50_5m or ema21_trend > ema50_trend
    trend_down = ema21_5m < ema50_5m or ema21_trend < ema50_trend

    swing_high = float(df_trend['High'].iloc[-50:].max())
    swing_low = float(df_trend['Low'].iloc[-50:].min())
    fib_382 = swing_low + (swing_high-swing_low)*0.382
    fib_786 = swing_low + (swing_high-swing_low)*0.786
    in_fibo = fib_382*0.99 <= cc <= fib_786*1.01

    tocca_ema21 = abs(cc - ema21_5m) < rng*1.0
    tocca_ema50 = abs(cc - ema50_5m) < rng*1.0
    tocca_sup_res = abs(cc - swing_low) < rng*1.5 or abs(cc - swing_high) < rng*1.5
    confluenza = sum([in_fibo, tocca_ema21, tocca_ema50, tocca_sup_res]) >= 1
    if not confluenza: return None

    # --- INVERTITO QUI: ---
    # Prima: lower==wick + trend_up = BUY
    # Ora: lower==wick + trend_up = SELL (al contrario)
    if lower == wick and trend_up:
        return "SELL", int((wick/rng)*100), "CONTRARIO - era BUY ora SELL"
    if upper == wick and trend_down:
        return "BUY", int((wick/rng)*100), "CONTRARIO - era SELL ora BUY"
    return None

def bot_loop():
    global AVVIO
    if not AVVIO:
        send(f"🔄 *3 PILASTRI AL CONTRARIO*\nWick>62% - INVERTITO BUY/SELL\n{datetime.now(ITALY_TZ).strftime('%H:%M:%S')} ITALIA")
        AVVIO=True
    while True:
        try:
            for base, otc, reali in ALL:
                now=datetime.now(ITALY_TZ)
                sec=(5-now.minute%5)*60-now.second
                if not 15 <= sec <= 120: continue
                res = check_3_pilastri_contrario(base)
                if not res: continue
                direction, perc, motivo = res
                for label in [otc, reali]:
                    key=f"{label}_{direction}_CONTR"
                    if key in LAST and time.time()-LAST[key]<400: continue
                    msg=f"🔄 *PINBAR CONTRARIO*\n{label}\n{'🟢 BUY 5M' if direction=='BUY' else '🔴 SELL 5M'}\nWick {perc}% | {motivo}\n⏰ {now.strftime('%H:%M:%S')} ITALIA"
                    send(msg); LAST[key]=time.time()
                time.sleep(0.8)
            time.sleep(3)
        except Exception as e:
            print(e); time.sleep(5)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
