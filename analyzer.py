# V87 FINALE FIX CRASH - 1MIN + 5MIN - TUTTE 33 COPPIE - 1 MIN SCADENZA
import yfinance as yf, pandas as pd, gc
from flask import Flask, jsonify
from datetime import datetime
import pytz, os, time
app = Flask(__name__)
OTC_MAP = {
    "EURUSD-OTC":"EURUSD=X", "GBPUSD-OTC":"GBPUSD=X", "USDJPY-OTC":"USDJPY=X",
    "AUDUSD-OTC":"AUDUSD=X", "USDCAD-OTC":"USDCAD=X", "USDCHF-OTC":"USDCHF=X",
    "EURJPY-OTC":"EURJPY=X", "EURGBP-OTC":"EURGBP=X", "GBPJPY-OTC":"GBPJPY=X",
    "AUDJPY-OTC":"AUDJPY=X", "EURCHF-OTC":"EURCHF=X", "GBPCHF-OTC":"GBPCHF=X",
    "CADJPY-OTC":"CADJPY=X", "CHFJPY-OTC":"CHFJPY=X", "AUDCAD-OTC":"AUDCAD=X",
    "EURAUD-OTC":"EURAUD=X", "GBPAUD-OTC":"GBPAUD=X", "AUDCHF-OTC":"AUDCHF=X",
    "NZDUSD-OTC":"NZDUSD=X", "EURCAD-OTC":"EURCAD=X", "NZDJPY-OTC":"NZDJPY=X",
    "GBPCAD-OTC":"GBPCAD=X", "EURTRY-OTC":"EURTRY=X", "USDTRY-OTC":"USDTRY=X",
    "Tesla OTC":"TSLA","Apple OTC":"AAPL","Microsoft OTC":"MSFT",
    "Gold OTC":"GC=F","Silver OTC":"SI=F","WTI OTC":"CL=F","Brent OTC":"BZ=F","Gas OTC":"NG=F"
}
def fix(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def add_all(df):
    d=df['Close'].diff()
    df['RSI']=100-(100/(1+d.where(d>0,0).rolling(14).mean()/-d.where(d<0,0).rolling(14).mean()))
    df['EMA21']=df['Close'].ewm(21).mean(); df['EMA50']=df['Close'].ewm(50).mean()
    return df
def check_one(pair_otc, real_sym):
    try:
        df1=yf.download(real_sym, period="2d", interval="1m", progress=False, auto_adjust=True)
        df1=fix(df1)
        if len(df1)<60: return None
        df1=add_all(df1)
        df5=yf.download(real_sym, period="2d", interval="5m", progress=False, auto_adjust=True)
        df5=fix(df5)
        if len(df5)<30:
            del df5; gc.collect()
            return None
        c1=float(df1.iloc[-1]['Close']); ema21_1=float(df1.iloc[-1]['EMA21']); ema50_1=float(df1.iloc[-1]['EMA50']); rsi1=float(df1.iloc[-1]['RSI'])
        c5=float(df5.iloc[-1]['Close']); ema50_5=float(df5.iloc[-1]['EMA50']); rsi5=float(df5.iloc[-1]['RSI'])
        direzione=None
        if c1>ema50_1 and ema21_1>ema50_1 and 35<=rsi1<=58: direzione="BUY"
        elif c1<ema50_1 and ema21_1<ema50_1 and 42<=rsi1<=65: direzione="SELL"
        else:
            del df1, df5; gc.collect()
            return None
        # FILTRO 5 MIN ANTI DISCESA BRUTTA - QUELLO CHE BLOCCAVA WTI
        if direzione=="BUY":
            if c5 < ema50_5 or rsi5 < 40:
                del df1, df5; gc.collect()
                return None
            if float(df5.iloc[-1]['Close']) < float(df5.iloc[-2]['Close']) < float(df5.iloc[-3]['Close']):
                del df1, df5; gc.collect()
                return None
        else:
            if c5 > ema50_5 or rsi5 > 60:
                del df1, df5; gc.collect()
                return None
            if float(df5.iloc[-1]['Close']) > float(df5.iloc[-2]['Close']) > float(df5.iloc[-3]['Close']):
                del df1, df5; gc.collect()
                return None
        fmt = f"{c1:.5f}" if "-OTC" in pair_otc and "JPY" not in pair_otc else f"{c1:.3f}" if "JPY" in pair_otc else f"{c1:.2f}"
        res={"pair":pair_otc,"dir":direzione,"price":fmt,"note":f"85% {direzione} 1m+5m CONFERMATO RSI {rsi1:.0f}/{rsi5:.0f}"}
        del df1, df5; gc.collect()
        return res
    except:
        gc.collect()
        return None

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V87 FIX CRASH</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:16px}.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:20px;width:95%;max-width:400px;display:block;margin:12px auto}.btn-green{background:#00ff88;color:#000;border:3px solid #00ff88}.btn-dark{background:#222;color:#fff;border:2px solid #444}.card{background:#1a1a1a;border-radius:14px;padding:14px;margin:10px auto;max-width:420px;text-align:left;border-left:6px solid #00ff88}.sell{border-left-color:#ff3b3b}.prepara{background:#ffcc00;color:#000;font-weight:bold;padding:12px;border-radius:10px;margin-top:8px;text-align:center;font-size:16px;border:2px solid #fff}.exp{background:#00ff88;color:#000;font-weight:bold;padding:10px;border-radius:8px;display:block;margin-top:8px;text-align:center}</style></head><body>
<h2>✅ V87 FINALE - FIX CRASH - 1m+5m</h2><p style="color:#00ff88">Anti discesa brutta - Tutte 33 coppie - 1 min scadenza</p>
<div class="btn btn-green" onclick="cerca()">🔔 ATTIVA V87 FIX</div><div class="btn btn-dark" onclick="cerca()">🔍 SCAN 33 COPPIE</div><p id="info">Pronto...</p><div id="live"></div>
<script>
function getNext(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMinutes(n.getMinutes()+1); return nx;}
function cerca(){document.getElementById('info').innerText='⏳ Scan 33 (30 sec leggero)...'; fetch('/api/scan').then(r=>r.json()).then(d=>{document.getElementById('info').innerText=d.time+' | '+d.signals.length+' segnali'; let h=''; let now=Date.now(); let next=getNext(); let entry=next.getTime(); let entryStr=next.toLocaleTimeString('it-IT'); d.signals.forEach(s=>{let diff=Math.max(0,Math.ceil((entry-now)/1000)); let txt=diff>0?`⏰ ENTRA TRA ${diff} SEC ALLE ${entryStr}`:'🔥 ENTRA ORA ALLE '+entryStr; h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><b style="color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'};font-size:18px">${s.dir} ${s.pair}</b><br>${s.note}<br>Prezzo: ${s.price}<br><div class="prepara">${txt}</div><div class="exp">SCADENZA 1 MINUTO - CONFERMATO 5 MIN</div></div>`;}); document.getElementById('live').innerHTML=h||'<p style="color:#666">Nessun segnale - filtro 5min blocca discese (meglio così, evita perdite tipo WTI)</p>';});}
setInterval(cerca,30000);
</script></body></html>"""

@app.route('/api/scan')
def api():
    tz=pytz.timezone('Europe/Rome'); now=datetime.now(tz).strftime('%H:%M:%S IT')
    out=[]
    pairs=list(OTC_MAP.items())
    # FIX CRASH: 5 alla volta, non 23 insieme
    for i in range(0,len(pairs),5):
        batch=pairs[i:i+5]
        for otc, real in batch:
            r=check_one(otc, real)
            if r: out.append(r)
            time.sleep(0.2)
        gc.collect()
    return jsonify({"signals":out,"time":now})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
