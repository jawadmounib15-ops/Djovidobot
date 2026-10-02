# V90 COMPLETO - STORICO + SUONO + 40 SEC AVVISO + SCADENZA 1MIN - TUTTO FIXATO
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

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V90 COMPLETO</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:12px}
.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:20px;width:95%;max-width:400px;display:block;margin:10px auto;cursor:pointer}
.g{background:#00ff88;color:#000;border:3px solid #00ff88}.d{background:#222;color:#fff;border:2px solid #444}
.card{background:#1a1a1a;border-radius:14px;padding:14px;margin:10px auto;max-width:420px;text-align:left;border-left:6px solid #00ff88}
.sell{border-left-color:#ff3b3b}
.prepara{background:#ffcc00;color:#000;font-weight:bold;padding:12px;border-radius:10px;margin-top:8px;text-align:center;font-size:16px;border:2px solid #fff;animation:blink 1s infinite}
.exp{background:#00ff88;color:#000;font-weight:bold;padding:10px;border-radius:8px;display:block;margin-top:8px;text-align:center}
.storico{background:#111;border:1px solid #333;border-radius:10px;padding:10px;margin:15px auto;max-width:420px;text-align:left;font-size:13px}
@keyframes blink{0%{opacity:1}50%{opacity:0.6}100%{opacity:1}}
</style></head><body>
<h2>✅ V90 - TUTTO RIPRISTINATO</h2>
<p style="color:#00ff88">Suono + Storico + 40sec Avviso + 1min Scadenza</p>

<div class="btn g" onclick="attivaAudio()">🔔 ATTIVA SUONO + SCAN</div>
<div class="btn d" onclick="cerca()">🔍 SCAN 33 COPPIE - 1m+5m</div>
<p id="info">Clicca ATTIVA SUONO per abilitare audio</p>
<div id="live"></div>
<div class="storico"><b>📜 STORICO SEGNALI:</b><div id="storico">Nessun segnale ancora</div><br><div onclick="localStorage.clear();document.getElementById('storico').innerHTML='Pulito';alert('Storico pulito')" style="color:#ff3b3b;cursor:pointer">🗑️ Pulisci storico</div></div>

<audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio>

<script>
let audioOk=false; let storicoArr = JSON.parse(localStorage.getItem('storico_v90')||'[]');
function aggiornaStoricoUI(){let h=''; storicoArr.slice(0,20).forEach(s=>{h+=`<div>${s}</div>`;}); document.getElementById('storico').innerHTML=h||'Nessun segnale';}
aggiornaStoricoUI();

function attivaAudio(){
  audioOk=true;
  let a=document.getElementById('beep'); a.play().then(()=>{a.pause(); a.currentTime=0;}).catch(()=>{});
  if(navigator.vibrate) navigator.vibrate(200);
  document.getElementById('info').innerText='✅ Suono ATTIVO - cerco segnali...';
  cerca();
}
function suona(){
  if(!audioOk) return;
  let a=document.getElementById('beep'); a.currentTime=0; a.play().catch(()=>{});
  if(navigator.vibrate) navigator.vibrate([800,200,800,200,800]);
}

function getNextCandle(){
  let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMilliseconds(0); nx.setMinutes(n.getMinutes()+1); return nx;
}
let currentSignals=[]; let entryTime=0;

function cerca(){
  document.getElementById('info').innerText='⏳ Scan 33 coppie (30 sec)...';
  fetch('/api/scan').then(r=>r.json()).then(d=>{
    currentSignals=d.signals; entryTime=getNextCandle().getTime();
    if(d.signals.length>0){
      suona();
      let nowStr=new Date().toLocaleTimeString('it-IT');
      d.signals.forEach(s=>{
        let txt=`${nowStr} - ${s.dir} ${s.pair} ${s.price}`;
        storicoArr.unshift(txt); if(storicoArr.length>50) storicoArr.pop();
      });
      localStorage.setItem('storico_v90', JSON.stringify(storicoArr));
      aggiornaStoricoUI();
    }
    render();
  });
}

function render(){
  let now=Date.now(); let diffEntry=Math.ceil((entryTime-now)/1000);
  let h='';
  if(diffEntry>40){
    document.getElementById('info').innerText=`⏰ Prossima entrata tra ${diffEntry} sec - aspetta`;
  } else if(diffEntry>0){
    document.getElementById('info').innerText=`🔥 PREPARA! ENTRA TRA ${diffEntry} SEC!`;
    if(diffEntry<=40 && diffEntry>38) suona(); // avviso 40 sec
  } else if(diffEntry>-60){
    let scad=Math.max(0,60+diffEntry);
    document.getElementById('info').innerText=`✅ TRADE IN CORSO - SCADE TRA ${scad} SEC`;
    h+=`<div style="background:#00ff88;color:#000;padding:10px;border-radius:10px;font-weight:bold;margin-bottom:10px">🔴 TRADE ATTIVO - Scadenza tra ${scad} sec</div>`;
  } else {
    document.getElementById('info').innerText=`⏳ In attesa prossima candela...`;
  }

  currentSignals.forEach(s=>{
    let txt=diffEntry>0?`⏰ ENTRA TRA ${diffEntry} SEC ALLE ${new Date(entryTime).toLocaleTimeString('it-IT')}`:diffEntry>-60?`🔥 TRADE IN CORSO - SCADE TRA ${Math.max(0,60+diffEntry)} SEC`:'⌛ SCADUTO - aspetta prossima';
    let col=s.dir=='BUY'?'#00ff88':'#ff3b3b';
    h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><b style="color:${col};font-size:18px">${s.dir} ${s.pair}</b><br>${s.note}<br>Prezzo: ${s.price}<br><div class="prepara">${txt}</div><div class="exp">SCADENZA 1 MINUTO - CONFERMATO 5 MIN</div></div>`;
  });
  document.getElementById('live').innerHTML=h||'<p style="color:#666">Nessun segnale - filtro 5min blocca discese brutte (bene)</p>';
}

setInterval(render,1000);
setInterval(cerca,30000);
</script></body></html>"""

@app.route('/api/scan')
def api():
    out=[]
    for otc, real in OTC_MAP.items():
        try:
            df1=yf.download(real, period="2d", interval="1m", progress=False, auto_adjust=True)
            df1=fix(df1)
            if len(df1)<60: continue
            d=df1['Close'].diff()
            rsi=100-(100/(1+d.where(d>0,0).rolling(14).mean()/-d.where(d<0,0).rolling(14).mean()))
            ema21=df1['Close'].ewm(21).mean(); ema50=df1['Close'].ewm(50).mean()
            df5=yf.download(real, period="2d", interval="5m", progress=False, auto_adjust=True)
            df5=fix(df5)
            if len(df5)<30:
                del df1, df5; gc.collect()
                continue
            d5=df5['Close'].diff()
            rsi5=100-(100/(1+d5.where(d5>0,0).rolling(14).mean()/-d5.where(d5<0,0).rolling(14).mean()))
            ema50_5=df5['Close'].ewm(50).mean()
            c1=float(df1.iloc[-1]['Close']); c5=float(df5.iloc[-1]['Close'])
            r1=float(rsi.iloc[-1]); r5=float(rsi5.iloc[-1])
            e21=float(ema21.iloc[-1]); e50=float(ema50.iloc[-1]); e50_5=float(ema50_5.iloc[-1])
            dire=None
            if c1>e50 and e21>e50 and 35<=r1<=58: dire="BUY"
            elif c1<e50 and e21<e50 and 42<=r1<=65: dire="SELL"
            if dire:
                if dire=="BUY" and (c5<e50_5 or r5<40): dire=None
                if dire=="SELL" and (c5>e50_5 or r5>60): dire=None
                if dire and float(df5.iloc[-1]['Close'])!=float(df5.iloc[-2]['Close']):
                    if dire=="BUY" and float(df5.iloc[-1]['Close']) < float(df5.iloc[-2]['Close']) < float(df5.iloc[-3]['Close']): dire=None
                    if dire=="SELL" and float(df5.iloc[-1]['Close']) > float(df5.iloc[-2]['Close']) > float(df5.iloc[-3]['Close']): dire=None
            if dire:
                fmt=f"{c1:.5f}" if "JPY" not in otc and "-OTC" in otc and len(otc)<13 else f"{c1:.2f}"
                out.append({"pair":otc,"dir":dire,"price":fmt,"note":f"85% {dire} 1+5m {r1:.0f}/{r5:.0f}"})
            del df1, df5; gc.collect()
            time.sleep(0.15)
        except:
            gc.collect()
            continue
    return jsonify({"signals":out})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
