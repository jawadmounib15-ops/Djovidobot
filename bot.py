import os, time, requests, yfinance as yf, pandas as pd, numpy as np
from threading import Thread
from flask import Flask
from datetime import datetime
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VERSION = "V37.0 7 LAVORI COMPLETO - basato su V36.8"
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "EURGBP=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X"]

app = Flask(__name__)
@app.route("/")
def home(): return f"{VERSION} LIVE - {datetime.now().strftime('%H:%M:%S')}"

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        print(f"TG: {msg[:40]}")
    except Exception as e: print(f"Err TG: {e}")

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_data(symbol):
    try:
        df = yf.download(symbol, period="2d", interval="5m", progress=False, auto_adjust=True)
        if df.empty or len(df) < 60: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        close = pd.to_numeric(df['Close'], errors='coerce').dropna()
        high = pd.to_numeric(df['High'], errors='coerce').dropna()
        low = pd.to_numeric(df['Low'], errors='coerce').dropna()
        
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        ema5 = close.ewm(span=5, adjust=False).mean()
        sma50 = close.rolling(50).mean()
        rsi = calc_rsi(close)
        
        # Bollinger 20,2
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + 2*bb_std
        bb_lower = bb_mid - 2*bb_std
        
        # Dati ultima candela
        c = float(close.iloc[-1])
        h = float(high.iloc[-1])
        l = float(low.iloc[-1])
        r = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
        e20 = float(ema20.iloc[-1]); e50 = float(ema50.iloc[-1]); e5 = float(ema5.iloc[-1])
        s50 = float(sma50.iloc[-1]) if not pd.isna(sma50.iloc[-1]) else c
        bu = float(bb_upper.iloc[-1]); bl = float(bb_lower.iloc[-1])
        h20 = float(high.rolling(20).max().iloc[-2]); l20 = float(low.rolling(20).min().iloc[-2])
        
        # === 7 LAVORI LOGICA ===
        lavoro = None; side = None
        
        # L1 TREND
        if e20 > e50 and r > 50 and r < 65 and c > e20:
            side="BUY"; lavoro="L1 TREND"
        elif e20 < e50 and r < 50 and r > 35 and c < e20:
            side="SELL"; lavoro="L1 TREND"
        # L2 RIMBALZO - IL TUO V36.8 STRETTO
        if not lavoro:
            if c <= bl and r <= 32: side="BUY"; lavoro="L2 RIMBALZO 32/68"
            elif c >= bu and r >= 68: side="SELL"; lavoro="L2 RIMBALZO 32/68"
        # L4 PULLBACK - torna su SMA50
        if not lavoro:
            if c > s50 and close.iloc[-2] < s50 and e20 > e50: side="BUY"; lavoro="L4 PULLBACK"
            elif c < s50 and close.iloc[-2] > s50 and e20 < e50: side="SELL"; lavoro="L4 PULLBACK"
        # L7 SUPPORTO - minimo/massimo giorno
        if not lavoro:
            day_low = float(low.tail(288).min()); day_high = float(high.tail(288).max())
            if c <= day_low*1.0005 and r <= 35: side="BUY"; lavoro="L7 SUPPORTO"
            elif c >= day_high*0.9995 and r >= 65: side="SELL"; lavoro="L7 SUPPORTO"
        # L3 BREAKOUT
        if not lavoro:
            if c > h20: side="BUY"; lavoro="L3 BREAKOUT"
            elif c < l20: side="SELL"; lavoro="L3 BREAKOUT"
        # L6 CROSS - EMA5 incrocia EMA20
        if not lavoro:
            if e5 > e20 and ema5.iloc[-2] <= ema20.iloc[-2] and e20 > e50: side="BUY"; lavoro="L6 CROSS"
            elif e5 < e20 and ema5.iloc[-2] >= ema20.iloc[-2] and e20 < e50: side="SELL"; lavoro="L6 CROSS"
        # L5 DOPPIO - semplificato pivot
        if not lavoro:
            if l <= low.rolling(20).min().iloc[-1] and r <= 38: side="BUY"; lavoro="L5 DOPPIO"
            elif h >= high.rolling(20).max().iloc[-1] and r >= 62: side="SELL"; lavoro="L5 DOPPIO"

        if lavoro:
            return {"price":c, "rsi":r, "ema20":e20, "ema50":e50, "side":side, "lavoro":lavoro}
        return {"price":c, "rsi":r, "ema20":e20, "ema50":e50, "side":None, "lavoro":None}
    except Exception as e:
        print(f"Errore {symbol}: {e}"); return None

def bot_loop():
    time.sleep(5)
    send_tg(f"✅ *{VERSION} LIVE* 🟢\n7 LAVORI ATTIVI\nL1 TREND | L2 RIMBALZO 32/68 | L3 BREAKOUT | L4 PULLBACK | L5 DOPPIO | L6 CROSS | L7 SUPPORTO\nScansione ogni 2 min")
    print(f"{VERSION} AVVIATO")
    while True:
        try:
            for sym in SYMBOLS:
                data = get_data(sym)
                if not data: continue
                nome = sym.replace("=X","").replace("EURUSD","EUR/USD").replace("GBPUSD","GBP/USD").replace("EURGBP","EUR/GBP").replace("USDJPY","USD/JPY").replace("AUDUSD","AUD/USD")
                if data['side']:
                    msg = f"{'🟢' if data['side']=='BUY' else '🔻'} *{data['side']} {nome} - {data['lavoro']}*\nRSI: {data['rsi']:.1f}\nPrezzo: {data['price']:.5f}\nEMA20 {'>' if data['ema20']>data['ema50'] else '<'} EMA50"
                    send_tg(msg)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {nome} RSI:{data['rsi']:.1f} {data['lavoro'] or 'ATTESA'}")
                time.sleep(2)
        except Exception as e: print(f"Errore loop: {e}"); time.sleep(10)
        print("--- Scan OK V37 7 LAVORI attendo 2m ---")
        time.sleep(120)

Thread(target=bot_loop, daemon=True).start()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
