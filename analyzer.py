# ANALYZER.PY V73.2 - LARGATO 7% MINIMO
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz, os
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","GBPAUD=X","EURNZD=X","CADCHF=X","CADJPY=X","AUDCAD=X","AUDCHF=X","USDCAD=X","CHFJPY=X","GBPNZD=X","NZDCAD=X"]

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def rsi_calc(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_pair(sym):
    try:
        df = yf.download(sym, period="2d", interval="5m", progress=False)
        df = fix_df(df)
        if len(df) < 70: return None
        df['RSI'] = rsi_calc(df['Close'], 14)
        highs = df['High'].values
        lows = df['Low'].values
        swing_high = None
        swing_low = None
        for i in range(len(df)-25, len(df)-5):
            if highs[i] == max(highs[i-5:i+6]):
                swing_high = float(highs[i])
            if lows[i] == min(lows[i-5:i+6]):
                swing_low = float(lows[i])
        if swing_high is None or swing_low is None: return None
        last = df.iloc[-1]
        prev = df.iloc[-2]
        c = float(last['Close'])
        c_prev = float(prev['Close'])
        rsi_now = float(last['RSI'])
        range_sw = swing_high - swing_low
        if range_sw == 0: return None
        last_20 = df.iloc[-20:]
        max_20 = float(last_20['High'].max())
        min_20 = float(last_20['Low'].min())
        range_20_pct = (max_20 - min_20) / c
        if range_20_pct < 0.0009: # era 0.0010 -> 7% più largo
            return None
        small = 0
        for k in range(-12, 0):
            try:
                cc = float(df.iloc[k]['Close'])
                oo = float(df.iloc[k]['Open'])
                body = abs(cc-oo)
                if body < (range_sw * 0.11): # era 0.12
                    small += 1
            except: pass
        if small >= 7: # era 6 -> 1 in più
            return None
        rsi_last5 = df['RSI'].iloc[-5:].values
        if max(rsi_last5) - min(rsi_last5) < 4 and 39 < rsi_now < 61: # era <5 e 40-60
            return None
        dist_high = abs(c - swing_high) / range_sw
        dist_low = abs(c - swing_low) / range_sw
        if dist_low < 0.14 and c > c_prev and rsi_now < 42: # era 0.12 e 40
            return {"pair":sym.replace("=X",""),"dir":"BUY","price":f"{c:.5f}","note":f"CROCE BASSA + RSI {rsi_now:.0f}"}
        if dist_high < 0.14 and c < c_prev and rsi_now > 58: # era 0.12 e 60
            return {"pair":sym.replace("=X",""),"dir":"SELL","price":f"{c:.5f}","note":f"CROCE ALTA + RSI {rsi_now:.0f}"}
    except:
        return None

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V73.2 7%</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:16px}
.btn{background:#00ff88;color:#000;border:none;padding:16px;border-radius:14px;font-weight:bold;font-size:19px;width:95%;max-width:380px;display:block;margin:10px auto}
.card{background:#1a1a1a;border-radius:14px;padding:14px;margin:10px auto;max-width:400px;text-align:left;border-left:5px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}.old{opacity:0.6;background:#222}
.badge{position:absolute;top:10px;right:10px;font-size:11px;padding:3px 8px;border-radius:6px;font-weight:bold}
.live{background:#ffcc00;color:#000}.scad{background:#555;color:#fff}
.exp{background:#00ff88;color:#000;font-weight:bold;padding:5px 9px;border-radius:8px;display:inline-block;margin-top:6px}
</style></head><body>
<h2>✖️ V73.2 LARGATO 7%</h2>
<p style="color:#00ff88">Stesse regole - solo 7% più largo</p>
<button class="btn" id="b1" onclick="attiva()">🔔 ATTIVA ALLARME</button>
<button class="btn" style="background:#222;color:#fff;border:1px solid #444" onclick="cerca()">🔍 SCAN ORA</button>
<p id="info">...</p><div id="live"></div>
<hr style="border:0;border-top:1px solid #333;margin:18px 0">
<h3 style="color:#888">📜 STORICO</h3><div id="hist"></div>
<button class="btn" style="background:#333;color:#999;font-size:14px;padding:10px" onclick="localStorage.clear();history=[];renderHist();">🗑️ Pulisci</button>
<audio id="s1" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<audio id="s2" src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" preload="auto"></audio>
<script>
let ok=false, a1=document.getElementById('s1'), a2=document.getElementById('s2');
let history = JSON.parse(localStorage.getItem('v73hist')||'[]');
function attiva(){ok=true; a1.play().then(()=>{a1.pause();a1.currentTime=0}).catch(()=>{}); a2.play().then(()=>{a2.pause();a2.currentTime=0}).catch(()=>{}); document.getElementById('b1').innerHTML='✅ ATTIVO 7%'; document.getElementById('b1').style.background='#ffcc00'; if(Notification&&Notification.permission!='granted')Notification.requestPermission(); renderHist();}
function suona(){if(!ok)return; a1.currentTime=0;a1.play(); setTimeout(()=>{a2.currentTime=0;a2.play()},400); setTimeout(()=>{a1.currentTime=0;a1.play()},900); if(navigator.vibrate) navigator.vibrate([1000,300,1000,300,1000]); if(Notification&&Notification.permission=='granted')new Notification('✖️ CROCE!',{body:'Entra 00:05:00'});}
function renderHist(){let h=''; [...history].reverse().forEach(s=>{h+=`<div class="card old ${s.dir=='SELL'?'sell':''}"><span class="badge scad">${s.time}</span><b style="color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b><br>${s.note}<br>${s.price}</div>`;}); document.getElementById('hist').innerHTML=h||'<p style="color:#555">Vuoto</p>';}
function cerca(){fetch('/api/scan').then(r=>r.json()).then(d=>{document.getElementById('info').innerText=d.time+' | '+d.signals.length; let h=''; let nuovi=0; d.signals.forEach(s=>{let id=s.pair+'_'+d.time.slice(0,5); if(!history.find(x=>x.id==id)){history.push({id:id,pair:s.pair,dir:s.dir,price:s.price,note:s.note,time:d.time}); nuovi++;} let cls=s.dir=='SELL'?'card sell':'card'; h+=`<div class="${cls}"><span class="badge live">CROCE!</span><b style="font-size:20px;color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b><br>${s.note}<br>${s.price}<br><span class="exp">⏱️ ENTRA 00:05:00</span></div>`;}); if(nuovi>0){localStorage.setItem('v73hist',JSON.stringify(history.slice(-40))); suona(); renderHist();} document.getElementById('live').innerHTML=h;});}
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
