# app/Analyzer.py - V10 SAFE - 10 COPPIE - H1 TREND + M15 ENTRATA
import requests
import pandas as pd
import ta

# Le tue 10 coppie
COPPIE = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDUSD=X","USDCAD=X","NZDUSD=X","EURGBP=X","USDCHF=X"]
NOMI = {
    "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY",
    "EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDUSD=X":"AUD/USD",
    "USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","EURGBP=X":"EUR/GBP","USDCHF=X":"USD/CHF"
}

def get_df(ticker, interval, range_):
    try:
        yahoo_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_}"
        url = f"https://api.allorigins.win/raw?url={yahoo_url}"
        r = requests.get(url, timeout=20)
        j = r.json()
        res = j['chart']['result'][0]
        ts = res['timestamp']
        q = res['indicators']['quote'][0]
        df = pd.DataFrame({
            "Close": q['close'],
            "High": q['high'],
            "Low": q['low']
        }, index=pd.to_datetime(ts, unit='s')).dropna()
        return df
    except:
        return pd.DataFrame()

def analizza_safe():
    live = 0
    for cp in COPPIE:
        df_h1 = get_df(cp, "60m", "20d")
        df_m15 = get_df(cp, "15m", "5d")

        if df_h1.empty or df_m15.empty: continue
        if len(df_h1) < 210 or len(df_m15) < 50: continue

        live += 1

        # --- DATI H1 ---
        close_h1 = df_h1['Close']
        high_h1 = df_h1['High']
        low_h1 = df_h1['Low']
        close_m15 = df_m15['Close']

        prezzo = close_h1.iloc[-1]
        ema200 = close_h1.ewm(span=200).mean().iloc[-1]
        adx = ta.trend.ADXIndicator(high_h1, low_h1, close_h1, 14).adx().iloc[-1]
        macd = ta.trend.MACD(close_h1).macd().iloc[-1]
        rsi_m15 = ta.momentum.RSIIndicator(close_m15, 14).rsi().iloc[-1]
        e9 = close_m15.ewm(span=9).mean().iloc[-1]
        e21 = close_m15.ewm(span=21).mean().iloc[-1]

        # FILTRO SICUREZZA: ADX > 28 altrimenti è laterale
        if adx < 28:
            continue

        # FILTRO TREND + ENTRATA
        if prezzo > ema200 and macd > 0 and 45 <= rsi_m15 <= 55 and e9 > e21:
            det = f"H1 UP | Px>EMA200 | ADX {adx:.0f} | MACD>0 | M15 RSI {rsi_m15:.0f} | EMA9>21"
            return f"{NOMI[cp]} - CALL 30m", 85, live, det

        if prezzo < ema200 and macd < 0 and 45 <= rsi_m15 <= 55 and e9 < e21:
            det = f"H1 DOWN | Px<EMA200 | ADX {adx:.0f} | MACD<0 | M15 RSI {rsi_m15:.0f} | EMA9<21"
            return f"{NOMI[cp]} - PUT 30m", 85, live, det

    return None, 0, live, "Nessun trend H1 pulito - in attesa (sicurezza)"

# Per compatibilità se la tua app.py chiama analizza() invece di analizza_safe()
def analizza():
    return analizza_safe()
