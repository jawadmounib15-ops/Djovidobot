import os, time, requests, yfinance as yf, pandas as pd
from threading import Thread
from flask import Flask
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VERSION = "V38 FINALE REALE BLOCCO DISCESA"
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "EURGBP=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X"]

app = Flask(__name__)
@app.route("/")
def home(): return f"{VERSION} LIVE"
def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": m, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def calc_rsi(c, p=14):
    d = c.diff()
    g = d.where(d>0,0).rolling(p).mean()
    l = -d.where(d<0,0).rolling(p).mean()
    rs = g/l
    return 100-(100/(1+rs))

last_sent = {}

def get_data(sym):
    try:
        df = yf.download(sym, period="5d", interval="15m", progress=False, auto_adjust=True)
        if len(df)<100: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        c = pd.to_numeric(df['Close'], errors='coerce').dropna()
        h, l, o = df['High'], df['Low'], df['Open']
        ema20 = c.ewm(span=20).mean(); ema50 = c.ewm(span=50).mean()
        sma50 = c.rolling(50).mean()
        rsi = calc_rsi(c)
        bb_m = c.rolling(20).mean(); bb_s = c.rolling(20).std()
        bb_u = bb_m+2*bb_s; bb_l = bb_m-2*bb_s

        price=float(c.iloc[-1]); prev=float(c.iloc[-2]); prev2=float(c.iloc[-3])
        e20=float(ema20.iloc[-1]); e50=float(ema50.iloc[-1])
        pe20=float(ema20.iloc[-2]); pe50=float(ema50.iloc[-2])
        s50=float(sma50.iloc[-1]); s50_5=float(sma50.iloc[-6])
        r=float(rsi.iloc[-1])
        bu=float(bb_u.iloc[-1]); bl=float(bb_l.iloc[-1])
        bb_w=(bu-bl)/float(bb_m.iloc[-1])
        curr_o=float(o.iloc[-1]); prev_o=float(o.iloc[-2])
        is_green = price > curr_o
        is_red = price < curr_o
        body = abs(price-curr_o)
        sma_up = s50 > s50_5 + 0.0001
        sma_down = s50 < s50_5 - 0.0001
        # FILTRO CROLLO: se ultime 2 chiusure in discesa, niente BUY
        trend_down = prev < prev2 and price < prev
        trend_up = prev > prev2 and price > prev

        lavoro=side=None

        # L1 SOLO TREND FORTE
        if not lavoro and e20>e50 and sma_up and is_green and trend_up and price>s50 and price>e20 and prev<price:
            if r>=52 and r<=54:
                side="BUY"; lavoro="L1 TREND FORTE"
        elif not lavoro and e20<e50 and sma_down and is_red and trend_down and price<s50 and price<e20 and prev>price:
            if r>=46 and r<=48:
                side="SELL"; lavoro="L1 TREND FORTE"

        # L2 RIMBALZO SOLO ESTREMO
        if not lavoro:
            if float(c.iloc[-1]) <= bl and r<=32 and is_green:
                side="BUY"; lavoro="L2 RIMBALZO"
            elif float(c.iloc[-1]) >= bu and r>=68 and is_red:
                side="SELL"; lavoro="L2 RIMBALZO"

        # L3 BREAKOUT CON TREND
        if not lavoro:
            max20=float(h.rolling(20).max().iloc[-2])
            min20=float(l.rolling(20).min().iloc[-2])
            if price>max20 and is_green and sma_up and r>=54 and r<=58:
                side="BUY"; lavoro="L3 BREAKOUT"
            elif price<min20 and is_red and sma_down and r>=42 and r<=46:
                side="SELL"; lavoro="L3 BREAKOUT"

        # L7 SQUEEZE STRETTISSIMO
        if not lavoro:
            if bb_w<0.0018 and e20>e50 and sma_up and is_green and r>=52 and r<=53.5 and price>e20:
                side="BUY"; lavoro="L7 SQUEEZE"
            elif bb_w<0.0018 and e20<e50 and sma_down and is_red and r>=46.5 and r<=48 and price<e20:
                side="SELL"; lavoro="L7 SQUEEZE"

        # BLOCCO TOTALE PER COPPIA 25 MIN
        if side:
            now=datetime.now()
            if sym in last_sent:
                diff=now-last_sent[sym]['time']
                same_price=abs(last_sent[sym].get('price',0)-price)<0.0001
                if diff < timedelta(minutes=25) or same_price:
                    return {"skip":True}
            last_sent[sym]={'time':now,'price':price,'key':lavoro}
            return {"price":price,"rsi":r,"side":side,"lavoro":lavoro}
        return None
    except: return None

def bot_loop():
    time.sleep(3)
    send_tg(f"✅ *{VERSION} LIVE*\nBlocco discesa attivo - 25min per coppia - 15m")
    while True:
        for sym in SYMBOLS:
            d=get_data(sym)
            if not d or d.get("skip"): continue
            if d.get("side"):
                nome=sym.replace("=X","")
                emoji="🟢" if d['side']=="BUY" else "🔻"
                send_tg(f"{emoji} *{d['side']} {nome} - {d['lavoro']}*\nRSI: {d['rsi']:.1f} | 15m\nPrezzo: {d['price']:.5f}")
            time.sleep(10)
        time.sleep(300)

Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__":
    port=int(os.getenv("PORT",10000))
    app.run(host="0.0.0.0",port=port)
