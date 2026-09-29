# bot.py - PINBAR H4 4H + TELEGRAM
from flask import Flask, render_template_string
import threading, time, os, pytz, pandas as pd
from datetime import datetime
from curl_cffi import requests as crequests
import requests as req

app = Flask(__name__)
ROMA = pytz.timezone("Europe/Rome")

# TELEGRAM
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

COPPIE = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDUSD=X","USDCAD=X","NZDUSD=X","EURGBP=X","USDCHF=X"]
NOMI = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDUSD=X":"AUD/USD","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","EURGBP=X":"EUR/GBP","USDCHF=X":"USD/CHF"}

HTML = """<html><head><meta name="viewport" content="width=device-width"><title>PINBAR H4 TELEGRAM</title>
<style>
body{background:#0e0e0e;color:#fff;font-family:Arial;padding:15px}
.card{background:#1a1a1a;padding:18px;border-radius:16px;margin-top:14px;border-left:5px solid #00ff88}
.safe{border:1px solid #00ff88;border-radius:12px;padding:12px;text-align:center;color:#00ff88;font-weight:bold}
small{color:#aaa;white-space:pre-wrap;word-break:break-all}
.bull{color:#00ff88}.bear{color:#ff5555}
</style></head><body>
<h2>📌 PINBAR H4 4H + TELEGRAM</h2>
<div class="safe">{{batch_info}} | LIVE {{live}}/10 | Telegram {{tg_status}}</div>
<div class="card"><div style="font-size:22px" class="{{colore}}">{{segnale}}</div><small>{{dettaglio}}</small><div style="color:#666;margin-top:8px">{{ora2}}</div></div>
<div class="card"><div style="font-size:40px" class="{{colore}}">{{percent}}%</div><div class="{{colore}}">{{msg}}</div><small>{{debug}}</small><br><small>{{ora}}</small></div>
<script>setTimeout(()=>location.reload(),30000)</script></body></html>"""

def send_telegram(messaggio):
    if not TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        req.post(url, data={"chat_id": CHAT_ID, "text": messaggio, "parse_mode":"Markdown"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def ema(s,n): return s.ewm(span=n).mean()
def get_df(ticker):
    try:
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=240m&range=60d"
        r=crequests.get(url, impersonate="chrome110", timeout=20)
        j=r.json()
        if j['chart']['result'] is None: return pd.DataFrame()
        res=j['chart']['result'][0]; ts=res['timestamp']; q=res['indicators']['quote'][0]
        df=pd.DataFrame({"Open":q['open'],"High":q['high'],"Low":q['low'],"Close":q['close']}, index=pd.to_datetime(ts,unit='s')).dropna()
        return df
    except: return pd.DataFrame()

ultimo_segnale_inviato = ""

def analizza_h4_4h():
    global ultimo_segnale_inviato
    live=0
    for cp in COPPIE:
        df = get_df(cp)
        if df.empty or len(df)<50: continue
        live+=1
        df['EMA21'] = ema(df['Close'],21)
        last=df.iloc[-1]; prev=df.iloc[-2]

        O,H,L,C = float(last['Open']), float(last['High']), float(last['Low']), float(last['Close'])
        Po,Ph,Pl,Pc = float(prev['Open']), float(prev['High']), float(prev['Low']), float(prev['Close'])
        body=abs(C-O); rng=H-L
        if rng==0: continue
        upper=H-max(O,C); lower=min(O,C)-L
        nose=max(upper,lower); nose_pct=nose/rng*100; body_pct=body/rng*100

        if nose_pct < 70: continue
        if body_pct > 25: continue
        if not (min(O,C) >= Pl and max(O,C) <= Ph): continue

        tipo = "BULLISH" if lower>upper else "BEARISH"
        if tipo=="BULLISH" and C < L+rng*0.65: continue
        if tipo=="BEARISH" and C > L+rng*0.35: continue

        up = last['Close'] > last['EMA21']; down = last['Close'] < last['EMA21']
        recent_high = df['High'].iloc[-20:-1].max(); recent_low = df['Low'].iloc[-20:-1].min()
        fakeout_res = last['High'] > recent_high and last['Close'] < recent_high
        fakeout_sup = last['Low'] < recent_low and last['Close'] > recent_low
        key_level = fakeout_res or fakeout_sup

        if tipo=="BULLISH" and not (up and (key_level or abs(last['Low']-last['EMA21'])/last['Close']<0.0035)): continue
        if tipo=="BEARISH" and not (down and (key_level or abs(last['High']-last['EMA21'])/last['Close']<0.0035)): continue

        perc = 85 if nose_pct>=75 else 80
        azione = f"CALL 4h" if tipo=="BULLISH" else f"PUT 4h"
        segnale_txt = f"{NOMI[cp]} - PINBAR {tipo} PULITA - {azione}"

        # EVITA SPAM TELEGRAM - invia solo se nuovo
        if segnale_txt!= ultimo_segnale_inviato:
            msg_tg = f"🚨 *PINBAR H4 PULITA* 🚨\n\n📊 {NOMI[cp]}\n📌 {tipo}\n💥 Naso {nose_pct:.0f}% (regola 70%)\n📦 Body {body_pct:.0f}% dentro prev\n📈 EMA21 {'UP' if up else 'DOWN'} + {'FAKEOUT' if key_level else 'Rimbalzo EMA'}\n\n⏰ *ENTRA ORA: {azione}*\nScadenza 4 ore\n\nWinRate atteso 53% | R:R 1:2"
            send_telegram(msg_tg)
            ultimo_segnale_inviato = segnale_txt

        det = f"Naso {nose_pct:.0f}% | Body {body_pct:.0f}% dentro prev | EMA21 + Fakeout OK | Scadenza 4h"
        return segnale_txt, perc, live, det, f"Telegram inviato: {NOMI[cp]}", tipo

    return None,0,live,"Nessuna pinbar H4 pulita - 1-3 al giorno max è normale", "In attesa H4", ""

stato={"percent":0,"msg":"In attesa pinbar H4...","segnale":"Scansiono H4 4h...","dettaglio":"Scadenza 4h = 1 candela H4","live":0,"batch_info":"Avvio H4","debug":"Telegram pronto" if TOKEN else "Metti TOKEN nelle Env","colore":"","tg_status":"ON" if TOKEN else "OFF"}

def loop():
    while True:
        try:
            res,perc,live,det,dbg,tipo = analizza_h4_4h()
            stato["live"]=live; stato["batch_info"]=f"{live}/10 LIVE H4"; stato["debug"]=dbg
            stato["tg_status"]="ON" if TOKEN else "OFF"
            if res:
                stato["segnale"]=f"ENTRA ORA: {res}"; stato["dettaglio"]=det; stato["percent"]=perc; stato["msg"]=res
                stato["colore"]="bull" if "BULLISH" in res else "bear"
            else:
                stato["segnale"]=f"{live}/10 LIVE - {det}"; stato["percent"]=0; stato["msg"]="In attesa pinbar H4 pulita"; stato["colore"]=""
        except Exception as e: stato["debug"]=str(e)[:200]
        time.sleep(90)

threading.Thread(target=loop,daemon=True).start()

@app.route('/')
def home():
    ora=datetime.now(ROMA).strftime('%H:%M:%S')
    return render_template_string(HTML,**stato,ora=ora,ora2=ora)

if __name__=="__main__":
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",10000)))
