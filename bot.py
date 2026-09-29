# bot.py - DOPPIO H4 4H + M5 30M - NOMI TUOI ENV
from flask import Flask, render_template_string
import threading, time, os, pytz, pandas as pd
from datetime import datetime
from curl_cffi import requests as crequests
import requests as req

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")

TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

COPPIE = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDUSD=X","USDCAD=X","NZDUSD=X","EURGBP=X","USDCHF=X"]
NOMI = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDUSD=X":"AUD/USD","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","EURGBP=X":"EUR/GBP","USDCHF=X":"USD/CHF"}

HTML = """<html><head><meta name="viewport" content="width=device-width"><title>DOPPIO PINBAR</title>
<style>
body{background:#0e0e0e;color:#fff;font-family:Arial;padding:15px}
.card{background:#1a1a1a;padding:16px;border-radius:16px;margin-top:14px}
.h4{border-left:5px solid #00ff88}.m5{border-left:5px solid #ffcc00}
.safe{border:1px solid #00ff88;border-radius:12px;padding:10px;text-align:center;color:#00ff88;font-weight:bold}
small{color:#aaa;white-space:pre-wrap;word-break:break-all;font-size:12px}
.bull{color:#00ff88}.bear{color:#ff5555}
</style></head><body>
<h2>📌 DOPPIO PINBAR H4 + M5</h2>
<div class="safe">LIVE {{live}}/10 | TG {{tg}} | H4:{{s1}}% | M5:{{s2}}%</div>
<div class="card h4"><b>LAVORO 1 - H4 4 ORE</b><br><div class="{{c1}}">{{sig1}}</div><small>{{det1}}</small></div>
<div class="card m5"><b>LAVORO 2 - M5 30M FILA ORDINATA</b><br><div class="{{c2}}">{{sig2}}</div><small>{{det2}}</small><br><small>{{debug}}</small></div>
<div style="color:#666;margin-top:10px">{{ora}}</div>
<script>setTimeout(()=>location.reload(),25000)</script></body></html>"""

def send_tg(txt):
    if not TOKEN or not CHAT_ID: return False
    try:
        url=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        r=req.post(url, data={"chat_id":CHAT_ID,"text":txt,"parse_mode":"Markdown"}, timeout=15)
        print(f"TG SEND: {r.status_code} {r.text[:200]}")
        return r.status_code==200
    except Exception as e:
        print(f"TG ERR: {e}")
        return False

def ema(s,n): return s.ewm(span=n).mean()
def get_df(ticker, interval, range_):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_}"
        r=crequests.get(url, impersonate="chrome110", timeout=20)
        j=r.json()
        if j['chart']['result'] is None: return pd.DataFrame()
        res=j['chart']['result'][0]; ts=res['timestamp']; q=res['indicators']['quote'][0]
        df=pd.DataFrame({"Open":q['open'],"High":q['high'],"Low":q['low'],"Close":q['close']}, index=pd.to_datetime(ts,unit='s')).dropna()
        return df
    except: return pd.DataFrame()

def is_pinbar(last, prev):
    O,H,L,C=float(last['Open']),float(last['High']),float(last['Low']),float(last['Close'])
    Po,Ph,Pl=float(prev['Open']),float(prev['High']),float(prev['Low'])
    body=abs(C-O); rng=H-L
    if rng==0: return False,"",0,0
    upper=H-max(O,C); lower=min(O,C)-L
    nose=max(upper,lower); nose_pct=nose/rng*100; body_pct=body/rng*100
    if nose_pct<70 or body_pct>25: return False,"",0,0
    if not (min(O,C)>=Pl and max(O,C)<=Ph): return False,"",0,0
    tipo="BULLISH" if lower>upper else "BEARISH"
    if tipo=="BULLISH" and C<L+rng*0.65: return False,"",0,0
    if tipo=="BEARISH" and C>L+rng*0.35: return False,"",0,0
    return True,tipo,nose_pct,body_pct

stato={"sig1":"Avvio...","det1":"...","c1":"","s1":0,"sig2":"Avvio...","det2":"...","c2":"","s2":0,"live":0,"tg":"ON" if TOKEN else "OFF","debug":"..."}
last_h4=""; last_m5=""

def lavoro_h4():
    global last_h4
    while True:
        try:
            live=0
            for cp in COPPIE:
                df=get_df(cp,"240m","60d")
                if df.empty or len(df)<50: continue
                live+=1; df['EMA21']=ema(df['Close'],21)
                last=df.iloc[-1]; prev=df.iloc[-2]
                ok,tipo,nose,body=is_pinbar(last,prev)
                if not ok: continue
                up=last['Close']>last['EMA21']
                down=last['Close']<last['EMA21']
                rh=df['High'].iloc[-20:-1].max(); rl=df['Low'].iloc[-20:-1].min()
                fake=(last['High']>rh and last['Close']<rh) or (last['Low']<rl and last['Close']>rl)
                if tipo=="BULLISH" and not up: continue
                if tipo=="BEARISH" and not down: continue
                sig=f"{NOMI[cp]} {tipo} - {'CALL 4h' if tipo=='BULLISH' else 'PUT 4h'}"
                stato.update({"sig1":sig,"det1":f"Naso {nose:.0f}% Body {body:.0f}% EMA21+{'Fake' if fake else 'Bounce'}","c1":"bull" if tipo=="BULLISH" else "bear","s1":85 if nose>=75 else 80,"live":live})
                if sig!=last_h4:
                    send_tg(f"🟢 *LAVORO 1 - H4 4H*\n📊 {NOMI[cp]}\n📌 {tipo} {nose:.0f}%\n⏰ {sig}")
                    last_h4=sig
                break
            else:
                stato["sig1"]=f"{live}/10 LIVE - Nessuna H4"; stato["s1"]=0
        except Exception as e: stato["det1"]=str(e)[:120]
        time.sleep(90)

def lavoro_m5():
    global last_m5
    while True:
        try:
            for cp in COPPIE:
                df_h4=get_df(cp,"240m","60d"); df_h1=get_df(cp,"60m","20d"); df_m5=get_df(cp,"5m","5d")
                if df_h4.empty or df_h1.empty or df_m5.empty: continue
                df_h4['EMA21']=ema(df_h4['Close'],21); df_h1['EMA21']=ema(df_h1['Close'],21); df_m5['EMA21']=ema(df_m5['Close'],21)
                last=df_m5.iloc[-1]; prev=df_m5.iloc[-2]
                ok,tipo,nose,body=is_pinbar(last,prev)
                if not ok: continue
                up_h4=df_h4.iloc[-1]['Close']>df_h4.iloc[-1]['EMA21']; up_h1=df_h1.iloc[-1]['Close']>df_h1.iloc[-1]['EMA21']
                down_h4=df_h4.iloc[-1]['Close']<df_h4.iloc[-1]['EMA21']; down_h1=df_h1.iloc[-1]['Close']<df_h1.iloc[-1]['EMA21']
                if tipo=="BULLISH" and not (up_h4 and up_h1): continue
                if tipo=="BEARISH" and not (down_h4 and down_h1): continue
                sig=f"{NOMI[cp]} {tipo} - {'CALL 30m' if tipo=='BULLISH' else 'PUT 30m'}"
                stato.update({"sig2":sig,"det2":f"Naso {nose:.0f}% Fila H4:{'UP' if up_h4 else 'DOWN'} H1:{'UP' if up_h1 else 'DOWN'}","c2":"bull" if tipo=="BULLISH" else "bear","s2":74 if nose>=75 else 70})
                if sig!=last_m5:
                    send_tg(f"🟡 *LAVORO 2 - M5 30M FILA ORDINATA*\n📊 {NOMI[cp]}\n📌 {tipo} M5 {nose:.0f}%\n📈 H4 {'UP' if up_h4 else 'DOWN'} H1 {'UP' if up_h1 else 'DOWN'}\n⏰ {sig}")
                    last_m5=sig
                break
            else:
                stato["sig2"]="Nessuna M5 in fila ordinata"
        except Exception as e: stato["debug"]=str(e)[:120]
        time.sleep(60)

# AVVIO TELEGRAM TEST - arriva 1 volta all'avvio
if TOKEN and CHAT_ID:
    send_tg("✅ *BOT AVVIATO CORRETTAMENTE*\n\n🟢 Lavoro 1: H4 4h sicuro\n🟡 Lavoro 2: M5 30m fila ordinata\n\nAspetto pinbar pulita 70%...")

threading.Thread(target=lavoro_h4, daemon=True).start()
threading.Thread(target=lavoro_m5, daemon=True).start()

@app.route('/')
def home():
    ora=datetime.now(ROMA).strftime('%H:%M:%S')
    return render_template_string(HTML, sig1=stato["sig1"], det1=stato["det1"], c1=stato["c1"], s1=stato["s1"], sig2=stato["sig2"], det2=stato["det2"], c2=stato["c2"], s2=stato["s2"], live=stato["live"], tg=stato["tg"], debug=stato["debug"], ora=ora)

if __name__=="__main__":
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
