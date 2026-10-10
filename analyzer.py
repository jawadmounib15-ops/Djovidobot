# Analyzer.py - V12.1 - AL CONTRARIO ALLARGATO - 3 MIN
import os, time, threading
from flask import Flask, render_template_string, jsonify
import yfinance as yf
import pandas as pd
from curl_cffi import requests as cffi_requests
from datetime import datetime, timedelta

PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","GBPJPY=X","AUDJPY=X","EURGBP=X","GBPCHF=X","EURCHF=X","AUDCAD=X","CADJPY=X","CHFJPY=X","NZDJPY=X"]

app = Flask(__name__)
_YF = cffi_requests.Session(impersonate="chrome")
logs = []
last_scan = "Avvio..."

HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V12.1 ALLARGATO</title>
<style>
body{background:#0f172a;color:#fff;font-family:Arial;padding:10px;margin:0}
.card{background:#1e293b;padding:12px;border-radius:12px;margin:8px 0;border-left:5px solid #f97316}
.buy{border-left-color:#22c55e}.sell{border-left-color:#ef4444}
.b{padding:5px 10px;border-radius:6px;font-weight:bold;display:inline-block}
.bu{background:#22c55e;color:#000}.se{background:#ef4444;color:#fff}
.t{color:#facc15;font-weight:bold}
button{padding:16px;width:100%;border-radius:12px;border:none;font-weight:bold;background:#f97316;color:#fff;font-size:16px;margin:6px 0}
table{width:100%;font-size:11px;border-collapse:collapse} td,th{padding:6px;border-bottom:1px solid #334155;text-align:left}
.small{color:#94a3b8;font-size:10px}
h2{margin:8px 0}
</style></head><body>
<h2>🔄 V12.1 - CONTRARIO ALLARGATO 3MIN</h2>
<div class="card">Trovati: {{logs|length}} | Ultimo: {{last}}<br><span class="small">ALLARGATO: RSI 60+ = SELL | RSI 40- = BUY | Dist EMA >0.15% | 15 coppie</span></div>
<button onclick="fetch('/scan').then(r=>r.json()).then(d=>location.reload())">🔍 SCANNA ORA - ALLARGATO</button>
<div class="card"><h3>🔴 LIVE 3 MIN</h3><div id="live">Carico...</div></div>
<div class="card"><h3>📜 STORICO</h3><table><tr><th>Ora</th><th>Segnale</th><th>Prezzo</th><th>Perché</th></tr>
{% for s in logs[::-1][:70] %}
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
   h+=`<div class="card ${s.side=='BUY'?'buy':'sell'}"><span class="b ${s.side=='BUY'?'bu':'se'}">${s.side} ${s.pair}</span> ${s.price} <span class="t">00:0${m}:${String(sec).padStart(2,'0')}</span><br><span class="small">${s.why} - scade ${s.exp_str}</span></div>`;
  }
 });
 if(!h) h='<small>Nessun live - clicca SCANNA, trova entro 20 sec</small>';
 document.getElementById('live').innerHTML=h;
}
setInterval(()=>{fetch('/api').then(r=>r.json()).then(d=>{data=d; render();})},4000);
setInterval(render,1000); render();
</script></body></html>
"""

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    rs=g/l
    return 100-(100/(1+rs))

def signal_allargato(sym):
    try:
        name=sym.replace("=X","")+" OTC"
        df=fix_df(yf.Ticker(sym, session=_YF).history(period="2d", interval="1m"))
        if len(df)<50: return None
        df['e20']=df['Close'].ewm(span=20).mean()
        df['e50']=df['Close'].ewm(span=50).mean()
        df['rsi']=rsi(df['Close'])
        last=df.iloc[-1]
        cc=float(last['Close']); e20=float(last['e20']); e50=float(last['e50']); r=float(last['rsi'])
        
        if "JPY" in name:
            if cc<50 or cc>300: return None
        else:
            if cc<0.5 or cc>5: return None

        dist=abs(cc-e20)/cc

        # ALLARGATO: basta RSI + distanza
        if r >= 60 and dist > 0.0015:  # 0.15% lontano
            return {"pair":name,"side":"SELL","price":round(cc,5 if "JPY" not in name else 3),"why":f"ALLARGATO SELL RSI {int(r)} >60 Dist {round(dist*100,2)}%","time":datetime.now().strftime("%H:%M:%S"),"exp":time.time()+180,"exp_str":(datetime.now()+timedelta(minutes=3)).strftime("%H:%M:%S")}
        if r <= 40 and dist > 0.0015:
            return {"pair":name,"side":"BUY","price":round(cc,5 if "JPY" not in name else 3),"why":f"ALLARGATO BUY RSI {int(r)} <40 Dist {round(dist*100,2)}%","time":datetime.now().strftime("%H:%M:%S"),"exp":time.time()+180,"exp_str":(datetime.now()+timedelta(minutes=3)).strftime("%H:%M:%S")}
        
        # Se molto esteso anche senza RSI estremo
        if dist > 0.008 and float(last['Close']) < float(last['Open']):
            return {"pair":name,"side":"SELL","price":round(cc,5 if "JPY" not in name else 3),"why":f"Estensione 0.8% SELL","time":datetime.now().strftime("%H:%M:%S"),"exp":time.time()+180,"exp_str":(datetime.now()+timedelta(minutes=3)).strftime("%H:%M:%S")}
        if dist > 0.008 and float(last['Close']) > float(last['Open']):
            return {"pair":name,"side":"BUY","price":round(cc,5 if "JPY" not in name else 3),"why":f"Estensione 0.8% BUY","time":datetime.now().strftime("%H:%M:%S"),"exp":time.time()+180,"exp_str":(datetime.now()+timedelta(minutes=3)).strftime("%H:%M:%S")}

    except Exception as e:
        print(e)
        return None
    return None

def loop():
    global last_scan
    time.sleep(3)
    while True:
        try:
            found=0
            for s in PAIRS:
                if any(x['pair'].startswith(s.replace("=X","")) and x['exp']>time.time() for x in logs): continue
                sig=signal_allargato(s)
                if sig:
                    logs.append(sig)
                    if len(logs)>150: logs.pop(0)
                    found+=1
            last_scan=datetime.now().strftime("%H:%M:%S")+f" - trovati {found}"
        except: pass
        time.sleep(25)

@app.route('/')
def home():
    global last_scan
    return render_template_string(HTML, logs=logs, last=last_scan)
@app.route('/scan')
def scan():
    out=[]
    for s in PAIRS:
        if any(x['pair'].startswith(s.replace("=X","")) and x['exp']>time.time() for x in logs): continue
        sig=signal_allargato(s)
        if sig:
            logs.append(sig)
            out.append(sig)
    return jsonify(out)
@app.route('/api')
def api(): return jsonify(logs)

threading.Thread(target=loop, daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
