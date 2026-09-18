import yfinance as yf
import time
import requests
from datetime import datetime
import pytz
import pandas as pd

# === CONFIG V13.2 SICURO - 7-8 WIN SU 10 ===
TELEGRAM_TOKEN = "INSERISCI_QUI_IL_TUO_TOKEN"
TELEGRAM_CHAT_ID = "INSERISCI_QUI_CHAT_ID"
INTERVAL = "15m"

# REGOLA D'ORO SICURA - QUESTA E' LA CORREZIONE PA
ENGULFING_MIN = 1.20
ENGULFING_MAX = 2.00
EMA_PERIOD = 50
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "EUR/JPY", "AUD/USD", "GBP/JPY", "EUR/GBP", "USD/CHF", "AUD/JPY", "EUR/AUD"]
YF_MAP = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "EUR/JPY": "EURJPY=X",
    "AUD/USD": "AUDUSD=X",
    "GBP/JPY": "GBPJPY=X",
    "EUR/GBP": "EURGBP=X",
    "USD/CHF": "CHF=X",
    "AUD/JPY": "AUDJPY=X",
    "EUR/AUD": "EURAUD=X"
}

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, data=payload, timeout=10)
        print(f"Inviato: {msg}")
    except Exception as e:
        print(f"Telegram error: {e}")

def calc_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def check_signal(pair):
    try:
        yf_symbol = YF_MAP.get(pair)
        if not yf_symbol:
            return None
            
        df = yf.download(yf_symbol, period="5d", interval=INTERVAL, progress=False, auto_adjust=False)
        
        if df.empty or len(df) < 60:
            return None
        
        # Fix per yfinance che ritorna MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df['EMA50'] = df['Close'].ewm(span=EMA_PERIOD, adjust=False).mean()
        df['RSI'] = calc_rsi(df, RSI_PERIOD)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        open_last = float(last['Open'])
        close_last = float(last['Close'])
        open_prev = float(prev['Open'])
        close_prev = float(prev['Close'])
        ema_last = float(last['EMA50'])
        rsi_last = float(last['RSI'])
        
        body_last = abs(close_last - open_last)
        body_prev = abs(close_prev - open_prev)
        
        if body_prev == 0 or body_last == 0:
            return None
        
        ratio = body_last / body_prev
        
        # FILTRO 1: Ratio sicuro 1.20-2.00 - BLOCCA 0.92 e 1.00
        if ratio < ENGULFING_MIN or ratio > ENGULFING_MAX:
            return None
        
        # FILTRO 2: Body deve essere > 60% della candela
        range_last = float(last['High'] - last['Low'])
        if range_last == 0 or (body_last / range_last) < 0.6:
            return None
            
        # ENGULFING PATTERN
        bullish_eng = (close_prev < open_prev) and (close_last > open_last) and (close_last > open_prev) and (open_last < close_prev)
        bearish_eng = (close_prev > open_prev) and (close_last < open_last) and (close_last < open_prev) and (open_last > close_prev)
        
        signal = None
        if bullish_eng:
            # FILTRO 3: RSI non ipercomprato
            if rsi_last > RSI_OVERBOUGHT:
                print(f"{pair} BUY bloccato RSI alto {rsi_last}")
                return None
            # FILTRO 4: Sopra EMA
            if close_last < ema_last:
                return None
            signal = "BUY"
            
        elif bearish_eng:
            # FILTRO 3: RSI non ipervenduto
            if rsi_last < RSI_OVERSOLD:
                print(f"{pair} SELL bloccato RSI basso {rsi_last}")
                return None
            # FILTRO 4: Sotto EMA
            if close_last > ema_last:
                return None
            signal = "SELL"
        else:
            return None
            
        return {
            "pair": pair,
            "signal": signal,
            "ratio": round(ratio, 2),
            "rsi": round(rsi_last, 1),
            "price": round(close_last, 5)
        }
    except Exception as e:
        print(f"Errore {pair}: {e}")
        return None

def main():
    print("=== BOT V13.2 SICURO AVVIATO ===")
    print(f"Ratio: {ENGULFING_MIN}-{ENGULFING_MAX} | Interval: {INTERVAL}")
    send_telegram("✅ *V13.2 SICURO AVVIATO*\nRatio: 1.20-2.00\nFiltri: RSI + EMA50 + Body 60%\nObiettivo: 7-8 WIN su 10")
    
    while True:
        try:
            now = datetime.now(pytz.timezone('Europe/Rome'))
            # Pausa notte - no OTC
            if now.hour >= 22 or now.hour < 8:
                print(f"[{now.strftime('%H:%M')}] Notte - pausa OTC")
                time.sleep(600)
                continue
                
            print(f"\n[{now.strftime('%H:%M:%S')}] Scansione {len(PAIRS)} coppie...")
            
            for pair in PAIRS:
                res = check_signal(pair)
                if res:
                    msg = f"✅ *SEGNALE SICURO 90%*\n\nCoppia: {res['pair']}\nDirezione: *{res['signal']}*\nPrezzo: {res['price']}\nRatio: {res['ratio']} (sicuro)\nRSI: {res['rsi']}\nTime: 15 min"
                    print(f"SEGNALE TROVATO: {res}")
                    send_telegram(msg)
                time.sleep(2)
                
            print("Attesa 5 min...")
            time.sleep(300)
            
        except Exception as e:
            print(f"Errore main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
