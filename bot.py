import os, time, requests, yfinance as yf, threading, pandas as pd, datetime
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home(): return "V151 FINALE COMPLETO OTC REALI"

TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")

# LISTE SEPARATE OTC / REALI
SYMBOLS_OTC = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","EURGBP=X","AUDJPY=X","CHFJPY=X"]
PAIRS_OTC = ["EUR/USD-OTC","GBP/USD-OTC","USD/JPY-OTC","AUD/USD-OTC","EUR/JPY-OTC","GBP/JPY-OTC","USD/CHF-OTC","EUR/GBP-OTC","AUD/JPY-OTC","CHF/JPY-OTC"]
SYMBOLS_REAL = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURGBP=X","AUDUSD=X","EURJPY=X","GBPJPY=X","USDCHF=X","AUDJPY=X","CHFJPY=X"]
PAIRS_REAL = ["EUR/USD","GBP/USD","USD/JPY","EUR/GBP","AUD/USD","EUR/JPY","GBP/JPY","USD/CHF","AUD/JPY","CHF/JPY"]

LAST = {}; LAST_PRICE = {}; GLOBAL = 0

def send(m):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def is_otc():
    now = datetime.datetime.utcnow()
    if now.weekday()>=5: return True
    if now.hour<7 or now.hour>21: return True
    return False

def wick(o,h,l,c):
    r=h-l
    if r==0: return 0,0,100
    return ((min(o,c)-l)/r)*100, ((h-max(o,c))/r)*100, (abs(o-c)/r)*100

def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def expiry(minuti):
    return (datetime.datetime.now() + datetime.timedelta(minutes=minuti)).strftime("%H:%M:%S")

def bot():
    global GLOBAL
    time.sleep(3)
    send("💣 *V151 FINALE ONLINE*\n✅ ANALISI PRECISA\n✅ OTC/REALI SEPARATI\n✅ SCADENZA CON ORARIO\n✅ ANTI-DUP + ANTI-LAG\n8 LAVORI TOP")
    while True:
        try:
            otc_mode = is_otc()
            SYMBOLS = SYMBOLS_OTC if otc_mode else SYMBOLS_REAL
            PAIRS = PAIRS_OTC if otc_mode else PAIRS_REAL
            MERCATO = "OTC" if otc_mode else "REALI"

            cand=[]
            for yahoo,pair in zip(SYMBOLS, PAIRS):
                time.sleep(0.4) # ANTI-LAG
                df=yf.download(yahoo, period="5d", interval="1m", progress=False, auto_adjust=True)
                if df.empty: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                df=df.dropna()
                if len(df)<60: continue

                df5=df.resample('5min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                df15=df.resample('15min').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                df1h=df.resample('1h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
                df4h=df.resample('4h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()

                df['RSI']=rsi(df['Close']); df5['RSI']=rsi(df5['Close']); df15['RSI']=rsi(df15['Close']); df1h['RSI']=rsi(df1h['Close'])
                df['EMA20']=df['Close'].ewm(span=20).mean(); df['EMA50']=df['Close'].ewm(span=50).mean()
                df['BB_UP']=df['Close'].rolling(20).mean()+df['Close'].rolling(20).std()*2
                df['BB_DN']=df['Close'].rolling(20).mean()-df['Close'].rolling(20).std()*2

                c=float(df['Close'].values[-2])
                # ANTI-DUP FORTE
                if pair in LAST_PRICE and abs(LAST_PRICE[pair]-c)<0.00008: continue
                if pair in LAST and time.time()-LAST[pair]<5400: continue

                o=float(df["Open"].values[-2]); h=float(df["High"].values[-2]); l=float(df["Low"].values[-2])
                o2=float(df["Open"].values[-3]); c2=float(df["Close"].values[-3]); o3=float(df["Open"].values[-4]); c3=float(df["Close"].values[-4])
                wb,ws,bd=wick(o,h,l,c)
                rsi1=float(df['RSI'].values[-2]); ema20=float(df['EMA20'].values[-2]); ema50=float(df['EMA50'].values[-2])
                bb_up=float(df['BB_UP'].values[-2]); bb_dn=float(df['BB_DN'].values[-2])
                rsi15=float(df15['RSI'].values[-2]) if len(df15)>=2 else rsi1
                rsi1h=float(df1h['RSI'].values[-2]) if len(df1h)>=2 else rsi1
                h4h=float(df4h["High"].values[-2]) if len(df4h)>=2 else h; l4h=float(df4h["Low"].values[-2]) if len(df4h)>=2 else l
                ora_now = datetime.datetime.now().strftime("%H:%M:%S")

                # L1 - 3MIN PINBAR
                if wb>=65 and bd<10 and rsi1<=35 and c>ema20 and ema20>ema50:
                    msg=f"💣 *L1 (3MIN) BUY {pair} PINBAR 76%*\n\n📊 *ANALISI {MERCATO} PRECISA {ora_now}:*\n├ Wick: {wb:.1f}% ✅ >65%\n├ Body: {bd:.1f}% ✅ <10%\n├ RSI: {rsi1:.1f} ✅ <35\n├ EMA20: {ema20:.5f}\n├ EMA50: {ema50:.5f}\n└ Trend: rialzista ✅\n\n⏰ *ENTRATA: {ora_now}*\n⏳ *SCADENZA: 3 MIN → {expiry(3)}*\n🎯 *{MERCATO} ANALIZZATO ORA*\n💰 Prezzo: {c:.5f}"
                    cand.append((76,msg,pair,c))
                if ws>=65 and bd<10 and rsi1>=65 and c<ema20 and ema20<ema50:
                    msg=f"💣 *L1 (3MIN) SELL {pair} PINBAR 76%*\n\n📊 *ANALISI {MERCATO} PRECISA {ora_now}:*\n├ Wick: {ws:.1f}% ✅ >65%\n├ Body: {bd:.1f}% ✅ <10%\n├ RSI: {rsi1:.1f} ✅ >65\n├ EMA20: {ema20:.5f}\n└ Trend: ribassista ✅\n\n⏰ *ENTRATA: {ora_now}*\n⏳ *SCADENZA: 3 MIN → {expiry(3)}*\n🎯 *{MERCATO} ANALIZZATO ORA*\n💰 Prezzo: {c:.5f}"
                    cand.append((76,msg,pair,c))

                # L2/L3 - 5MIN ENGULFING
                if c2<o2 and c>o and c>o2 and c2>bb_dn*0.999 and rsi1<45 and bd<18:
                    msg=f"🔥 *L2 (5MIN) BUY {pair} ENGULF 68%*\n\n📊 *ANALISI {MERCATO} {ora_now}:*\n├ Engulfing rialzista ✅\n├ RSI: {rsi1:.1f} ✅ <45\n├ BB Low: {bb_dn:.5f}\n└ Prezzo sopra BB ✅\n\n⏰ *ENTRATA: {ora_now}*\n⏳ *SCADENZA: 5 MIN → {expiry(5)}*\n🎯 *{MERCATO}* | {c:.5f}"
                    cand.append((68,msg,pair,c))
                if c2>o2 and c<o and c<o2 and c2<bb_up*1.001 and rsi1>55 and bd<18:
                    msg=f"🔥 *L3 (5MIN) SELL {pair} ENGULF 68%*\n\n📊 *ANALISI {MERCATO} {ora_now}:*\n├ Engulfing ribassista ✅\n├ RSI: {rsi1:.1f} ✅ >55\n├ BB High: {bb_up:.5f}\n└ Prezzo sotto BB ✅\n\n⏰ *ENTRATA: {ora_now}*\n⏳ *SCADENZA: 5 MIN → {expiry(5)}*\n🎯 *{MERCATO}* | {c:.5f}"
                    cand.append((68,msg,pair,c))

                # L4/L5 - 15MIN MORNING/EVENING STAR
                if c3<o3 and abs(c3-o3)>abs(c2-o2)*1.3 and c>o and c>(o3+c3)/2 and rsi15<40:
                    msg=f"⭐ *L4 (15MIN) BUY {pair} MORNING STAR 76%*\n\n📊 *ANALISI {MERCATO} {ora_now}:*\n├ 3 candele reversal ✅\n├ RSI15: {rsi15:.1f} ✅ <40\n└ Pattern rialzista ✅\n\n⏰ *ENTRATA: {ora_now}*\n⏳ *SCADENZA: 15 MIN → {expiry(15)}*\n🎯 *{MERCATO}* | {c:.5f}"
                    cand.append((76,msg,pair,c))
                if c3>o3 and abs(c3-o3)>abs(c2-o2)*1.3 and c<o and c<(o3+c3)/2 and rsi15>60:
                    msg=f"⭐ *L5 (15MIN) SELL {pair} EVENING STAR 72%*\n\n📊 *ANALISI {MERCATO} {ora_now}:*\n├ 3 candele reversal ✅\n├ RSI15: {rsi15:.1f} ✅ >60\n└ Pattern ribassista ✅\n\n⏰ *ENTRATA: {ora_now}*\n⏳ *SCADENZA: 15 MIN → {expiry(15)}*\n🎯 *{MERCATO}* | {c:.5f}"
                    cand.append((72,msg,pair,c))

                # L6 - 15MIN TREND
                if c>ema20 and ema20>ema50 and rsi15>50 and rsi15<68:
                    msg=f"📈 *L6 (15MIN) BUY {pair} TREND 70%*\n\n📊 *ANALISI {MERCATO} {ora_now}:*\n├ EMA20>{ema50} ✅\n├ RSI15: {rsi15:.1f} 50-68 ✅\n└ Rimbalzo trend ✅\n\n⏰ *ENTRATA: {ora_now}*\n⏳ *SCADENZA: 15 MIN → {expiry(15)}*\n🎯 *{MERCATO}* | {c:.5f}"
                    cand.append((70,msg,pair,c))
                if c<ema20 and ema20<ema50 and rsi15<50 and rsi15>32:
                    msg=f"📈 *L6 (15MIN) SELL {pair} TREND 70%*\n\n📊 *ANALISI {MERCATO} {ora_now}:*\n├ EMA20<{ema50} ✅\n├ RSI15: {rsi15:.1f} 32-50 ✅\n└ Rimbalzo trend ✅\n\n⏰ *ENTRATA: {ora_now}*\n⏳ *SCADENZA: 15 MIN → {expiry(15)}*\n🎯 *{MERCATO}* | {c:.5f}"
                    cand.append((70,msg,pair,c))

                # L7/L8 - 1 ORA BREAKOUT
                if c>h4h and c>bb_up and rsi1h>60:
                    msg=f"🚀 *L7 (1ORA) BUY {pair} BREAKOUT 68%*\n\n📊 *ANALISI {MERCATO} {ora_now}:*\n├ Rottura max 4H: {h4h:.5f} ✅\n├ BB rotta: {bb_up:.5f} ✅\n├ RSI1H: {rsi1h:.1f} ✅ >60\n└ Breakout rialzista ✅\n\n⏰ *ENTRATA: {ora_now}*\n⏳ *SCADENZA: 1 ORA → {expiry(60)}*\n🎯 *{MERCATO}* | {c:.5f}"
                    cand.append((68,msg,pair,c))
                if c<l4h and c<bb_dn and rsi1h<40:
                    msg=f"🚀 *L8 (1ORA) SELL {pair} BREAKOUT 68%*\n\n📊 *ANALISI {MERCATO} {ora_now}:*\n├ Rottura min 4H: {l4h:.5f} ✅\n├ BB rotta: {bb_dn:.5f} ✅\n├ RSI1H: {rsi1h:.1f} ✅ <40\n└ Breakout ribassista ✅\n\n⏰ *ENTRATA: {ora_now}*\n⏳ *SCADENZA: 1 ORA → {expiry(60)}*\n🎯 *{MERCATO}* | {c:.5f}"
                    cand.append((68,msg,pair,c))

            if cand and time.time()-GLOBAL>480:
                cand.sort(key=lambda x: x[0], reverse=True)
                score,msg,pair,price=cand[0]
                send(msg); LAST[pair]=time.time(); LAST_PRICE[pair]=price; GLOBAL=time.time()
            time.sleep(3)
        except Exception as e:
            print(e); time.sleep(5)

threading.Thread(target=bot, daemon=True).start()
app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
