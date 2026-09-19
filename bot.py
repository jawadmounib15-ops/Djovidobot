import os, requests, time, yfinance as yf, pandas as pd
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")
PAIRS = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "EURJPY=X": "EUR/JPY", "GBPJPY=X": "GBP/JPY"}

def send(m):
    try:
        if TOKEN and CHAT:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT, "text": m}, timeout=10)
    except:
        pass

def get_data(sym, interval, period):
    try:
        df = yf.download(sym, interval=interval, period=period, progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return pd.DataFrame()

def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def sma(s, n): return s.rolling(n).mean()
def rsi_calc(s, n=14):
    d = s.diff()
    g = d.where(d > 0, 0).rolling(n).mean()
    l = -d.where(d < 0, 0).rolling(n).mean()
    return 100 - (100 / (1 + g / l))

def format_msg(tipo, coppia, lavoro, motivo, prezzo):
    now = datetime.now()
    expiry = now + timedelta(minutes=5)
    icon = "🟢" if tipo=="BUY" else "🔴"
    return f"""{icon} SEGNALE {tipo} - {coppia}
💰 Prezzo: {prezzo:.5f}
⏱️ Scadenza: 5 MINUTI
🕐 Entrata: {now.strftime('%H:%M:%S')}
📅 Scadenza alle: {expiry.strftime('%H:%M:%S')}
🧠 Lavoro: {lavoro}
📊 Motivo: {motivo}
⚡️ Azione: Entra subito in {tipo}"""

def check(sym, name):
    df_h1 = get_data(sym, "60m", "10d")
    df_m15 = get_data(sym, "15m", "5d")
    df_m5 = get_data(sym, "5m", "3d")
    df_m1 = get_data(sym, "1m", "2d")
    if len(df_m15) < 50 or len(df_m1) < 30: return []
    res = []
    c1 = float(df_m1["Close"].iloc[-1])
    o1 = float(df_m1["Open"].iloc[-1])
    l1 = float(df_m1["Low"].iloc[-1])
    h1 = float(df_m1["High"].iloc[-1])
    c_prev = float(df_m1["Close"].iloc[-2])
    o_prev = float(df_m1["Open"].iloc[-2])
    r1 = float(rsi_calc(df_m1["Close"]).iloc[-1])
    r_prev = float(rsi_calc(df_m1["Close"]).iloc[-2])
    e5_15 = float(ema(df_m15["Close"], 5).iloc[-1])
    e20_15 = float(ema(df_m15["Close"], 20).iloc[-1])
    e50_15 = float(ema(df_m15["Close"], 50).iloc[-1])
    s50_15 = float(sma(df_m15["Close"], 50).iloc[-1])
    e5_1 = float(ema(df_m1["Close"], 5).iloc[-1])
    e20_1 = float(ema(df_m1["Close"], 20).iloc[-1])
    e5_1_prev = float(ema(df_m1["Close"], 5).iloc[-2])
    e20_1_prev = float(ema(df_m1["Close"], 20).iloc[-2])
    body = abs(c1 - o1)
    lo = min(o1, c1) - l1
    up = h1 - max(o1, c1)
    pin_buy = lo > body * 1.5
    pin_sell = up > body * 1.5
    eng_buy = c1 > o1 and c_prev < o_prev
    eng_sell = c1 < o1 and c_prev > o_prev
    ma20 = sma(df_m1["Close"], 20)
    std20 = df_m1["Close"].rolling(20).std()
    upper = float((ma20 + 2 * std20).iloc[-1])
    lower = float((ma20 - 2 * std20).iloc[-1])
    high20 = float(df_m5["High"].rolling(20).max().iloc[-2])
    low20 = float(df_m5["Low"].rolling(20).min().iloc[-2])
    daily_low = float(df_h1["Low"].rolling(24).min().iloc[-1])
    daily_high = float(df_h1["High"].rolling(24).max().iloc[-1])
    low_ago = float(df_m1["Low"].rolling(10).min().iloc[-11])
    high_ago = float(df_m1["High"].rolling(10).max().iloc[-11])

    if e5_15 > e20_15 > e50_15 and pin_buy:
        res.append(format_msg("BUY", name, "L1 TREND", "3 EMA allineate UP + Pinbar rialzista", c1))
    if e5_15 < e20_15 < e50_15 and pin_sell:
        res.append(format_msg("SELL", name, "L1 TREND", "3 EMA allineate DOWN + Pinbar ribassista", c1))
    if r_prev < 30 and r1 > 30 and l1 <= lower * 1.002:
        res.append(format_msg("BUY", name, "L2 RIMBALZO", "RSI esce da 30 + tocco Bollinger inferiore", c1))
    if r_prev > 70 and r1 < 70 and h1 >= upper * 0.998:
        res.append(format_msg("SELL", name, "L2 RIMBALZO", "RSI esce da 70 + tocco Bollinger superiore", c1))
    if c1 > high20:
        res.append(format_msg("BUY", name, "L3 BREAKOUT", f"Rottura massimo 20 candele {high20:.5f}", c1))
    if c1 < low20:
        res.append(format_msg("SELL", name, "L3 BREAKOUT", f"Rottura minimo 20 candele {low20:.5f}", c1))
    if abs(c1 - s50_15) / c1 < 0.002 and eng_buy and e5_15 > e20_15:
        res.append(format_msg("BUY", name, "L4 PULLBACK", "Ritorno su SMA50 + Engulfing rialzista", c1))
    if abs(c1 - s50_15) / c1 < 0.002 and eng_sell and e5_15 < e20_15:
        res.append(format_msg("SELL", name, "L4 PULLBACK", "Ritorno su SMA50 + Engulfing ribassista", c1))
    if abs(low_ago - l1) / l1 < 0.001 and c1 > o1 and r1 > r_prev:
        res.append(format_msg("BUY", name, "L5 DOPPIO MIN", "Doppio minimo + RSI in risalita", c1))
    if abs(high_ago - h1) / h1 < 0.001 and c1 < o1 and r1 < r_prev:
        res.append(format_msg("SELL", name, "L5 DOPPIO MAX", "Doppio massimo + RSI in discesa", c1))
    if e5_1 > e20_1 and e5_1_prev < e20_1_prev and r1 > 45:
        res.append(format_msg("BUY", name, "L6 CROSS", "Incrocio medie M1 UP + RSI >45", c1))
    if e5_1 < e20_1 and e5_1_prev > e20_1_prev and r1 < 55:
        res.append(format_msg("SELL", name, "L6 CROSS", "Incrocio medie M1 DOWN + RSI <55", c1))
    if abs(c1 - daily_low) / c1 < 0.001 and (pin_buy or eng_buy):
        res.append(format_msg("BUY", name, "L7 SUPPORTO", f"Supporto giornaliero {daily_low:.5f}", c1))
    if abs(c1 - daily_high) / c1 < 0.001 and (pin_sell or eng_sell):
        res.append(format_msg("SELL", name, "L7 RESISTENZA", f"Resistenza giornaliera {daily_high:.5f}", c1))
    return res

def loop():
    send("✅ V31 ULTIMATE LIVE - 7 LAVORI + MESSAGGIO DETTAGLIATO")
    while True:
        try:
            for k, v in PAIRS.items():
                for s in check(k, v):
                    send(s)
                    time.sleep(20)
            time.sleep(75)
        except Exception as e:
            print(e)
            time.sleep(60)

@app.route("/")
def home(): return "V31 LIVE - 7 LAVORI DETTAGLIATI"

Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
