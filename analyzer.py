from flask import Flask, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from curl_cffi import requests as cffi_requests

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

PAIRS = [
("EURUSD=X","EUR/USD"),("GBPUSD=X","GBP/USD"),("AUDUSD=X","AUD/USD"),
("USDJPY=X","USD/JPY"),("USDCHF=X","USD/CHF"),("USDCAD=X","USD/CAD"),
("NZDUSD=X","NZD/USD"),("EURJPY=X","EUR/JPY"),("EURGBP=X","EUR/GBP"),
("EURCHF=X","EUR/CHF"),("EURAUD=X","EUR/AUD"),("EURCAD=X","EUR/CAD"),
("GBPJPY=X","GBP/JPY"),("GBPCHF=X","GBP/CHF"),("GBPCAD=X","GBP/CAD"),
("GBPAUD=X","GBP/AUD"),("AUDJPY=X","AUD/JPY"),("AUDCAD=X","AUD/CAD"),
("AUDCHF=X","AUD/CHF"),("NZDJPY=X","NZD/JPY"),
("EURUSD=X","EUR/USD OTC"),("GBPUSD=X","GBP/USD OTC"),
("EURJPY=X","EUR/JPY OTC"),("GBPJPY=X","GBP/JPY OTC"),
("AUDJPY=X","AUD/JPY OTC"),("USDJPY=X","USD/JPY OTC"),
("AUDUSD=X","AUD/USD OTC"),("EURGBP=X","EUR/GBP OTC"),
]

def get_df(sym):
    try:
        df=yf.Ticker(sym,session=session).history(period="2d",interval="5m")
        return df if len(df)>=60 else None
    except: return None

def scadenza():
    now = datetime.now(ROMA)
    min_arrotondato = (now.minute // 5 + 1) * 5
    if min_arrotondato == 60:
        scad = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        scad = now.replace(minute=min_arrotondato, second=0, microsecond=0)
    return scad.strftime("%H:%M")

def pinbar_any(o,h,l,c, df):
    b=abs(c-o); r=h-l
    if r==0 or b==0: return None
    up=h-max(o,c); lo=min(o,c)-l
    lo_perc = lo/r; up_perc = up/r; body_perc = b/r
    
    # REGOLA BASE COMUNE A TUTTE
    if body_perc > 0.30: return None  # corpo max 30%
    if lo_perc < 0.68 and up_perc < 0.68: return None  # almeno un'ombra 68%+
    
    # Evita pinbar sporche con 2 ombre lunghe
    if lo_perc > 0.15 and up_perc > 0.15:
        # se entrambe >15% non è pinbar pulita come foto
        if not (lo_perc >= 0.68 or up_perc >= 0.68):
            return None
        if lo_perc >= 0.40 and up_perc >= 0.40:
            return None

    delta = df['Close'].diff()
    gain = delta.where(delta>0,0).ewm(span=14).mean()
    loss = -delta.where(delta<0,0).ewm(span=14).mean()
    rs = gain.iloc[-1] / (loss.iloc[-1] + 0.00001)
    rsi = 100 - (100/(1+rs))

    # TIPO 1: HAMMER CALL come tua foto - ombra sotto 68%+
    if lo_perc >= 0.68 and up_perc <= 0.15 and body_perc <= 0.30:
        ratio = lo/b if b>0 else 0
        if ratio < 2.2: return None
        min10 = df['Low'].iloc[-11:-1].min()
        if l > min10 * 1.001: return None
        if rsi > 50: return None
        return "CALL", int(lo_perc*100), round(ratio,1), int(rsi)

    # TIPO 2: SHOOTING STAR PUT - ombra sopra 68%+ (opposto della foto)
    if up_perc >= 0.68 and lo_perc <= 0.15 and body_perc <= 0.30:
        ratio = up/b if b>0 else 0
        if ratio < 2.2: return None
        max10 = df['High'].iloc[-11:-1].max()
        if h < max10 * 0.999: return None
        if rsi < 50: return None
        return "PUT", int(up_perc*100), round(ratio,1), int(rsi)

    return None

def analizza():
    if not (0 <= datetime.now(ROMA).hour < 23): return []
    out=[]; sc=scadenza(); visto=set()
    for ysym,label in PAIRS:
        if label in visto: continue
        df=get_df(ysym)
        if df is None: continue
        r=df.iloc[-1]
        res=pinbar_any(r['Open'],r['High'],r['Low'],r['Close'], df)
        if not res: continue
        d, perc, ratio, rsi=res
        out.append({"coppia":label,"dir":d,"perc":perc,"ratio":ratio,"rsi":rsi,"scadenza":sc,"ora":datetime.now(ROMA).strftime("%H:%M:%S")})
        visto.add(label)
    return out

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width'><title>V6.2 ANY PINBAR</title>
<style>body{background:#111;color:#fff;font-family:Arial;padding:15px}.card{border:2px solid #0f0;padding:14px;margin:10px 0;border-radius:12px;background:#1a1a1a}.CALL{color:#0f0;font-size:22px;font-weight:bold}.PUT{color:#f44;font-size:22px;font-weight:bold}.OTC{color:#ff0}button{padding:14px;border:none;border-radius:10px;font-size:16px;font-weight:bold;margin:6px 0;width:100%}#unlock{background:#0f0;color:#000}#analyze{background:#222;color:#fff;border:1px solid #555}</style></head><body>
<h2>🎯 V6.2 PINBAR 68%+ ANY - REALI+OTC 5M</h2>
<div style=color:#ff0;font-size:12px>CALL come foto (ombra sotto) + PUT (ombra sopra) - basta che rispetti 68%+</div>
<div id=status style=color:#aaa;margin-top:8px>V6.2 ANY attivo 5m - 28 coppie</div>
<button id=unlock onclick=enableAudio()>🔊 AUDIO</button>
<button id=analyze onclick=load()>🔄 CERCA PINBAR (5M)</button>
<div id=l style=margin-top:10px></div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<script>
let audioEnabled=false;
function enableAudio(){let a=document.getElementById('b');a.play().then(()=>{a.pause();a.currentTime=0;audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON';localStorage.setItem('audio','1');}).catch(e=>{});}
async function load(){
  document.getElementById('status').innerText='⏳ Scansiono 28 coppie...';
  try{
    let r=await fetch('/api/signals'); let d=await r.json(); let c=document.getElementById('l');
    if(d.length==0){
      document.getElementById('status').innerText='✅ 28 coppie - nessuna pinbar 68%+ ora';
      c.innerHTML='<p style=color:#666>Nessuna pinbar valida ora.<br>Check: '+new Date().toLocaleTimeString()+'</p>';
    } else {
      document.getElementById('status').innerText='🔥 '+d.length+' PINBAR TROVATE!';
      c.innerHTML=''; d.forEach(s=>{
        let e=document.createElement('div'); e.className='card';
        e.innerHTML=`<b>${s.coppia} 5M</b> ${s.ora}<br><span class=${s.dir}>${s.dir}</span> Ombra ${s.perc}% ${s.ratio}x RSI ${s.rsi}<br>Scad <b>${s.scadenza} (5 MIN)</b>`;
        c.appendChild(e);
      });
      if(audioEnabled){document.getElementById('b').play().catch(()=>{}); if(navigator.vibrate) navigator.vibrate([400,100,400]);}
    }
    if(localStorage.getItem('audio')=='1'){audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON';}
  }catch(e){document.getElementById('status').innerText='❌ Errore...';}
}
load(); setInterval(load,15000);
</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
