# ANALYZER.PY V74.2 - STORICO + VECCHIO/NUOVO + SCADENZA 3MIN 70%
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime, timedelta
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","GBPAUD=X","EURNZD=X","CADCHF=X","CADJPY=X","AUDCAD=X","AUDCHF=X","CHFJPY=X","GBPNZD=X","NZDCAD=X"]

TIMEFRAMES = {"1M":{"period":"1d","interval":"1m"},"5M":{"period":"2d","interval":"5m"},"15M":{"period":"5d","interval":"15m"}}

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def rsi_calc(series, period=14):
    delta=series.diff(); gain=delta.where(delta>0,0).rolling(window=period).mean(); loss=-delta.where(delta<0,0).rolling(window=period).mean()
    rs=gain/loss; return 100-(100/(1+rs))

def check_single_tf(sym, tf_name):
    try:
        cfg=TIMEFRAMES[tf_name]
        df=yf.download(sym, period=cfg["period"], interval=cfg["interval"], progress=False)
        df=fix_df(df)
        if len(df)<70: return None
        df['RSI']=rsi_calc(df['Close'],14)
        highs=df['High'].values; lows=df['Low'].values
        swing_high=swing_low=None
        for i in range(len(df)-25,len(df)-5):
            if highs[i]==max(highs[i-5:i+6]): swing_high=float(highs[i])
            if lows[i]==min(lows[i-5:i+6]): swing_low=float(lows[i])
        if swing_high is None or swing_low is None: return None
        last=df.iloc[-1]; prev=df.iloc[-2]
        c=float(last['Close']); c_prev=float(prev['Close']); rsi_now=float(last['RSI'])
        range_sw=swing_high-swing_low
        if range_sw==0: return None
        last_20=df.iloc[-20:]
        range_20_pct=(float(last_20['High'].max())-float(last_20['Low'].min()))/c
        if range_20_pct<0.0009: return None
        dist_high=abs(c-swing_high)/range_sw; dist_low=abs(c-swing_low)/range_sw
        if dist_low<0.132 and c>c_prev and rsi_now<44: return "BUY",rsi_now
        if dist_high<0.132 and c<c_prev and rsi_now>56: return "SELL",rsi_now
    except: return None
    return None

def check_pair_multitf(sym):
    results={}
    for tf in TIMEFRAMES:
        r=check_single_tf(sym,tf)
        if r: results[tf]=r
    if not results: return None
    dirs=[v[0] for v in results.values()]; buy=dirs.count("BUY"); sell=dirs.count("SELL")
    if buy>=2 or (buy==1 and sell==0): final_dir="BUY"
    elif sell>=2 or (sell==1 and buy==0): final_dir="SELL"
    else: return None
    num_tf=len(results)
    if num_tf==1: expiry="00:01:00"; conf="55%"
    else: expiry="00:03:00"; conf="70%"
    tf_text=" + ".join([f"{k}:{v[0]} RSI {v[1]:.0f}" for k,v in results.items()])
    return {"pair":sym.replace("=X",""),"dir":final_dir,"expiry":expiry,"confidence":conf,"note":tf_text,"confluence":f"{buy}B/{sell}S","tfs":list(results.keys())}

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V74.2 STORICO</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:12px}
.btn{background:#00ff88;color:#000;border:none;padding:14px;border-radius:12px;font-weight:bold;font-size:16px;width:95%;max-width:380px;display:block;margin:7px auto}
.card{background:#1a1a1a;border-radius:14px;padding:12px;margin:8px auto;max-width:420px;text-align:left;border-left:5px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}.old{opacity:0.55;background:#111;border-left-color:#555}
.badge{position:absolute;top:8px;right:8px;font-size:10px;padding:4px 8px;border-radius:6px;font-weight:bold}
.live{background:#ffcc00;color:#000}.vecchio{background:#ff3b3b;color:#fff}.nuovo{background:#00ff88;color:#000;animation:blink 1s infinite}
@keyframes blink{50%{opacity:0.5}}
.tf{background:#222;color:#00ff88;font-size:11px;padding:2px 6px;border-radius:4px;margin-right:4px}
.exp{background:#00ff88;color:#000;font-weight:bold;padding:5px 9px;border-radius:8px;display:inline-block;margin-top:6px;font-size:13px}
.exp3{background:#ffcc00;color:#000;font-weight:bold;padding:6px 10px;border-radius:8px;display:inline-block;margin-top:6px;font-size:14px}
.timer{color:#ffcc00;font-weight:bold;font-size:12px}
.hist-title{color:#888;margin-top:20px;border-top:1px solid #333;padding-top:12px}
</style></head><body>
<h2>📊 V74.2 - STORICO + SCADENZA</h2>
<p style="color:#ffcc00">3MIN 70% + Vecchio/Nuovo</p>
<button class="btn" id="b1" onclick="attiva()">🔔 ATTIVA ALLARME</button>
<button class="btn" style="background:#222;color:#fff;border:1px solid #444" onclick="cerca()">🔍 SCAN ORA</button>
<p id="info">...</p>
<div id="live"></div>
<h3 class="hist-title">📜 STORICO SEGNALI (oggi)</h3>
<div id="hist"></div>
<button class="btn" style="background:#333;color:#999;font-size:12px;padding:8px" onclick="clearHist()">🗑️ Pulisci storico</button>
<audio id="s1" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
let ok=false; let history=JSON.parse(localStorage.getItem('v742_hist')||'[]');
let liveSignals={}; // pair -> timestamp

function attiva(){ok=true; document.getElementById('b1').innerHTML='✅ ATTIVO - STORICO ON'; document.getElementById('b1').style.background='#ffcc00'; let a=document.getElementById('s1'); a.play().then(()=>{a.pause();a.currentTime=0}).catch(()=>{}); if(Notification&&Notification.permission!='granted')Notification.requestPermission(); renderHist();}
function suona(){if(!ok)return; document.getElementById('s1').currentTime=0; document.getElementById('s1').play(); if(navigator.vibrate) navigator.vibrate([500,200,500]);}

function renderHist(){
 let h=''; [...history].reverse().slice(0,50).forEach(s=>{
  let cls=s.dir=='SELL'?'card old sell':'card old';
  let age=Math.floor((Date.now()-s.ts)/60000);
  let ageTxt=age<=3?'🟢 NUOVO - '+age+' min fa':'🔴 VECCHIO - '+age+' min fa - SCADUTO';
  h+=`<div class="${cls}"><span class="badge ${age<=3?'nuovo':'vecchio'}">${age<=3?'NUOVO':'VECCHIO'}</span><b style="color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b> - ${s.expiry}<br><span style="font-size:11px;color:#aaa">${s.note}</span><br><span class="timer">${ageTxt}</span><br><span style="font-size:11px;color:#666">${s.time}</span></div>`;
 });
 document.getElementById('hist').innerHTML=h||'<p style="color:#555">Nessuno storico</p>';
}

function clearHist(){localStorage.removeItem('v742_hist'); history=[]; liveSignals={}; renderHist();}

function cerca(){
 fetch('/api/scan').then(r=>r.json()).then(d=>{
  document.getElementById('info').innerText=d.time+' | LIVE: '+d.signals.length+' | STORICO: '+history.length;
  let h=''; let nuovi=0;
  let nowTs=Date.now();
  d.signals.forEach(s=>{
   let id=s.pair+'_'+s.dir;
   let isNew=!liveSignals[id];
   let prevTs=liveSignals[id]||nowTs;
   let ageMin=Math.floor((nowTs-prevTs)/60000);
   if(isNew){
    // aggiungi a storico
    history.push({pair:s.pair,dir:s.dir,expiry:s.expiry,note:s.note,time:d.time,ts:nowTs,confidence:s.confidence});
    if(history.length>100) history=history.slice(-100);
    localStorage.setItem('v742_hist',JSON.stringify(history));
    liveSignals[id]=nowTs;
    nuovi++;
   }
   let badgeClass=isNew?'nuovo':'vecchio';
   let badgeTxt=isNew?'🟢 NUOVO ORA':'🟡 DA '+ageMin+' MIN';
   if(ageMin>5) badgeTxt='🔴 VECCHIO '+ageMin+' MIN';
   let expClass=s.expiry=='00:03:00'?'exp3':'exp';
   let cls=s.dir=='SELL'?'card sell':'card';
   if(ageMin>4) cls+=' old';
   let tfs=s.tfs.map(t=>`<span class="tf">${t}</span>`).join('');
   h+=`<div class="${cls}"><span class="badge ${badgeClass}">${badgeTxt}</span><b style="font-size:18px;color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b><br><div style="margin:4px 0">${tfs} ${s.confidence}</div><div style="color:#888;font-size:12px">${s.note}</div><span class="${expClass}">⏱️ ENTRA ${s.expiry}</span> <span class="timer">${ageMin==0?'APPENA USCITO':ageMin+' min fa'}</span></div>`;
  });
  // segnali scomparsi = scaduti
  Object.keys(liveSignals).forEach(k=>{
   if(!d.signals.find(s=> (s.pair+'_'+s.dir)==k)){
    let elapsed=Math.floor((nowTs-liveSignals[k])/60000);
    if(elapsed>10) delete liveSignals[k];
   }
  });
  if(nuovi>0){ suona(); renderHist(); if(Notification&&Notification.permission=='granted') new Notification('NUOVO SEGNALE '+nuovi,{body:d.signals.map(s=>s.dir+' '+s.pair).join(', ')}); }
  document.getElementById('live').innerHTML=h||'<p style="color:#555">Nessun segnale nuovo - guarda storico sotto</p>';
 });
}
setInterval(()=>{renderHist(); cerca();},45000);
window.onload=()=>{renderHist(); cerca();};
</script></body></html>"""

@app.route('/api/scan')
def api():
    tz=pytz.timezone('Europe/Rome'); now=datetime.now(tz).strftime('%H:%M:%S IT')
    out=[]
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs={ex.submit(check_pair_multitf,s):s for s in PAIRS}
        for f in as_completed(futs):
            r=f.result()
            if r: out.append(r)
    out.sort(key=lambda x: x['confidence'], reverse=True)
    return jsonify({"signals":out,"time":now})

if __name__=="__main__":
    import os; app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
