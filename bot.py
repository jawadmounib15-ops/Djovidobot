import time
import yfinance as yf
import pandas as pd

# CONFIGURAZIONE
COPPIE = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X"]
TELEGRAM_TOKEN = "METTI QUI IL TUO TOKEN"
TELEGRAM_CHAT_ID = "METTI QUI IL TUO CHAT ID"

# REGOLE V12 75% - PIU' LARGHE!
ENGULFING_RATIO = 0.75  # Prima era 0.80, adesso 75%!
EMA_FAST = 50
EMA_SLOW = 200
RSI_MIN = 30
RSI_MAX = 70

def lavoro1_trend(df):
    # Guarda EMA 50 e 200
    ema50 = df['Close'].ewm(span=EMA_FAST).mean().iloc[-1]
    ema200 = df['Close'].ewm(span=EMA_SLOW).mean().iloc[-1]
    if ema50 > ema200:
        return "BUY"
    else:
        return "SELL"

def lavoro2_engulfing(df):
    # Guarda candela grossa 75% (prima era 80%)
    ultima = df.iloc[-1]
    precedente = df.iloc[-2]
    
    corpo_ultima = abs(ultima['Close'] - ultima['Open'])
    corpo_prec = abs(precedente['Close'] - precedente['Open'])
    
    if corpo_prec == 0:
        return None
    
    rapporto = corpo_ultima / corpo_prec
    
    if rapporto >= ENGULFING_RATIO:
        if ultima['Close'] > ultima['Open']:
            return "BUY"
        else:
            return "SELL"
    return None

def lavoro3_sicuro(trend, engulfing):
    # Se tutti e due dicono uguale = SICURO 75%!
    if trend == engulfing and engulfing is not None:
        return True
    return False

# LOOP PRINCIPALE
print("V12 75% AVVIATO - 3 LAVORI - ASPETTO SEGNALI...")

while True:
    for coppia in COPPIE:
        try:
            df = yf.download(coppia, period="2d", interval="15m", progress=False)
            if len(df) < 200:
                continue
            
            # 3 LAVORI
            trend = lavoro1_trend(df)
            engulf = lavoro2_engulfing(df)
            sicuro = lavoro3_sicuro(trend, engulf)
            
            if sicuro:
                print(f"🟢 SEGNALE SICURO 75% - {coppia} - {trend} - 3 LAVORI OK!")
                # Qui manda telegram
            elif engulf:
                print(f"🟡 SEGNALE 75% - {coppia} - {engulf}")
                
        except Exception as e:
            print(f"Errore {coppia}: {e}")
    
    print("Controllo finito, aspetto 15 min...")
    time.sleep(900)  # 15 minuti
