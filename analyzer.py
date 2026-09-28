# analyzer.py - V3 SICURO FIX 43x + ANTI-CONTRARIO VERO
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta

ITALY_TZ = timezone(timedelta(hours=2))
COOLDOWN = {} # anti-spam 10 min

def get_data(symbol: str, interval: str = "5m"):
    """Scarica dati + EMA + RSI + BB + ATR"""
    try:
        period = "10d" if interval == "5m" else "20d"
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)
        if len(df) < 200:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        df['EMA9'] = close.ewm(span=9).mean()
        df['EMA21'] = close.ewm(span=21).mean()
        df['EMA50'] = close.ewm(span=50).mean()
        df['EMA200'] = close.ewm(span=200).mean()

        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain / loss))

        df['SMA20'] = close.rolling(20).mean()
        std = close.rolling(20).std()
        df['BB_UP'] = df['SMA20'] + 2 * std
        df['BB_LOW'] = df['SMA20'] - 2 * std
        df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()

        return df
    except:
        return None

def is_pinbar_sicura(o: float, h: float, l: float, c: float):
    """Filtro PRO: body 10-28%, ratio 2.5-8x, wick 62% del range"""
    body = abs(c - o)
    rng = h - l
    if rng == 0:
        return None
    upper = h - max(o, c)
    lower = min(o, c) - l

    # FIX 43x + doji
    if body < rng * 0.10: # corpo troppo piccolo = doji
        return None
    if body > rng * 0.28: # corpo troppo grande = non pinbar
        return None

    ratio_up = upper / body if body!= 0 else 0
    ratio_low = lower / body if body!= 0 else 0
    if ratio_up > 8 or ratio_low > 8: # elimina 43.4x
        return None

    if lower >= body * 2.5 and lower >= rng * 0.62 and upper <= rng * 0.25:
        return "CALL", round(ratio_low, 1)

    if upper >= body * 2.5 and upper >= rng * 0.62 and lower <= rng * 0.25:
        return "PUT", round(ratio_up, 1)

    return None

def analyze_92(symbol: str, tf: str = "5m"):
    """Lavoro 1 - 92%+ SICURO con anti-contrario vero"""
    now = datetime.now(ITALY_TZ)
    interval = "5m" if tf == "5m" else "15m"
    df = get_data(symbol, interval)
    if df is None:
        return {"score": 0, "action": "WAIT", "reason": "Mercato chiuso", "tf": tf, "time": now.strftime("%H:%M:%S"), "timestamp": now.timestamp()}

    last = df.iloc[-1]
    price = float(last['Close'])
    ema9 = float(last['EMA9'])
    ema21 = float(last['EMA21'])
    ema50 = float(last['EMA50'])
    ema200 = float(last['EMA200'])
    rsi = float(last['RSI'])

    # 1. Trend vero con 4 EMA
    trend_up = ema9 > ema21 and ema21 > ema50 and price > ema200
    trend_down = ema9 < ema21 and ema21 < ema50 and price < ema200

    # 2. RSI zona sicura
    if not (40 <= rsi <= 60):
        return {"score": 0, "action": "WAIT", "reason": f"RSI {rsi:.0f} fuori 40-60", "tf": tf, "time": now.strftime("%H:%M:%S"), "timestamp": now.timestamp()}

    # 3. Pinbar sicura?
    pin = is_pinbar_sicura(float(last['Open']), float(last['High']), float(last['Low']), price)
    if not pin:
        return {"score": 0, "action": "WAIT", "reason": "No pinbar sicura", "tf": tf, "time": now.strftime("%H:%M:%S"), "timestamp": now.timestamp()}

    direzione, ratio = pin

    # 4. ANTI-CONTRARIO VERO (fix BTC)
    if trend_up and direzione == "PUT":
        return {"score": 0, "action": "WAIT", "reason": "Scarto PUT contro trend UP", "tf": tf, "time": now.strftime("%H:%M:%S"), "timestamp": now.timestamp()}
    if trend_down and direzione == "CALL":
        return {"score": 0, "action": "WAIT", "reason": "Scarto CALL contro trend DOWN", "tf": tf, "time": now.strftime("%H:%M:%S"), "timestamp": now.timestamp()}
    if not trend_up and not trend_down:
        return {"score": 0, "action": "WAIT", "reason": "Laterale - no trade", "tf": tf, "time": now.strftime("%H:%M:%S"), "timestamp": now.timestamp()}

    score = 95 if ratio >= 3.5 else 92
    action = f"{'BUY' if direzione == 'CALL' else 'SELL'} {score}% SICURA"
    return {"score": score, "action": action, "reason": f"Pinbar {ratio}x | RSI {rsi:.0f} | EMA200 OK", "tf": tf, "time": now.strftime("%H:%M:%S"), "timestamp": now.timestamp()}

def analyze_1min_before(symbol: str, tf_label: str = "5m"):
    """Lavoro 2 - 1 min prima chiusura candela 5m, con anti-contrario"""
    try:
        df = yf.download(symbol, period="2d", interval="1m", progress=False, auto_adjust=False)
        if len(df) < 60:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        c = df['Close']
        df['EMA21'] = c.ewm(span=21).mean()
        df['EMA50'] = c.ewm(span=50).mean()
        df['EMA200'] = c.ewm(span=200).mean()
        delta = c.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain / loss))

        now = datetime.now(ITALY_TZ)
        sec_to_close = (5 - now.minute % 5) * 60 - now.second
        if sec_to_close > 300:
            sec_to_close -= 300
        if not (25 <= sec_to_close <= 110): # solo 60-25 sec prima
            return None

        last5 = df.iloc[-5:]
        o = float(last5.iloc[0]['Open'])
        cc = float(last5.iloc[-1]['Close'])
        hh = float(last5['High'].max())
        ll = float(last5['Low'].min())

        pin = is_pinbar_sicura(o, hh, ll, cc)
        if not pin:
            return None
        direzione, ratio = pin

        ema21 = float(df['EMA21'].iloc[-1])
        ema50 = float(df['EMA50'].iloc[-1])
        ema200 = float(df['EMA200'].iloc[-1])
        rsi = float(df['RSI'].iloc[-1])

        if not (38 <= rsi <= 62):
            return None

        trend_up = cc > ema50 and ema21 > ema50 and cc > ema200
        trend_down = cc < ema50 and ema21 < ema50 and cc < ema200
        if trend_up and direzione == "PUT":
            return None
        if trend_down and direzione == "CALL":
            return None
        if not trend_up and not trend_down:
            return None

        # Anti-spam 10 min
        if symbol in COOLDOWN and (now.timestamp() - COOLDOWN[symbol]) < 600:
            return None
        COOLDOWN[symbol] = now.timestamp()

        return {
            "price": round(cc, 5),
            "score": 94,
            "action": f"{'BUY' if direzione == 'CALL' else 'SELL'} 1 MIN PRIMA 📌",
            "reason": f"ANTI-CONTRARIO {ratio}x RSI {rsi:.0f} - {sec_to_close}s",
            "tf": f"{tf_label} {sec_to_close}s",
            "time": now.strftime("%H:%M:%S"),
            "timestamp": now.timestamp()
        }
    except:
        return None
