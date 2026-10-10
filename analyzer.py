# Analyzer.py - V11.0 - SOLO EMA - NO PINBAR - 3 MIN OTC
import os, time, threading
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd
from curl_cffi import requests as cffi_requests
from datetime import datetime, timedelta

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURGBP=X","GBPCHF=X","EURCHF=X","AUDCAD=X"]

app = Flask(__name__)
_YF = cffi_requests.Session(impersonate="chrome")
logs = []

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V11 EMA 3MIN</title>
<style>
body{background:#0f172a;color:#fff;font-family:Arial;padding:10px}
.card{background:#1e293b;padding:12px;border-radius:12px;margin:8px 0;border-left:5px solid #3b82f6}
.buy{border-left-color:#22c55e}.sell{border-left-color:#ef4444}
.b{padding:5px 10px;border-radius:6px;font-weight:bold}
.bu{background:#22c55e;color:#000}.se{background:#ef4444;color:#fff}
.t{color:#facc15;font-weight:bold;font-size:18px}
button{padding:14px;width:100%;border-radius:10px;border:none;font-weight:bold;background:#3b82f6;color:#fff;margin:5px 0}
table{width:100%;font-size:11px;border-collapse:collapse} td,th{padding:6px;border-bottom:1px solid #334155}
.small{color:#94a3b8;font-size:10px}
</style></head><body>
<h2>🔵 V11.0 - SOLO EMA 20/50 - 3 MIN - NO PINBAR</h2>
<div class="card">Trovati: {{logs|length}} | Scan: {{last}}<br><span class="small">EMA20 > EMA50 = Uptrend | Pullback su EMA + RSI 50-70 = BUY | Viceversa SELL</span></div>
<button onclick="fetch('/scan').then(r=>r.json()).then(d=>location.reload())">🔍 SCANNA EMA 3 MIN</button>
<div class="card"><h3>🔴 LIVE 3 MIN EMA</h3><div id="live"></div></div>
<div class="card"><h3>📜 STORICO EMA</h3><table>
<tr><th>Ora</th><th>Segnale</th><th>Prezzo</th><th>Motivo</th></tr>
{% for s in logs[::-1][:60] %}
<tr><td>{{s.time}}</td><td><span class="b {{'bu' if s.side=='BUY' else 'se'}}">{{s.side}} {{s.pair}}</span></td><td>{{s.price}}</td><td>{{s.why}}</td></tr>
{% endfor %}
</table></div>
<script>
let data={{logs|tojson}};
function render(){
 let h=''; let now=Date.now(); let seen={};
 data.slice().reverse().forEach(s=>{
  let diff=Math.floor((s.exp*1000-now)/1000);
  if(diff>0 && !seen[s.pair]){
   seen[s.pair]=1;
   h+=`<div class="card ${s.side=='BUY'?'buy':'sell'}"><span class="b ${s.side=='BUY'?'bu':'se'}">${s.side} ${s.pair}</span> ${s.price} <span class="t">00:0${Math.floor(diff/60)}:${String(diff%60).padStart(2,'0')}</span><br><span class="small">${s.why} scade ${s.exp_str}</span></div>`;
  }
 });
 if(!h) h='<small>Nessun live EMA - in trend ora</small>';
 document.getElementById('live').innerHTML=h;
}
setInterval(()=>{fetch('/api').then(r=>r.json()).then(d=>{data=d; render();})},4000);
setInterval(render,1000); render();
</script></body></html>
"""

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi_calc(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def ema_signal(sym):
    try:
        name=sym.replace("=X","")+" OTC"
        base=sym
        df=fix_df(yf.Ticker(base, session=_YF).history(period="3d", interval="1m"))
        if len(df)<60: return None
        df['e20']=df['Close'].ewm(span=20).mean()
        df['e50']=df['Close'].ewm(span=50).mean()
        df['e200']=df['Close'].ewm(span=200).mean()
        df['rsi']=rsi_calc(df['Close'])
        last=df.iloc[-1]
        cc=float(last['Close']); e20=float(last['e20']); e50=float(last['e50']); e200=float(last['e200']); r=float(last['rsi'])
        
        if "JPY" in name and (cc<50 or cc>250): return None
        if "JPY" not in name and (cc<0.5 or cc>5): return None

        # DISTANZA PER PULLBACK
        dist_e20 = abs(cc-e20)/cc

        # TREND FORTE: EMA 20 e 50 separati
        trend_up = e20 > e50 and cc > e20 and e50 > e200
        trend_down = e20 < e50 and cc < e20 and e50 < e200

        # PULLBACK VICINO EMA20 (0.05% - 0.20% di distanza) = rimbalzo
        is_pullback = 0.0003 < dist_e20 < 0.0025

        if trend_up and is_pullback and 48 <= r <= 68 and float(last['Close']) > float(last['Open']):
            return {"pair":name,"side":"BUY","price":round(cc,5 if "JPY" not in name else 3),"why":f"UPTREND EMA20>{round(e20,5)} > EMA50 | Pullback {round(dist_e20*100,2)}% + RSI{int(r)}","time":datetime.now().strftime("%H:%M:%S"),"exp":time.time()+180,"exp_str":(datetime.now()+timedelta(minutes=3)).strftime("%H:%M:%S")}
        if trend_down and is_pullback and 32 <= r <= 52 and float(last['Close']) < float(last['Open']):
            return {"pair":name,"side":"SELL","price":round(cc,5 if "JPY" not in name else 3),"why":f"DOWNTREND EMA20<{round(e20,5)} < EMA50 | Pullback {round(dist_e20*100,2)}% + RSI{int(r)}","time":datetime.now().strftime("%H:%M:%S"),"exp":time.time()+180,"exp_str":(datetime.now()+timedelta(minutes=3)).strftime("%H:%M:%S")}
    except Exception as e:
        print(e)
        return None
    return None

def loop():
    while True:
        for s in PAIRS:
            if any(x['pair'].startswith(s.replace("=X","")) and x['exp']>time.time() for x in logs): continue
            sig=ema_signal(s)
            if sig:
                logs.append(sig)
                if len(logs)>150: logs.pop(0)
        time.sleep(30)

@app.route('/')
def home(): return render_template_string(HTML, logs=logs, last=datetime.now().strftime("%H:%M:%S"))
@app.route('/scan')
def scan():
    out=[]
    for s in PAIRS:
        if any(x['pair'].startswith(s.replace("=X","")) and x['exp']>time.time() for x in logs): continue
        sig=ema_signal(s)
        if sig:
            logs.append(sig); out.append(sig)
    return jsonify(out)
@app.route('/api')
def api(): return jsonify(logs)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
