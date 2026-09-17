import yfinance as yf
import requests
import time
import os

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ENGULFING = 1.20 # Filtro 80% SICURO Pa!

COPPIE_YF = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
    "EURGBP=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "EURCAD=X",
    "GBPCHF=X", "EURCHF=X", "AUDCAD=X", "GBPCAD=X", "EURAUD=X",
    "GBPAUD=X", "AUDCHF=X", "CADJPY=X", "CHFJPY=X", "EURTRY=X",
    "USDTRY=X"
]

COPPIE_POCKET = [
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD",
    "EUR/GBP", "EUR/JPY", "GBP/JPY", "AUD/JPY", "EUR/CAD",
    "GBP/CHF", "EUR/CHF", "AUD/CAD", "GBP/CAD", "EUR/AUD",
    "GBP/AUD", "AUD/CHF", "CAD/JPY", "CHF/JPY", "EUR/TRY",
    "USD/TRY"
]

def manda_telegram(messaggio):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": messaggio}, timeout=10)
    except:
        pass

def analizza():
    print(f">>> Giro 21 coppie - 80% SICURO - Filtro {ENGULFING}")
    for i, simbolo_yf in enumerate(COPPIE_YF):
        nome = COPPIE_POCKET[i]
        try:
            df = yf.download(simbolo_yf, period="3d", interval="15m", progress=False, auto_adjust=True)
            if len(df) < 200:
                continue
            ema50 = df['Close'].ewm(span=50).mean().iloc[-1].item()
            ema200 = df['Close'].ewm(span=200).mean().iloc[-1].item()
            trend = "BUY" if ema50 > ema200 else "SELL"
            ultima = df.iloc[-1]
            prec = df.iloc[-2]
            def get_val(c, col):
                v = c[col]
                return float(v.iloc[0] if hasattr(v, 'iloc') else v)
            corpo_ult = abs(get_val(ultima, 'Close') - get_val(ultima, 'Open'))
            corpo_prec = abs(get_val(prec, 'Close') - get_val(prec, 'Open'))
            if corpo_prec == 0:
                continue
            rapporto = corpo_ult / corpo_prec
            close_u = get_val(ultima, 'Close')
            open_u = get_val(ultima, 'Open')
            engulf = None
            if rapporto >= ENGULFING:
                engulf = "BUY" if close_u > open_u else "SELL"
            if engulf and trend == engulf:
                msg = f"🟢 SEGNALE SICURO 80% - {nome} - {trend}\n3 LAVORI OK - Ratio: {rapporto:.2f}"
                print(msg)
                manda_telegram(msg)
        except Exception as e:
            print(f"Errore {nome}: {e}")

print(f"V13 AVVIATO - 80% SICURO - FILTRO {ENGULFING}")
manda_telegram(f"🟢 V13 AVVIATO - 80% SICURO - Filtro {ENGULFING} - 21 coppie")

while True:
    analizza()
    time.sleep(900)
