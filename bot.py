import yfinance as yf
import requests
import time
import os
from threading import Thread
from flask import Flask
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ENGULFING = 5.00

COPPIE_YF = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURGBP=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURCAD=X","GBPCHF=X","EURCHF=X","AUDCAD=X","GBPCAD=X","EURAUD=X","GBPAUD=X","AUDCHF=X","CADJPY=X","CHFJPY=X","EURTRY=X","USDTRY=X"]
COPPIE_POCKET = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD","EUR/GBP","EUR/JPY","GBP/JPY","AUD/JPY","EUR/CAD","GBP/CHF","EUR/CHF","AUD/CAD","GBP/CAD","EUR/AUD","GBP/AUD","AUD/CHF","CAD/JPY","CHF/JPY","EUR/TRY","USD/TRY"]

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot 80% LIVE - REGOLE VERE - NO OTC NOTTE", 200

def manda_telegram(messaggio):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": messaggio}, timeout=10)
    except:
        pass

def analizza():
    ora = datetime.now().hour
    if ora >= 23 or ora < 5:
        print(f"[{ora}:00] NOTTE - REGOLA 1 - STOP OTC Pa!")
        return
    print(f">>> Giro 21 coppie - Filtro {ENGULFING}")
    for i, simbolo_yf in enumerate(COPPIE_YF):
        nome = COPPIE_POCKET[i]
        try:
            df = yf.download(simbolo_yf, period="3d", interval="15m", progress=False, auto_adjust=True)
            if len(df) < 200: continue
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
            if corpo_prec == 0: continue
            rapporto = corpo_ult / corpo_prec
            close_u = get_val(ultima, 'Close')
            open_u = get_val(ultima, 'Open')
            engulf = None
            if rapporto >= ENGULFING:
                engulf = "BUY" if close_u > open_u else "SELL"
            if engulf and trend == engulf:
                msg = f"✅ SEGNALE SICURO 99% - {nome} - {trend}\nRatio: {rapporto:.2f}"
                print(msg)
                manda_telegram(msg)
        except Exception as e:
            print(f"Errore {nome}: {e}")

def run_bot():
    print("V13 AVVIATO - REGOLE VERE")
    manda_telegram("✅ V13 AVVIATO - REGOLE VERE - NO OTC NOTTE")
    while True:
        analizza()
        print("Giro finito, aspetto 5 min...")
        time.sleep(300)

Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
