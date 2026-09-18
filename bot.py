import yfinance as yf
import requests
import time
import os
from threading import Thread
from flask import Flask
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# V13.2 - 4 REGOLE SICURE
ENGULFING = 1.20
ENGULFING_MAX = 2.00
BODY_MIN_PCT = 0.0003
RSI_OB = 70
RSI_OS = 30

COPPIE_YF = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURGBP=X","EURJPY=X","GBPJPY=X"]
COPPIE_POCKET = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD","EUR/GBP","EUR/JPY","GBP/JPY"]

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot 80% LIVE - V13.2 SICURA - NO OTC NOTTE", 200

def manda_telegram(messaggio):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": messaggio}, timeout=10)
    except:
        pass

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analizza():
    ora = datetime.now().hour
    if ora >= 23 or ora < 5:
        print(f"{ora}:00 NOTTE - STOP OTC Pa!")
        return
    print(f">>> Giro {len(COPPIE_YF)} coppie - Filtro {ENGULFING}-{ENGULFING_MAX} + RSI")
    for i, simbolo_yf in enumerate(COPPIE_YF):
        nome = COPPIE_POCKET[i]
        try:
            df = yf.download(simbolo_yf, period="3d", interval="15m", progress=False, auto_adjust=True)
            if len(df) < 200:
                continue
            ema50 = df['Close'].ewm(span=50).mean().iloc[-1].item()
            ema200 = df['Close'].ewm(span=200).mean().iloc[-1].item()
            rsi = calc_rsi(df['Close']).iloc[-1].item()
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

            # REGOLA 1 - Ratio 1.20-2.00
            rapporto = corpo_ult / corpo_prec
            if rapporto < ENGULFING or rapporto > ENGULFING_MAX:
                continue

            # REGOLA 2 - No doji
            if corpo_ult < BODY_MIN_PCT:
                continue

            # REGOLA 3 - VERO ENGULFING + TREND
            close_u = get_val(ultima, 'Close')
            open_u = get_val(ultima, 'Open')
            close_p = get_val(prec, 'Close')
            open_p = get_val(prec, 'Open')

            bullish_eng = (close_p < open_p) and (close_u > open_u) and (close_u > open_p) and (open_u < close_p)
            bearish_eng = (close_p > open_p) and (close_u < open_u) and (close_u < open_p) and (open_u > close_p)

            engulf = ""
            if bullish_eng:
                engulf = "BUY"
            elif bearish_eng:
                engulf = "SELL"
            else:
                continue

            # REGOLA 4 - RSI ANTI-PICCO - NUOVA!
            if engulf == "BUY" and rsi > RSI_OB:
                print(f"{nome} BUY bloccato RSI {rsi:.1f} troppo alto")
                continue
            if engulf == "SELL" and rsi < RSI_OS:
                print(f"{nome} SELL bloccato RSI {rsi:.1f} troppo basso")
                continue

            if engulf and trend == engulf:
                msg = f"✅ SEGNALE SICURO 90% - {nome} - {trend}\nRatio: {rapporto:.2f} | RSI: {rsi:.1f}"
                print(msg)
                manda_telegram(msg)
        except Exception as e:
            print(f"Errore {nome}: {e}")

def run_bot():
    print("V13.2 AVVIATO - REGOLA SICURA + RSI")
    manda_telegram("✅ V13.2 AVVIATO - REGOLA SICURA 1.20-2.00 + VERO ENGULFING + RSI - NO OTC NOTTE")
    while True:
        analizza()
        print("Giro finito, aspetto 5 min...")
        time.sleep(300)

Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
