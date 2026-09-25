# CAMBIA SOLO QUESTE 2 RIGHE NEL CODICE CHE HAI
def check_pinbar(candles):
    # ...
        # PRIMA ERA 2.2 - ORA METTI 1.8 PER TEST
        if low/body>=1.8 and low>up*1.2 and 20<=r<=40:
            return "BUY", f"PINBAR BUY coda {low/body:.1f}x RSI {r:.0f}"
        if up/body>=1.8 and up>low*1.2 and 60<=r<=80:
            return "SELL", f"PINBAR SELL coda {up/body:.1f}x RSI {r:.0f}"
