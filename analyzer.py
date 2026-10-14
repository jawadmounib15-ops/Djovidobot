# Analyzer.py - V21.0 SOLO 30 MIN - NO OTC - BALANCED - FIX 0 SEGNALI
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from curl_cffi import requests as cffi_requests

_YF = cffi_requests.Session(impersonate="chrome", timeout=20)
ITALY = ZoneInfo("Europe/Rome")
SCADENZA = 30
RITRACC = 0.70

# SOLO 10 REALI
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","NZDUSD=X","EURJPY=X","EURGBP=X","EURCAD=X"]

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def rsi(s, p=7):
    d = s.diff()
    g = d.where(d>0,0).rolling(p).mean()
    l = -d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

# QUESTA E' LA FIX - PRIMA ERA TROPPO STRICT
def pinbar_30m_balanced(df):
    if len(df) < 30:
        return None
    c = df.iloc[-2]
    O,H,L,C = float(c['Open']), float(c['High']), float(c['Low']), float(c['Close'])
    total = H - L
    if total <= 0:
        return None

    corpo = abs(O-C)
    inf = min(O,C) - L
    sup = H - max(O,C)

    # FIX: corpo 30% non 20% - così la vede
    if corpo > total * 0.30:
        return None

    # FIX: miccia 60% non 70% - per 30m basta e avanza
    if inf >= total * 0.60 and sup <= total * 0.20:
        return {"dir":"SU", "target": L + (inf * RITRACC), "forza": inf/total*100, "O":O,"H":H,"L":L,"C":C}

    if sup >= total * 0.60 and inf <= total * 0.20:
        return {"dir":"GIÙ", "target": H - (sup * RITRACC), "forza": sup/total*100, "O":O,"H":H,"L":L,"C":C}

    return None

class Analyzer:
    def __init__(self):
        self.cooldown = {}
        self.stats_30m = 0

    def is_mercato_reale(self):
        now = datetime.now(ITALY)
        if now.weekday() >= 5: return False
        if now.hour < 8 or now.hour >= 22: return False
        return True

    def scanna_30m(self):
        """ Chiamato dal tuo bottone SCANNA STRICT """
        risultati = []
        if not self.is_mercato_reale():
            print("Mercato reale chiuso - skip")
            return risultati

        for symbol in PAIRS:
            clean = symbol.replace("=X","")
            if clean in self.cooldown and time.time() - self.cooldown[clean] < 1800:
                continue
            try:
                # FIX CRITICO: 60d per 30m, non 5d - con 5d non trova niente
                df = fix_df(yf.Ticker(symbol, session=_YF).history(period="60d", interval="30m"))
                if len(df) < 30:
                    continue

                df['rsi7'] = rsi(df['Close'], 7)
                last_rsi = float(df['rsi7'].iloc[-2])

                pin = pinbar_30m_balanced(df)
                if not pin:
                    continue

                # FIX: RSI 35/65 non 30/70 - così manda
                if pin["dir"] == "SU" and last_rsi > 35:
                    continue
                if pin["dir"] == "GIÙ" and last_rsi < 65:
                    continue

                self.cooldown[clean] = time.time()
                self.stats_30m += 1

                risultati.append({
                    "asset": clean,
                    "dir": "CALL" if pin["dir"]=="SU" else "PUT",
                    "scadenza": f"{SCADENZA}m",
                    "entry": pin["target"],
                    "forza": pin["forza"],
                    "rsi": last_rsi,
                    "candela": f"O:{pin['O']:.5f} H:{pin['H']:.5f} L:{pin['L']:.5f} C:{pin['C']:.5f}",
                    "ora": datetime.now(ITALY).strftime("%H:%M:%S")
                })
                print(f"[{datetime.now(ITALY).strftime('%H:%M:%S')}] 30m {clean} TROVATO!")

            except Exception as e:
                print(f"Err {clean}: {e}")
                continue

        return risultati

# per compatibilità con la tua app vecchia
def get_analyzer():
    return Analyzer()
