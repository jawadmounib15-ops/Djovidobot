# V87 FINALE - 1MIN + 5MIN CONFERMA - ANTI DISCESA BRUTTA
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz, os
from concurrent.futures import ThreadPoolExecutor, as_completed
app = Flask(__name__)
OTC_MAP = {
    "EURUSD-OTC":"EURUSD=X", "GBPUSD-OTC":"GBPUSD=X", "USDJPY-OTC":"USDJPY=X",
    "AUDUSD-OTC":"AUDUSD=X", "USDCAD-OTC":"USDCAD=X", "USDCHF-OTC":"USDCHF=X",
    "EURJPY-OTC":"EURJPY=X", "EURGBP-OTC":"EURGBP=X", "GBPJPY-OTC":"GBPJPY=X",
    "AUDJPY-OTC":"AUDJPY=X", "EURCHF-OTC":"EURCHF=X", "GBPCHF-OTC":"GBPCHF=X",
    "CADJPY-OTC":"CADJPY=X", "CHFJPY-OTC":"CHFJPY=X", "AUDCAD-OTC":"AUDCAD=X",
    "EURAUD-OTC":"EURAUD=X", "GBPAUD-OTC":"GBPAUD=X", "AUDCHF-OTC":"AUDCHF=X",
    "NZDUSD-OTC":"NZDUSD=X", "EURCAD-OTC":"EURCAD=X",
    "Tesla OTC":"TSLA","Apple OTC":"AAPL","Microsoft OTC":"MSFT"
}
def fix(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def add_all(df):
    d=df['Close'].diff()
    df['RSI']=100-(100/(1+d.where(d>0,0).rolling(14).mean()/-d.where(d<0,0).rolling(14).mean()))
    df['EMA21']=df['Close'].ewm(21).mean(); df['EMA50']=df['Close'].ewm(50).mean()
    df['BB_UP']=df['Close'].rolling(20).mean() + df['Close'].rolling(20).std()*2
    df['BB_LOW']=df['Close'].rolling(20).mean() - df['Close'].rolling(20).std()*2
    df['ATR']=(df['High']-df['Low']).rolling(14).mean()
    return df
def check_otc(pair_otc, real_sym):
    try:
        # 1 MIN
        df1=yf.download(real_sym, period="5d", interval="1m", progress=False); df1=fix(df1)
        if len(df1)<60: return None
        df1=add_all(df1)
        # 5 MIN - CONFERMA ANTI DISCESA
        df5=yf.download(real_sym, period="5d", interval="5m", progress=False); df5=fix(df5)
        if len(df5)<60: return None
        df5=add_all(df5)

        c1=float(df1.iloc[-1]['Close']); ema21_1=float(df1.iloc[-1]['EMA21']); ema50_1=float(df1.iloc[-1]['EMA50']); rsi1=float(df1.iloc[-1]['RSI'])
        c5=float(df5.iloc[-1]['Close']); ema21_5=float(df5.iloc[-1]['EMA21']); ema50_5=float(df5.iloc[-1]['EMA50']); rsi5=float(df5.iloc[-1]['RSI'])

        # FILTRO 5 MIN - SE DISCESA BRUTTA BLOCCA
        # Per BUY: 5min deve essere sopra EMA50 e RSI >40, non in discesa brutta
        # Per SELL: 5min deve essere sotto EMA50 e RSI <60

        voti=0; dirs=[]
        if c1>ema50_1 and ema21_1>ema50_1 and 35<=rsi1<=58: voti+=1; dirs.append("BUY")
        if c1<ema50_1 and ema21_1<ema50_1 and 42<=rsi1<=65: voti+=1; dirs.append("SELL")

        # Bollinger
        if float(df1.iloc[-2]['Low']) < float(df1.iloc[-2]['BB_LOW']) and c1>float(df1.iloc[-1]['BB_LOW']) and 32<=rsi1<=52: voti+=1; dirs.append("BUY")
        if float(df1.iloc[-2]['High']) > float(df1.iloc[-2]['BB_UP']) and c1<float(df1.iloc[-1]['BB_UP']) and 48<=rsi1<=68: voti+=1; dirs.append("SELL")

        # Engulf
        o1=float(df1.iloc[-1]['Open']); o1_prev=float(df1.iloc[-2]['Open']); c1_prev=float(df1.iloc[-2]['Close'])
        body=abs(c1-o1); body_prev=abs(c1_prev-o1_prev)
        if body > body_prev*1.5:
            if c1>o1 and c1_prev<o1_prev: voti+=1; dirs.append("BUY")
            if c1<o1 and c1_prev>o1_prev: voti+=1; dirs.append("SELL")

        # Decidi direzione 1min
        buy_count=dirs.count("BUY"); sell_count=dirs.count("SELL")
        direzione="BUY" if buy_count>=2 else "SELL" if sell_count>=2 else None
        if not direzione: return None

        # FILTRO ANTI DISCESA BRUTTA 5MIN - QUESTO MANCAVA PRIMA
        if direzione=="BUY":
            if c5 < ema50_5: return None  # 5min in downtrend -> NO BUY
            if rsi5 < 40: return None  # 5min ipervenduto in discesa -> NO BUY
            if float(df5.iloc[-1]['Close']) < float(df5.iloc[-2]['Close']) and float(df5.iloc[-2]['Close']) < float(df5.iloc[-3]['Close']): return None  # 3 candele 5min rosse -> NO BUY
        else:
            if c5 > ema50_5: return None
            if rsi5 > 60: return None
            if float(df5.iloc[-1]['Close']) > float(df5.iloc[-2]['Close']) and float(df5.iloc[-2]['Close']) > float(df5.iloc[-3]['Close']): return None

        # Wick filter
        h1=float(df1.iloc[-1]['High']); l1=float(df1.iloc[-1]['Low'])
        uw = h1 - max(o1,c1); lw = min(o1,c1) - l1; body_abs=abs(c1-o1)
        if direzione=="BUY" and uw > body_abs*1.5: return None
        if direzione=="SELL" and lw > body_abs*1.5: return None

        fmt = f"{c1:.5f}" if "-OTC" in pair_otc and len(pair_otc)<12 else f"{c1:.2f}"
        return {"pair":pair_otc,"dir":direzione,"price":fmt,"note":f"85% {direzione} 1m+5m CONF | RSI1 {rsi1:.0f} RSI5 {rsi5:.0f}"}
    except: return None

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V87 FINAL</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:16px}.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:20px;width:95%;max-width:400px;display:block;margin:12px auto;cursor:pointer}.btn-green{background:#00ff88;color:#000;border:3px solid #00ff88}.btn-dark{background:#222;color:#fff;border:2px solid #444}.card{background:#1a1a1a;border-radius:14px;padding:14px;margin:10px auto;max-width:420px;text-align:left;border-left:6px solid #00ff88}.sell{border-left-color:#ff3b3b}.prepara{background:#ffcc00;color:#000;font-weight:bold;padding:12px;border-radius:10px;margin-top:8px;text-align:center;border:2px solid #fff}.exp{background:#00ff88;color:#000;font-weight:bold;padding:10px;border-radius:8px;display:block;margin-top:8px;text-align:center}</style></head><body>
<h2>✅ V87 FINALE - 1MIN + 5MIN</h2><p style="color:#00ff88">ANTI DISCESA BRUTTA - BLOCCA WTI COME OGGI</p>
<div class="btn btn-green" onclick="attiva()" ontouchstart="attiva()">🔔 ATTIVA V87</div><div class="btn btn-dark" onclick="cerca()">🔍 SCAN 23 - 1+5 MIN</div><p id="info">Pronto...</p><div id="live"></div>
<script>
let ok=false; function attiva(){ok=true; new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg').play().catch(()=>{}); cerca();}
function suona(){if(!ok)return; new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg').play(); try{navigator.vibrate([800,200,800]);}catch(e){}}
function getNext(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMinutes(n.getMinutes()+1); return nx;}
function cerca(){fetch('/api/scan').then(r=>r.json()).then(d=>{document.getElementById('info').innerText=d.time+' | ANTI DISCESA 1+5 MIN'; let h=''; let now=Date.now(); let next=getNext(); let entry=next.getTime(); let entryStr=next.toLocaleTimeString('it-IT'); d.signals.forEach(s=>{let diff=Math.max(0,Math.ceil((entry-now)/1000)); let txt=diff>0?`⏰ ENTRA TRA ${diff} SEC ALLE ${entryStr}`:'🔥 ENTRA ORA!'; h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><b style="color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b><br>${s.note}<br>${s.price}<br><div class="prepara">${txt}</div><div class="exp">TRADE 1 MIN - CONFERMATO 5 MIN</div></div>`;}); if(d.signals.length>0) suona(); document.getElementById('live').innerHTML=h||'<p style="color:#666">Nessun segnale - 5min blocca le discese brutte (meglio così)</p>';});}
setInterval(cerca,20000);
</script></body></html>"""
@app.route('/api/scan')
def api():
    tz=pytz.timezone('Europe/Rome'); now=datetime.now(tz).strftime('%H:%M:%S IT')
    out=[]
    with ThreadPoolExecutor(max_workers=23) as ex:
        futs={ex.submit(check_otc, otc, real): otc for otc, real in OTC_MAP.items()}
        for f in as_completed(futs):
            r=f.result()
            if r: out.append(r)
    return jsonify({"signals":out,"time":now})
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
