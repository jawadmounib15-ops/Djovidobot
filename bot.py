# bot.py - MEDIO STRETTO TREND + CONTRARIO
import os, time, requests, yfinance as yf
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "MEDIO CONTRARIO OK"

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
        df['EMA21']=c.ewm(21).mean()
        df['EMA50']=c.ewm(50).mean()
        return df
    except: return None

def check_medio_contrario(y):
    df5 = get_df(y,"5m","5d")
    df15 = get_df(y,"15m","10d")
    if df5 is None or df15 is None: return None

    c = df5.iloc[-1]; o=float(c['Open']); cc=float(c['Close']); h=float(c['High']); l=float(c['Low'])
    body=abs(cc-o); rng=h-l
    if rng==0: return None
    upper = h - max(o,cc)
    lower = min(o,cc) - l
    wick = max(upper, lower)
    nose = min(upper, lower)

    # --- MEDIO STRETTO ---
    if wick < rng*0.60: return None # medio: 60%
    if body > rng*0.32: return None # medio: 32%
    if nose > rng*0.20: return None # medio: 20%
    if wick < body*2.0: return None

    # --- SOLO TREND MEDIO STRETTO ---
    ema21_5 = float(df5['EMA21'].iloc[-1])
    ema50_5 = float(df5['EMA50'].iloc[-1])
    ema21_15 = float(df15['EMA21'].iloc[-1])
    ema50_15 = float(df15['EMA50'].iloc[-1])

    # Trend deve essere chiaro su 5m + 15m (medio stretto)
    trend_up = ema21_5 > ema50_5 and ema21_15 > ema50_15 and cc > ema21_5
    trend_down = ema21_5 < ema50_5 and ema21_15 < ema50_15 and cc < ema21_5

    if not (trend_up or trend_down): return None

    # --- ROVINATO: TUTTO AL CONTRARIO ---
    # Se trend UP + pinbar BULLISH (lower wick) = dovrebbe essere BUY, noi diamo SELL
    # Se trend DOWN + pinbar BEARISH (upper wick) = dovrebbe essere SELL, noi diamo BUY

    if lower == wick and trend_up:
        return "SELL", int((wick/rng)*100), f"TREND UP FORTE MA CONTRARIO SELL"

    if upper == wick and trend_down:
        return "BUY", int((wick/rng)*100), f"TREND DOWN FORTE MA CONTRARIO BUY"

    return None

def bot_loop():
    global AVVIO
    if not AVVIO:
        send(f"⚠️ *MEDIO STRETTO CONTRARIO*\nTrend 5m+15m filtrato\nWick>60% Body<32%\nTUTTI I SEGNALI INVERTITI\n{datetime.now(ITALY_TZ).strftime('%H:%M:%S')} ITALIA")
        AVVIO=True
    while True:
        try:
            for base, otc, reali in ALL:
                now=datetime.now(ITALY_TZ)
                sec=(5-now.minute%5)*60-now.second
                if not 15 <= sec <= 110: continue

                res = check_medio_contrario(base)
                if not res: continue
                direction, perc, motivo = res

                for label in [otc, reali]:
                    key=f"{label}_{direction}_MEDCONT"
                    if key in LAST and time.time()-LAST[key]<300: continue

                    msg=f"🔄 *MEDIO CONTRARIO*\n{label}\n{'🟢 BUY 5M' if direction=='BUY' else '🔴 SELL 5M'}\nWick {perc}% | {motivo}\n⏰ {now.strftime('%H:%M:%S')} ITALIA"
                    send(msg); LAST[key]=time.time()
                time.sleep(0.7)
            time.sleep(3)
        except Exception as e:
            print(e); time.sleep(5)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
