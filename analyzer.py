import requests
import pandas as pd

COPPIE = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDUSD=X","USDCAD=X","NZDUSD=X","EURGBP=X","USDCHF=X"]
NOMI = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDUSD=X":"AUD/USD","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","EURGBP=X":"EUR/GBP","USDCHF=X":"USD/CHF"}

def ema(s, n): return s.ewm(span=n).mean()
def rsi(s, n=14):
    d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    rs = g.ewm(alpha=1/n).mean() / l.ewm(alpha=1/n).mean()
    return 100 - (100/(1+rs))
def adx(h, l, c, n=14):
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/n).mean()
    up = h.diff(); dn = -l.diff()
    plus = ((up>dn)&(up>0))*up; minus = ((dn>up)&(dn>0))*dn
    plus_di = 100 * plus.ewm(alpha=1/n).mean() / atr
    minus_di = 100 * minus.ewm(alpha=1/n).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=1/n).mean()
def macd(s): return s.ewm(span=12).mean() - s.ewm(span=26).mean()

def get_df(ticker, interval, range_):
    try:
        yahoo_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_}"
        url = f"https://api.allorigins.win/raw?url={yahoo_url}"
        r = requests.get(url, timeout=20).json()
        res = r['chart']['result'][0]
        ts = res['timestamp']; q = res['indicators']['quote'][0]
        return pd.DataFrame({"Close":q['close'],"High":q['high'],"Low":q['low']}, index=pd.to_datetime(ts, unit='s')).dropna()
    except: return pd.DataFrame()

def analizza_safe():
    live=0
    for cp in COPPIE:
        df_h1 = get_df(cp,"60m","20d"); df_m15 = get_df(cp,"15m","5d")
        if df_h1.empty or df_m15.empty or len(df_h1)<210 or len(df_m15)<50: continue
        live+=1
        c1,h1,l1 = df_h1['Close'],df_h1['High'],df_h1['Low']; c15 = df_m15['Close']
        prezzo = c1.iloc[-1]; e200 = ema(c1,200).iloc[-1]; adx_v = adx(h1,l1,c1).iloc[-1]
        macd_v = macd(c1).iloc[-1]; rsi_v = rsi(c15).iloc[-1]
        e9 = ema(c15,9).iloc[-1]; e21 = ema(c15,21).iloc[-1]
        if adx_v < 28: continue
        if prezzo>e200 and macd_v>0 and 45<=rsi_v<=55 and e9>e21:
            return f"{NOMI[cp]} - CALL 30m",85,live,f"H1 UP | Px>EMA200 | ADX {adx_v:.0f}>28 | MACD>0 | M15 RSI {rsi_v:.0f} | EMA9>21"
        if prezzo<e200 and macd_v<0 and 45<=rsi_v<=55 and e9<e21:
            return f"{NOMI[cp]} - PUT 30m",85,live,f"H1 DOWN | Px<EMA200 | ADX {adx_v:.0f}>28 | MACD<0 | M15 RSI {rsi_v:.0f} | EMA9<21"
    return None,0,live,"Nessun trend H1 pulito - in attesa sicurezza"

def analizza(): return analizza_safe()
