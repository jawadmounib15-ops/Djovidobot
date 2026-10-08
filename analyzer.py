# Analyzer.py - VERSIONE LARGA - Prende più pinbar
import pandas as pd
import json
import os
from datetime import datetime, timedelta

try:
    import winsound
    def play_sound(): winsound.Beep(800, 400)
except:
    def play_sound(): print("\a [SEGNALE]")

class PinBarAnalyzer:
    def __init__(self, expiry_candles=4, storico_file="storico_segnali.json"):
        self.expiry_candles = expiry_candles
        self.storico_file = storico_file
        self.storico = self.load_storico()

    def load_storico(self):
        if os.path.exists(self.storico_file):
            with open(self.storico_file, 'r') as f:
                try: return json.load(f)
                except: return []
        return []

    def save_storico(self):
        with open(self.storico_file, 'w') as f:
            json.dump(self.storico, f, indent=2)

    # VERSIONE LARGA
    def is_pinbar_larga(self, o, h, l, c):
        body = abs(c - o)
        upper = h - max(c, o)
        lower = min(c, o) - l
        total = h - l
        if total == 0: return None, 0

        # LARGO 1: body può essere fino al 50% del range (prima era 35%)
        if body > (total * 0.50):
            return None, 0

        # LARGO 2: stoppino basta 1.8x il body (prima 2.5x)
        # e 1.5x l'altro stoppino (prima 2x)

        # BULLISH - coda sotto
        if lower > (body * 1.8) and lower > (upper * 1.2):
            # chiusura nel 50% alto (prima 70%)
            if c > (l + total * 0.5):
                score = (lower / total) * 100
                return "BULLISH", round(score, 1)

        # BEARISH - coda sopra
        if upper > (body * 1.8) and upper > (lower * 1.2):
            if c < (l + total * 0.5):
                score = (upper / total) * 100
                return "BEARISH", round(score, 1)

        return None, 0

    def analyze(self, df, pair="EUR/USD"):
        if len(df) < 20: return None

        # ANTI-LAG: sempre penultima candela chiusa
        last = df.iloc[-2]
        o, h, l, c = last['open'], last['high'], last['low'], last['close']

        tipo, score = self.is_pinbar_larga(o, h, l, c)

        if tipo and score >= 55: # SOGLIA LARGA: prima era 65, ora 55 prendi di più
            
            # Filtro RSI MOLTO largo - solo per evitare estremi assurdi
            # lo puoi anche togliere se vuoi ancora più segnali
            # Per ora: 20-80
            try:
                delta = df['close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = -delta.where(delta < 0, 0).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                rsi_val = rsi.iloc[-2]
                if tipo == "BULLISH" and rsi_val > 80: return None
                if tipo == "BEARISH" and rsi_val < 20: return None
            except:
                pass

            entry = last['time'] if 'time' in last else datetime.now()
            expiry = entry + timedelta(minutes=5 * self.expiry_candles) if isinstance(entry, datetime) else datetime.now() + timedelta(minutes=20)

            segnale = {
                "pair": pair,
                "tipo": tipo,
                "score": score,
                "entry_time": str(entry),
                "expiry_time": str(expiry),
                "prezzo": float(c),
                "status": "ATTIVO"
            }

            # evita doppioni
            if not any(s['entry_time'] == str(entry) and s['pair'] == pair for s in self.storico):
                self.storico.append(segnale)
                self.save_storico()
                play_sound()
                print(f"--> {tipo} {pair} | score {score}% | prezzo {c}")
                return segnale
        return None

    def check_scadenza(self):
        now = datetime.now()
        for s in self.storico:
            try:
                exp = datetime.fromisoformat(s['expiry_time'])
                if now > exp and s['status'] == "ATTIVO":
                    s['status'] = "SCADUTO"
            except: pass
        self.save_storico()
