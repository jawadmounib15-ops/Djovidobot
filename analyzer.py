# analyzer.py - PINBAR PERFETTA + RSI + EMA come nelle tue foto
import pandas as pd

def rsi_calc(series, period=14):
    delta = series.diff()
    gain = delta.where(delta>0, 0).rolling(period).mean()
    loss = -delta.where(delta<0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100/(1+rs))

def ema(series, period):
    return series.ewm(span=period).mean()

def is_perfect_pinbar(o, h, l, c, rsi_val=None, price_vs_ema200=None, dist_ema20=None):
    body = abs(c - o)
    rng = h - l
    if rng == 0 or body == 0:
        return None

    up = h - max(o, c)
    low = min(o, c) - l
    close_pos = (c - l) / rng
    body_pct = body / rng

    # 1. Body 5-30% come foto
    if not (0.05 <= body_pct <= 0.30):
        return None

    # 2. Wick 2.8x minimo
    dominant = max(up, low)
    if dominant < body * 2.8:
        return None

    # 3. Wick 55% candela
    if dominant < rng * 0.55:
        return None

    # 4. Wick opposto max 30%
    opposite = min(up, low)
    if opposite > rng * 0.30:
        return None

    # 5. FILTRO RSI come nelle tue foto (non estremo)
    if rsi_val is not None:
        if not (30 <= rsi_val <= 72): # foto era 50-65
            return None

    # 6. FILTRO EMA come nelle foto
    if dist_ema20 is not None:
        if dist_ema20 > 0.012: # max 1.2% da EMA20, altrimenti troppo lontana
            return None

    if up > low: # SHOOTING STAR SELL - come foto 1.88463 e 1.32906
        if close_pos > 0.40:
            return None
        if price_vs_ema200 is not None and price_vs_ema200 < 0:
            # nelle foto era sopra EMA200, ma dopo scarico - permetto ma meglio sopra
            pass
        signal = "SELL"
        ratio = up / body
        return {
            "signal": signal,
            "type": "SHOOTING_STAR",
            "ratio": round(ratio,1),
            "body_pct": round(body_pct*100,1),
            "rsi": round(rsi_val,1) if rsi_val else None,
            "quality": "PERFETTA" if ratio>=3.5 else "BELLISSIMA"
        }
    else: # HAMMER BUY
        if close_pos < 0.60:
            return None
        signal = "BUY"
        ratio = low / body
        return {
            "signal": signal,
            "type": "HAMMER",
            "ratio": round(ratio,1),
            "body_pct": round(body_pct*100,1),
            "rsi": round(rsi_val,1) if rsi_val else None,
            "quality": "PERFETTA" if ratio>=3.5 else "BELLISSIMA"
        }

def analyze(df):
    """Analizza DataFrame con RSI + EMA come nelle foto"""
    signals = []
    if len(df) < 210:
        return signals

    df['RSI'] = rsi_calc(df['Close'])
    df['EMA20'] = ema(df['Close'], 20)
    df['EMA200'] = ema(df['Close'], 200)

    for i in range(200, len(df)):
        o = df['Open'].iloc[i]
        h = df['High'].iloc[i]
        l = df['Low'].iloc[i]
        c = df['Close'].iloc[i]
        rsi_val = float(df['RSI'].iloc[i])

        # distanza da EMA20
        ema20 = float(df['EMA20'].iloc[i])
        dist_ema20 = abs(c - ema20) / c

        # vs EMA200
        ema200 = float(df['EMA200'].iloc[i])
        price_vs_ema200 = c - ema200

        prev_high = df['High'].iloc[i-10:i].max()
        prev_low = df['Low'].iloc[i-10:i].min()

        # deve essere massimo/minimo locale come foto
        if h < prev_high * 0.9995 and l > prev_low * 1.0005:
            continue

        pin = is_perfect_pinbar(o, h, l, c, rsi_val, price_vs_ema200, dist_ema20)
        if pin:
            pin['index'] = i
            pin['time'] = str(df.index[i])
            pin['price'] = float(c)
            pin['ema20_dist'] = round(dist_ema20*100,2)
            signals.append(pin)

    return signals

def scan_last_candle(df):
    """Live - ultima candela con filtri foto"""
    if len(df) < 210:
        return None

    df['RSI'] = rsi_calc(df['Close'])
    df['EMA20'] = ema(df['Close'], 20)
    df['EMA200'] = ema(df['Close'], 200)

    last = df.iloc[-1]
    rsi_val = float(last['RSI'])
    dist_ema20 = abs(float(last['Close']) - float(last['EMA20'])) / float(last['Close'])
    vs_ema200 = float(last['Close']) - float(last['EMA200'])

    return is_perfect_pinbar(
        last['Open'], last['High'], last['Low'], last['Close'],
        rsi_val, vs_ema200, dist_ema20
    )
