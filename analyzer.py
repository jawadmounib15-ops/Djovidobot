from flask import Flask, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from curl_cffi import requests as cffi_requests
import time

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome")
ROMA = pytz.timezone("Europe/Rome")

STORICO = []

OTC_1M = [
("EURUSD=X","EUR/USD OTC"),("GBPUSD=X","GBP/USD OTC"),("USDJPY=X","USD/JPY OTC"),
("AUDUSD=X","AUD/USD OTC"),("EURJPY=X","EUR/JPY OTC"),("EURGBP=X","EUR/GBP OTC"),
("GBPJPY=X","GBP/JPY OTC"),("AUDJPY=X","AUD/JPY OTC"),("GBPCHF=X","GBP/CHF OTC"),
("EURCHF=X","EUR/CHF OTC"),("EURAUD=X","EUR/AUD OTC"),("NZDUSD=X","NZD/USD OTC"),
("GBPAUD=X","GBP/AUD OTC"),("GBPCAD=X","GBP/CAD OTC"),("AUDCAD=X","AUD/CAD OTC"),
("CHFJPY=X","CHF/JPY OTC"),("NZDJPY=X","NZD/JPY OTC"),("CADCHF=X","CAD/CHF OTC"),
]

def get_df_safe(sym):
    try:
        df=yf.Ticker(sym,session=session).history(period="2d",interval="1m")
        if df is None or len(df)<30: return None
        df=df.dropna()
        return df if len(df)>=30 else None
    except: return None

def scadenza_1m():
    now = datetime.now(ROMA)
    scad = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return scad.strftime("%H:%M:%S"), (60 - now.second), scad

def rsi_bb_bilanciato(o,h,l,c, df):
    try:
        sma20 = df['Close'].rolling(20).mean()
        std20 = df['Close'].rolling(20).std()
        bb_up = sma20 + std20*2
        bb_low = sma20 - std20*2
        delta = df['Close'].diff()
        gain = delta.where(delta>0,0).ewm(span=14).mean()
        loss = -delta.where(delta<0,0).ewm(span=14).mean()
        rsi_series = 100 - (100/(1+ (gain/(loss+0.00001))))

        if len(rsi_series)<3: return None
        rsi_prev = rsi_series.iloc[-2]
        rsi_now = rsi_series.iloc[-1]
        bb_low_prev = bb_low.iloc[-2]
        bb_up_prev = bb_up.iloc[-2]
        if str(rsi_prev)=='nan' or str(bb_low_prev)=='nan': return None

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        b_curr = abs(curr['Close']-curr['Open'])
        r_curr = curr['High']-curr['Low']
        lo_curr = min(curr['Open'],curr['Close']) - curr['Low']
        up_curr = curr['High'] - max(curr['Open'],curr['Close'])
        lo_perc = lo_curr/r_curr if r_curr>0 else 0
        up_perc = up_curr/r_curr if r_curr>0 else 0

        # BILANCIATO - via di mezzo:
        # BB: basta avvicinarsi 0.15% (non serve rottura vera come V9.5)
        # RSI: 40/60 (via di mezzo tra 42/58 largo e 36/64 stretto)
        # Ombra: 20% basta (non 28% stretto)

        vicino_low = prev['Low'] <= bb_low_prev * 1.0015 # più largo di V9.5
        vicino_high = prev['High'] >= bb_up_prev * 0.9985

        # CALL BILANCIATO
        if vicino_low and rsi_prev < 40:
            if lo_perc >= 0.20 or curr['Close'] > prev['Close']*0.9999:
                score = (40 - rsi_prev) + lo_perc*10
                return "CALL", int(rsi_prev), "BB LOW", score

        # PUT BILANCIATO
        if vicino_high and rsi_prev > 60:
            if up_perc >= 0.20 or curr['Close'] < prev['Close']*1.0001:
                score = (rsi_prev - 60) + up_perc*10
                return "PUT", int(rsi_prev), "BB HIGH", score

        # FALLBACK PINBAR se BB non tocca ma RSI estremo + pinbar forte
        # Così se mercato calmo trovi lo stesso qualcosa
        if rsi_prev < 30 and lo_perc >= 0.45:
            return "CALL", int(rsi_prev), "PINBAR RSI", 5
        if rsi_prev > 70 and up_perc >= 0.45:
            return "PUT", int(rsi_prev), "PINBAR RSI", 5

        return None
    except:
        return None

def analizza():
    global STORICO
    now = datetime.now(ROMA)
    sec = now.second
    if not (15 <= sec <= 58):
        return {"wait": True, "sec": sec, "signals": [], "storico": STORICO[-20:][::-1]}

    out=[]
    try:
        scad_str, rimanenti, scad_dt = scadenza_1m()
        candidati=[]
        for i,(ysym,label) in enumerate(OTC_1M):
            try:
                df=get_df_safe(ysym)
                if df is None: continue
                r=df.iloc[-1]
                res=rsi_bb_bilanciato(r['Open'],r['High'],r['Low'],r['Close'], df)
                if not res: continue
                d, rsi, bb, score=res
                candidati.append({
                    "coppia":label,"dir":d,"rsi":rsi,"bb":bb,"score":score,
                    "scadenza":scad_str,"ora":now.strftime("%H:%M:%S"),
                    "rimanenti": rimanenti, "scadenza_full": scad_dt.strftime("%H:%M:%S"),
                    "data": now.strftime("%d/%m %H:%M:%S")
                })
                if i % 5 == 0: time.sleep(0.12)
            except: continue

        candidati.sort(key=lambda x: x['score'], reverse=True)
        out = candidati[:5] # MAX 5

        for s in out:
            gia = [x for x in STORICO if x['coppia']==s['coppia'] and x['ora'][:5]==now.strftime("%H:%M")]
            if not gia:
                STORICO.append(s)
                if len(STORICO)>100: STORICO = STORICO[-100:]

        return {"wait": False, "sec": sec, "signals": out, "storico": STORICO[-20:][::-1], "debug": f"{len(candidati)} candidati"}
    except Exception as e:
        return {"wait": False, "sec": sec, "signals": out, "storico": STORICO[-20:][::-1], "error": str(e)[:80]}

PAGE="""<!DOCTYPE html><html><head><meta charset=utf-8>
<meta name=viewport content='width=device-width, initial-scale=1'>
<title>V9.6 BILANCIATO</title>
<style>
*{box-sizing:border-box}body{background:#000;color:#fff;font-family:Arial;margin:0;padding:0}
.header{background:#111;padding:14px;border-bottom:3px solid #0f0;position:sticky;top:0;z-index:10}
.header h2{margin:0;color:#0f0;font-size:18px}.sub{color:#ff0;font-size:11px;line-height:1.3}
.container{padding:10px}.card{border:3px solid #0f0;padding:14px;margin:12px 0;border-radius:14px;background:#151515}
.card.PUT{border-color:#ff3333}.CALL{color:#0f0;font-size:24px;font-weight:bold}.PUT{color:#ff3333;font-size:24px;font-weight:bold}
.timer{font-size:34px;font-weight:bold;color:#ff0;text-align:center;padding:10px;background:#222;border-radius:10px;margin:10px 0}
.countdown{font-size:20px;color:#0f0;text-align:center;font-weight:bold}
button{padding:14px;border:none;border-radius:12px;font-size:16px;font-weight:bold;margin:6px 0;width:100%}
#unlock{background:#0f0;color:#000}#analyze{background:#222;color:#fff;border:1px solid #555}
.storico{background:#111;border:1px solid #444;border-radius:12px;padding:10px;margin:15px 0}
.storico h3{margin:5px 0;color:#ff0;font-size:14px}
.row{display:flex;justify-content:space-between;font-size:12px;padding:6px 0;border-bottom:1px solid #222}
.row.CALL b{color:#0f0}.row.PUT b{color:#ff3333}
.debug{font-size:11px;color:#666;text-align:center}
</style></head><body>
<div class=header>
<h2>✅ V9.6 BILANCIATO - TROVA ORA - MAX 5</h2>
<div class=sub>BILANCIATO: RSI 40/60 + BB vicino 0.15% + Ombra 20% + Fallback pinbar 45% + Storico + 30sec</div>
</div>
<div class=container>
<div id=status>🟡 V9.6 BILANCIATO - trova 2-3 all'ora</div>
<div id=timer class=timer>00</div>
<div id=countdown class=countdown></div>
<div id=debug class=debug></div>
<button id=unlock onclick=enableAudio()>🔊 AUDIO ON - BILANCIATO</button>
<button id=analyze onclick=load()>🔄 SCANSIONA BILANCIATO</button>
<div id=l></div>
<div class=storico><h3>📜 STORICO ULTIMI 20 - BILANCIATO</h3><div id=storico>Nessun segnale - storico vuoto</div></div>
</div>
<audio id=b src=https://cdn.pixabay.com/audio/2022/03/10/audio_1c8c9a0727.mp3 preload=auto></audio>
<script>
let audioEnabled=false, lastCount=0;
function enableAudio(){let a=document.getElementById('b');a.play().then(()=>{a.pause();a.currentTime=0;audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON - BILANCIATO';localStorage.setItem('audio','1');}).catch(e=>{});}
function renderStorico(list){let h=document.getElementById('storico'); if(!list||list.length==0){h.innerHTML='<div style=color:#666>Nessun segnale - storico vuoto - ma ora trova</div>';return;} let html=''; list.forEach(s=>{html+=`<div class=row ${s.dir}><span>${s.data} - ${s.coppia}</span><span><b>${s.dir}</b> RSI${s.rsi} Scad ${s.scadenza}</span></div>`;}); h.innerHTML=html;}
async function load(){
  try{
    let r=await fetch('/api/signals'); if(!r.ok) throw new Error(r.status);
    let data=await r.json();
    document.getElementById('timer').innerText=':'+String(data.sec).padStart(2,'0')+' sec';
    if(data.debug) document.getElementById('debug').innerText=data.debug+' candidati trovati';
    if(data.wait){document.getElementById('countdown').innerText='⏰ Avviso tra '+(15-data.sec)+' sec'; document.getElementById('status').innerHTML='⏳ V9.6 BILANCIATO aspetto :15 - ora :'+data.sec; renderStorico(data.storico); return;}
    renderStorico(data.storico);
    let c=document.getElementById('l');
    if(data.signals.length==0){
      document.getElementById('status').innerHTML='🟢 BILANCIATO scan :'+data.sec+' - 0 ora - ma trova sicuro';
      document.getElementById('countdown').innerText='🔍 18 OTC scan - nessun BB vicino ora';
      if(lastCount>0) c.innerHTML='';
    } else {
      document.getElementById('status').innerHTML='🔥 '+data.signals.length+' SEGNALI BILANCIATO A :'+data.sec+' - '+data.signals[0].rimanenti+' SEC!';
      document.getElementById('countdown').innerText='🚨 '+data.signals[0].rimanenti+' SEC PER ENTRARE! SCADE '+data.signals[0].scadenza;
      c.innerHTML=''; data.signals.forEach(s=>{
        let e=document.createElement('div'); e.className='card '+s.dir;
        e.innerHTML=`<b>${s.coppia} 1M BILANCIATO</b> <span style=float:right;font-size:11px>${s.data}</span><br><span class=${s.dir}>${s.dir} 1M</span> - ${s.bb} RSI ${s.rsi}<br><div style=margin-top:8px;background:#222;padding:8px;border-radius:8px>⏰ ${s.ora} → SCAD <b style=color:#ff0>${s.scadenza_full}</b> - <b style=color:#0f0>${s.rimanenti} SEC</b></div><div style=margin-top:10px><span style=background:#0f0;color:#000;padding:10px;border-radius:8px;font-weight:bold;display:block;text-align:center>👉 ENTRA 1 MIN - SCADE ${s.scadenza}</span></div>`;
        c.appendChild(e);
      });
      if(audioEnabled && data.signals.length!=lastCount){document.getElementById('b').play().catch(()=>{}); if(navigator.vibrate) navigator.vibrate([500,100,500]);}
      lastCount=data.signals.length;
    }
    if(localStorage.getItem('audio')=='1'){audioEnabled=true;document.getElementById('unlock').innerText='✅ AUDIO ON';}
  }catch(e){document.getElementById('status').innerHTML='❌ '+e.message;}
}
setInterval(load,2000); load();
</script></body></html>"""

@app.route('/')
def home(): return PAGE
@app.route('/api/signals')
def sig(): return jsonify(analizza())
@app.route('/api/storico')
def storico(): return jsonify(STORICO[-50:][::-1])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
