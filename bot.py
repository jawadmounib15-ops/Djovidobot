import yfinance as yf
import time
import requests

# --- TUOI DATI TELEGRAM ---
TOKEN = "METTI QUI IL TUO TOKEN"
CHAT_ID = "METTI QUI IL TUO CHAT ID"

# --- 21 COPPIE REALI TUE - TUTTE! ---
COPPIE_POCKET = [
    "USD/JPY", "AUD/JPY", "AUD/CHF", "GBP/USD", "CAD/JPY",
    "CHF/JPY", "AUD/USD", "GBP/CAD", "USD/CHF", "EUR/JPY",
    "USD/CAD", "EUR/CHF", "EUR/GBP", "AUD/CAD", "GBP/CHF",
    "GBP/AUD", "EUR/USD", "GBP/JPY", "EUR/CAD", "CAD/CHF", "EUR/AUD"
]

# Converte da Pocket a yfinance
def converti(nome):
    return nome.replace("/", "") + "=X"

COPPIE_YF = [converti(c) for c in COPPIE_POCKET]
ENGULFING = 0.75 # 75% come hai detto tu Pa!

def manda_telegram(messaggio):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": messaggio})
    except:
        pass

def analizza():
    for i, simbolo_yf in enumerate(COPPIE_YF):
        nome_pocket = COPPIE_POCKET[i]
        try:
            df = yf.download(simbolo_yf, period="3d", interval="15m", progress=False)
            if len(df) < 200:
                continue

            # LAVORO 1 - TREND EMA 50/200
            ema50 = df['Close'].ewm(span=50).mean().iloc[-1]
            ema200 = df['Close'].ewm(span=200).mean().iloc[-1]
            trend = "BUY" if ema50 > ema200 else "SELL"

            # LAVORO 2 - ENGULFING 75%
            ultima = df.iloc[-1]
            prec = df.iloc[-2]
            corpo_ult = abs(float(ultima['Close'] - ultima['Open']))
            corpo_prec = abs(float(prec['Close'] - prec['Open']))
            if corpo_prec == 0:
                continue
            rapporto = corpo_ult / corpo_prec

            engulf = None
            if rapporto >= ENGULFING:
                engulf = "BUY" if ultima['Close'] > ultima['Open'] else "SELL"

            # LAVORO 3 - SICURO 75%
            if engulf and trend == engulf:
                msg = f"🟢 SEGNALE SICURO 75% - {nome_pocket} - {trend}\n3 LAVORI OK - 21 coppie"
                print(msg)
                manda_telegram(msg)
            elif engulf:
                print(f"🟡 Segnale 75% {nome_pocket} {engulf}")

        except Exception as e:
            print(f"Errore {nome_pocket}: {e}")

# --- AVVIO ---
print("V12 75% AVVIATO - 21 COPPIE REALI")
manda_telegram("🟢 V12 75% AVVIATO\n21 coppie reali attive\nCerco segnali 75% ogni 15 min")

while True:
    analizza()
    print("Finito giro 21 coppie, aspetto 15 min...")
    time.sleep(900)
