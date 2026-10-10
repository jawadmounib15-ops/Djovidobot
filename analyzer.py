# Analyzer.py - V13.0 - ULTRA ALLARGATO - 3 MIN - TROVA SICURO
import os, time, threading
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd
from curl_cffi import requests as cffi_requests
from datetime import datetime, timedelta

# RIDOTTO A 8 COPPIE PER NON BLOCCARE RENDER
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","GBPJPY=X","EURJPY=X","AUDJPY=X","EURGBP=X","USDCHF=X"]

app = Flask(__name__)
_YF = cffi_requests.Session(impersonate="chrome")
logs = []
last_scan = "Avvio V13..."

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V13 ULTRA</title>
<style>
body{background:#0f172a;color:#fff;font-family:Arial;padding:10px;margin:0}
.card{background:#1e293b;padding:12px;border-radius:12px;margin:8px 0;border-left:5px solid #22c55e}
.sell{border-left-color:#ef4444}
.b{padding:5px 10px;border-radius:6px;font-weight:bold;display:inline-block}
.bu{background:#22c55e;color:#000}.se{background:#ef4444;color:#fff}
.t{color:#facc15;font-weight:bold;font-size:16px}
button{padding:18px;width:100%;border-radius:12px;border:none;font-weight:bold;background:#22c55e;color:#000;font-size:17px;margin:8px 0}
table{width:100%;font-size:11px;border-collapse:collapse} td,th{padding:6px;border-bottom:1px solid #334155}
.small{color:#94a3b8;font-size:11px}
</style></head><body>
<h2>🟢 V13.0 - ULTRA ALLARGATO 3MIN - TROVA SICURO</h2>
<div class="card">Trovati: {{logs|length}} | {{last}}<br><span class="small">ULTRA: RSI 55+ SELL / 45- BUY | EMA 0.05% | 8 coppie veloci</span></div>
<button onclick="fetch('/scan').then(r=>r.json()).then(d=>{location.reload()})">🔍 SCANNA ORA - ULTRA</button>
<div class="card"><h3>🔴 LIVE 3 MIN</h3><div id="live">Scannerizzo...</div></div>
<div class="card"><h3>📜 STORICO</h3><table><tr><th>Ora</th><th>Segnale</th><th>Prezzo</th><th>Motivo</th></tr>
{% for s in logs[::-1][:80] %}
<tr><td>{{s.time}}</td><td><span class="b {{'bu' if s.side=='BUY' else 'se'}}">{{s.side}} {{s.pair}}</span></td><td>{{s.price}}</td><td>{{s.why}}</td></tr>
{% endfor %}</table></div>
<script>
let data={{logs|tojson}};
function render(){
 let h=''; let now=Date.now(); let seen={};
 data.slice().reverse().forEach(s=>{
  let diff=Math.floor((s.exp*1000-now)/1000);
  if(diff>0 && !seen[s.pair]){
   seen[s.pair]=1;
   let m=Math.floor(diff/60); let sec=diff%60;
   h+=`<div class="card ${s.side=='BUY'?'':'sell'}"><span class="b ${s.side=='BUY'?'bu':'se'}">${s.side} ${s.pair}</span> ${s.price} <span class="t">00:0${m}:${String(sec).padStart(2,'0')}</span><br><span class="small">${s.why}</span></div>`;
  }
 });
 if(!h) h='<small>Clicca SCANNA - trova in 5 sec</small>';
 document.getElementById('live').innerHTML=h;
}
setInterval(()=>{fetch('/api').then(r=>r.json()).then(d=>{data=d; render();})},3000);
setInterval(render,1000); render();
</script></body></html>
"""

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def ultra_signal(sym):
    try:
        name=sym.replace("=X","")+" OTC"
        # 2m invece di 1m - yfinance su Render va meglio
        df=fix_df(yf.Ticker(sym, session=_YF).history(period="1d", interval="2m"))
        if len(df)<30: return None
        df['e20']=df['Close'].ewm(span=20).mean()
        df['rsi']=rsi(df['Close'])
        last=df.iloc[-1]
        cc=float(last['Close']); e20=float(last['e20']); r=float(last['rsi'])
        if "JPY" in name and (cc<50 or cc>300): return None
        if "JPY" not in name and (cc<0.5 or cc>5): return None

        # ULTRA ALLARGATO - TROVA SICURO
        # 1) RSI semplice
        if r >= 55:
            return {"pair":name,"side":"SELL","price":round(cc,5 if "JPY" not in name else 3),"why":f"RSI {int(r)} >=65 SELL ULTRA","time":datetime.now().strftime("%H:%M:%S"),"exp":time.time()+180,"exp_str":(datetime.now()+timedelta(minutes=3)).strftime("%H:%M:%S")}
        if r <= 45:
            return {"pair":name,"side":"BUY","price":round(cc,5 if "JPY" not in name else 3),"why":f"RSI {int(r)} <=35 BUY ULTRA","time":datetime.now().strftime("%H:%M:%S"),"exp":time.time()+180,"exp_str":(datetime.now()+timedelta(minutes=3)).strftime("%H:%M:%S")}
        # 2) Se RSI neutro, guarda EMA
        if cc > e20*1.0005:
            return {"pair":name,"side":"SELL","price":round(cc,5 if "JPY" not in name else 3),"why":f"Sopra EMA20 {round((cc/e20-1)*100,2)}% SELL","time":datetime.now().strftime("%H:%M:%S"),"exp":time.time()+180,"exp_str":(datetime.now()+timedelta(minutes=3)).strftime("%H:%M:%S")}
        if cc < e20*0.9995:
            return {"pair":name,"side":"BUY","price":round(cc,5 if "JPY" not in name else 3),"why":f"Sotto EMA20 {round((cc/e20-1)*100,2)}% BUY","time":datetime.now().strftime("%H:%M:%S"),"exp":time.time()+180,"exp_str":(datetime.now()+timedelta(minutes=3)).strftime("%H:%M:%S")}
    except Exception as e:
        print(f"ERR {sym} {e}")
        return None
    return None

def loop():
    global last_scan
    time.sleep(4)
    while True:
        found=0
        for s in PAIRS[:4]: # scanna 4 per volta per non bloccare
            if any(x['pair'].startswith(s.replace("=X","")) and x['exp']>time.time() for x in logs): continue
            sig=ultra_signal(s)
            if sig:
                logs.append(sig)
                if len(logs)>150: logs.pop(0)
                found+=1
        last_scan=datetime.now().strftime("%H:%M:%S")+f" - trovati {found} - ULTRA"
        time.sleep(20)

@app.route('/')
def home(): return render_template_string(HTML, logs=logs, last=last_scan)
@app.route('/scan')
def scan():
    out=[]
    for s in PAIRS:
        if any(x['pair'].startswith(s.replace("=X","")) and x['exp']>time.time() for x in logs): continue
        sig=ultra_signal(s)
        if sig:
            logs.append(sig)
            out.append(sig)
            if len(out)>=3: break # max 3 per scan per non fare casino
    return jsonify(out)
@app.route('/api')
def api(): return jsonify(logs)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
