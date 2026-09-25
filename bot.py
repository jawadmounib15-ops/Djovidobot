# Aggiungi questa funzione per test
def process(pair, period, label):
    try:
        key=f"{pair}_{label}"
        if key in sent and time.time()-sent[key]<180: return
        candles=get_candles(pair, period)
        # DEBUG: se non arrivano candele manda alert
        if not candles:
            if pair=="EURUSD" and label=="M5": # solo 1 per non spammare
                send_tg(f"⚠️ DEBUG {pair} {label}: 0 candele! SSID scaduto?")
            return
        # DEBUG: ogni tanto manda stato
        sm={"M5":"5 MINUTI","M15":"15 MINUTI","H1":"1 ORA","H4":"4 ORE"}
        scad=sm.get(label,label)
        tf_text=f"⏰ *TIMEFRAME: {label} ({scad})*"
        #... resto uguale
