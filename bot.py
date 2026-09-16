import yfinance as yf
import pandas as pd
import time
import requests
import os

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = {
    "EURUSD=X": "EURUSD",
    "GBPUSD=X": "GBPUSD", 
    "USDJPY=X": "USDJPY",
    "GBPJPY=X": "GBPJPY",
    "EURJPY=X": "EURJPY",
    "AUDUSD=X": "AUDUSD",
    "GC=F": "GOLD",
    "BTC-USD": "BTCUSD",
    "ETH-USD": "ETHUSD",
    "SI=F": "SILVER",
    "USDCAD=X": "USDCAD",
    "EURGBP=X": "EURGBP"
}

NEAR_SR_PCT = 0.35
RSI_MIN = 30
RSI_MAX = 75
ATR_MIN_PCT = 0.15

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(f"INVIATO: {msg}")
    except Exception as e:
        print(f"Errore Telegram: {e}")

def get_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def is_pin_bar(row):
    body = abs(row['Close'] - row['Open'])
    if body < 0.0001: body = 0.0001
    upper = row['High'] - max(row['Close'], row['Open'])
    lower = min(row['Close'], row['Open']) - row['Low']
    if lower > body * 1.8 and upper < body * 0.8:
        return True, "BUY"
    if upper > body * 1.8 and lower < body * 0.8:
        return True, "SELL"
    return False, None

def is_engulfing(df):
    if len(df) < 2: return False, None
    p = df.iloc[-2]
    c = df.iloc[-1]
    if p['Close'] < p['Open'] and c['Close'] > c['Open'] and c['Close'] > p['Open'] and c['Open'] < p['Close']:
        return True, "BUY"
    if p['Close'] > p['Open'] and c['Close'] < c['Open'] and c['Close'] < p['Open'] and c['Open'] > p['Close']:
        return True, "SELL"
    return False, None

def check_one(ticker, name):
    try:
        df = yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if len(df) < 50:
            return
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['RSI'] = get_rsi(df['Close'])
        df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
        last = df.iloc[-1]
        atr_pct = (last['ATR'] / last['Close']) * 100
        if atr_pct < ATR_MIN_PCT:
            return
        recent_high = df['High'].tail(30).max()
        recent_low = df['Low'].tail(30).min()
        near_sr = abs(last['Close']-recent_high)/last['Close']*100 < NEAR_SR_PCT or abs(last['Close']-recent_low)/last['Close']*100 < NEAR_SR_PCT
        pin_ok, pin_dir = is_pin_bar(last)
        eng_ok, eng_dir = is_engulfing(df)
        if not (pin_ok or eng_ok):
            return
        direction = pin_dir if pin_ok else eng_dir
        pattern = "Pin Bar" if pin_ok else "Engulfing"
        score = 0
        if near_sr: score += 1
        if (direction=="BUY" and last['Close']>last['EMA20']) or (direction=="SELL" and last['Close']<last['EMA20']):
            score += 1
        if RSI_MIN < last['RSI'] < RSI_MAX:
            score += 1
        if score >= 2:
            emoji = "🟢" if direction=="BUY" else "🔴"
            msg = f"{emoji} {direction} {name} {pattern} 15m\nScore {score}/3 RSI {last['RSI']:.0f} | Pocket 30m"
            send_telegram(msg)
    except Exception as e:
        print(f"Err {name}: {e}")

send_telegram("✅ BOT V3.1 AVVIATO - filtri leggeri")
print("BOT V3.1 AVVIATO - filtri leggeri")

while True:
    print("Controllo mercati...")
    for ticker, name in SYMBOLS.items():
        check_one(ticker, name)
        time.sleep(1)
    print("Ciclo finito, dormo 3 min")
    time.sleep(180)
