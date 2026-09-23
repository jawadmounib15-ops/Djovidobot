import yfinance as yf
import time, gc, os, requests

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCHF=X","USDCAD=X","EURJPY=X","GBPJPY=X","EURGBP=X","AUDJPY=X","EURCHF=X","GBPCHF=X"]
NAMES = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","EURJPY","GBPJPY","EURGBP","AUDJPY","EURCHF","GBPCHF"]

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def tg(m):
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id":CHAT_ID,"text":m}, timeout=5)
    except: pass

def get_rsi(c, p=14):
    d = c.diff()
    g = d.where(d>0,0).rolling(p).mean()
    l = -d.where(d<0,0).rolling(p).mean()
    rs = g/l
    return 100 - (100/(1+rs))

tg("💀 V106 LIGHT TOLL 0.10% ONLINE")

while True:
    for i, pair in enumerate(PAIRS):
        try:
            df = yf.download(pair, period="1d", interval="5m", progress=False, auto_adjust=True)
            if len(df) < 50:
                del df
                continue

            close = float(df['Close'].iloc[-1])
            sma = float(df['Close'].rolling(20).mean().iloc[-1])
            std = float(df['Close'].rolling(20).std().iloc[-1])
            upper = sma + 2*std
            lower = sma - 2*std
            ema = float(df['Close'].ewm(span=200).mean().iloc[-1])
            rsi = float(get_rsi(df['Close']).iloc[-1])

            toll = lower * 0.001 # 0.10% = 10

            if rsi <= 35 and close <= lower + toll and close > ema:
                tg(f"💀 5M BUY {NAMES[i]} RSI:{int(rsi)} TOLL 0.10% 👉 POCKET: SELL")
            elif rsi >= 65 and close >= upper - toll and close < ema:
                tg(f"💀 5M SELL {NAMES[i]} RSI:{int(rsi)} TOLL 0.10% 👉 POCKET: BUY")

            del df
            gc.collect()
            time.sleep(3)
        except:
            gc.collect()
            continue
    gc.collect()
    time.sleep(60)
