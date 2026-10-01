# ANALYZER.PY V68 LARGO POCO + STORICO
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","EURAUD=X","GBPAUD=X","EURNZD=X","GBPNZD=X","NZDUSD=X","NZDCAD=X"]

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def check_pair(sym):
    try:
        df_h = yf.download(sym, period="20d", interval="60m", progress=False)
        df_h = fix_df(df_h)
        if len(df_h) < 60: return None
        df_4h = df_h.resample('4h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
        if len(df_4h) < 12: return None
        last_12 = df_4h.iloc[-12:]; rh=float(last_12['High'].max()); rl=float(last_12['Low'].min()); rs=rh-rl
        if rs==0: return None
        df_5 = yf.download(sym, period="5d", interval="5m", progress=False)
        df_5 = fix_df(df_5)
        if len(df_5)<20: return None
        last=df_5.iloc[-1]; o=float(last['Open']); h=float(last['High']); l=float(last['Low']); c=float(last['Close']); body=abs(c-o)
        up=h-max(o,c); down=min(o,c)-l
        # LARGO POCO: 2.0x invece di 2.5x, body 0.50 invece di 0.45
        if body==0 or max(up,down) < body*2.0 or body > (h-l)*0.50: return None
        # LARGO POCO: 0.18 invece di 0.12
        if abs(c-rl)/rs < 0.18 and l <= rl*1.0005 and c > rl and down > up*0.8:
            return {"pair":sym.replace("=X",""),"dir":"BUY","price":f"{c:.5f}","note":f"Rimbalzo Low 4H {down/body:.1f}x"}
        if abs(c-rh)/rs < 0.18 and h >= rh*0.9995 and c < rh and up > down*0.8:
            return {"pair":sym.replace("=X",""),"dir":"SELL","price":f"{c:.5f}","note":f"Rifiuto High 4H {up/body:.1f}x"}
    except: return None

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V68 LARGO</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:20px}
.btn{background:#00ff88;color:#000;border:none;padding:18px;border-radius:14px;font-weight:bold;font-size:20px;width:90%;max-width:360px;display:block;margin:12px auto}
.card{background:#1a1a1a;border-radius:14px;padding:16px;margin:12px auto;max-width:380px;text-align:left;border-left:5px solid #00ff88;position:relative}
.exp{background:#00ff88;color:#000;font-weight:bold;padding:6px 10px;border-radius:8px;display:inline-block;margin-top:8px;font-size:16px}
.sell{border-left-color:#ff3b3b} .old{opacity:0.6;background:#222;border-left-color:#666}
.badge{position:absolute;top:10px;right:10px;font-size:11px;padding:3px 8px;border-radius:6px;font-weight:bold}
.live{background:#ffcc00;color:#000} .scad{background:#555;color:#fff}
</style></head><body>
<h1>🔔 V68 LARGO POCO + 10 MIN</h1>
<button class="btn" id="b1" onclick="attiva()">🔔 ATTIVA ALLARME FORTE</button>
<button class="btn" style="background:#222;color:#fff;border:1px solid #444" onclick="cerca()">🔍 SCAN ORA</button>
<p id="info">Attiva e lascia aperto...</p><div id="live"></div>
<hr style="border:0;border-top:1px solid #333;margin:20px 0">
<h3 style="color:#888">📜 STORICO</h3><div id="hist"></div>
<button class="btn" style="background:#333;color:#999;font-size:14px;padding:10px" onclick="localStorage.clear();history=[];renderHist();">🗑️ Pulisci storico</button>
<audio id="s1" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<audio id="s2" src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" preload="auto"></audio>
<script>
let ok=false; let a1=document.getElementById('s1'), a2=document.getElementById('s2');
let history = JSON.parse(localStorage.getItem('v68hist')||'[]');
function attiva(){
 ok=true; a1.play().then(()=>{a1.pause();a1.currentTime=0}).catch(()=>{}); a2.play().then(()=>{a2.pause();a2.currentTime=0}).catch(()=>{});
 document.getElementById('b1').innerHTML='✅ ALLARME ATTIVO - LASCIA APERTO'; document.getElementById('b1').style.background='#ffcc00';
 if(Notification && Notification.permission!='granted'){Notification.requestPermission();}
 renderHist();
}
function suona(){if(!ok)return; a1.currentTime=0;a1.play(); setTimeout(()=>{a2.currentTime=0;a2.play()},400); setTimeout(()=>{a1.currentTime=0;a1.play()},900); if(navigator.vibrate) navigator.vibrate([1000,300,1000,300,1000]); if(Notification&&Notification.permission=='granted'){new Notification('🔔 SEGNALE V68!',{body:'Entra 10 MIN'});}}
function renderHist(){
 let h=''; [...history].reverse().forEach(s=>{
   h+=`<div class="card old ${s.dir=='SELL'?'sell':''}"><span class="badge scad">SCADUTO - ${s.time}</span><b style="color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b><br>${s.note}<br>Prezzo: ${s.price}</div>`;
 });
 document.getElementById('hist').innerHTML = h || '<p style="color:#555">Nessun segnale ancora</p>';
}
function cerca(){fetch('/api/scan').then(r=>r.json()).then(d=>{
 document.getElementById('info').innerText=d.time+' | Trovati: '+d.signals.length+' | Storico: '+history.length;
 let h=''; let nuovi=0;
 d.signals.forEach(s=>{
   let id=s.pair+'_'+d.time.slice(0,5);
   if(!history.find(x=>x.id==id)){history.push({id:id,pair:s.pair,dir:s.dir,price:s.price,note:s.note,time:d.time}); nuovi++;}
   let cls=s.dir=='SELL'?'card sell':'card';
   h+=`<div class="${cls}"><span class="badge live">LIVE ORA!</span><b style="font-size:20px;color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b><br>${s.note}<br>Prezzo: ${s.price}<br><span class="exp">⏱️ SCADENZA: 10 MINUTI</span></div>`;
 });
 if(nuovi>0){localStorage.setItem('v68hist',JSON.stringify(history.slice(-30))); suona(); renderHist();}
 document.getElementById('live').innerHTML=h;
});}
setInterval(cerca,60000); window.onload=()=>{renderHist(); cerca();}
</script></body></html>"""

@app.route('/api/scan')
def api():
    tz=pytz.timezone('Europe/Rome'); now=datetime.now(tz).strftime('%H:%M:%S IT')
    out=[]
    with ThreadPoolExecutor(max_workers=18) as ex:
        futs={ex.submit(check_pair,s):s for s in PAIRS}
        for f in as_completed(futs):
            r=f.result()
            if r: out.append(r)
    return jsonify({"signals":out,"time":now})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
