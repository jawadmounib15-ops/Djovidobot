# V104 SUPER LARGO - FIX SABATO + SPASSATO MAX
import yfinance as yf, pandas as pd, gc
from flask import Flask, jsonify
import os
app = Flask(__name__)

OTC_MAP = {
    "EURUSD-OTC":"EURUSD=X", "GBPUSD-OTC":"GBPUSD=X", "USDJPY-OTC":"USDJPY=X",
    "AUDUSD-OTC":"AUDUSD=X", "EURJPY-OTC":"EURJPY=X", "EURGBP-OTC":"EURGBP=X",
    "GBPJPY-OTC":"GBPJPY=X", "AUDJPY-OTC":"AUDJPY=X", "EURCHF-OTC":"EURCHF=X",
    "CADJPY-OTC":"CADJPY=X", "EURAUD-OTC":"EURAUD=X", "GBPAUD-OTC":"GBPAUD=X",
    "AUDCHF-OTC":"AUDCHF=X", "EURTRY-OTC":"EURTRY=X", "USDTRY-OTC":"USDTRY=X",
    "NZDJPY-OTC":"NZDJPY=X", "EURCAD-OTC":"EURCAD=X", "AUDCAD-OTC":"AUDCAD=X",
    "EURUSD":"EURUSD=X", "GBPUSD":"GBPUSD=X", "USDJPY":"USDJPY=X", "AUDUSD":"AUDUSD=X",
    "Gold":"GC=F", "Silver":"SI=F", "WTI":"CL=F"
}

def fix(df):
    try:
        if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    except: pass
    return df

def calc_rsi(series, period=14):
    try:
        delta=series.diff(); gain=(delta.where(delta>0,0)).rolling(window=period).mean()
        loss=(-delta.where(delta<0,0)).rolling(window=period).mean()
        if loss.iloc[-1]==0: return 50.0
        rs=gain/loss; rsi=100-(100/(1+rs)); v=float(rsi.iloc[-1])
        return v if not pd.isna(v) else 50.0
    except: return 50.0

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V104 SUPER LARGO</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:8px}
.btn{padding:20px;border-radius:16px;font-weight:bold;font-size:18px;width:98%;max-width:440px;display:block;margin:8px auto;cursor:pointer}
.g{background:#00ff88;color:#000;border:3px solid #00ff88}.d{background:#222;color:#fff;border:2px solid #555}
.card{background:#1e1e1e;border-radius:20px;padding:16px;margin:10px auto;max-width:460px;text-align:left;border-left:10px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}.perf{border:2px solid gold}
.score{font-size:44px;font-weight:900}.badge{position:absolute;top:12px;right:12px;text-align:right}
.prepara{background:#00ff88;color:#000;font-weight:bold;padding:12px;border-radius:10px;margin-top:10px;text-align:center}
.sellbg{background:#ff3b3b;color:#fff}
.warn40{background:#ffcc00;color:#000;font-weight:900;padding:14px;border-radius:12px;margin:10px auto;max-width:460px}
.storico{background:#111;border:1px solid #333;border-radius:12px;padding:12px;margin:14px auto;max-width:460px;text-align:left;font-size:12px}
.tag{font-size:10px;padding:3px 6px;border-radius:6px;font-weight:bold;display:inline-block}
.tag-rsi{background:#00ff88;color:#000}.tag-perf{background:gold;color:#000}
#s{padding:12px;border-radius:8px;margin:8px auto;max-width:440px;font-weight:bold}
.on{background:#00ff88;color:#000}.off{background:#ff3b3b;color:#fff}
</style></head><body>
<h2>✅ V104 SUPER LARGO 60/35 + 70/25</h2>
<div id="s" class="off">🔇 ATTIVA</div>
<div class="btn g" onclick="att()">🔔 ATTIVA SUONO + 40 SEC</div>
<div class="btn d" onclick="scan()">🔍 SCAN SUPER LARGO</div>
<p id="info">Fix sabato + 60/35 + 70/25</p>
<div id="warn40box"></div><div id="live"></div>
<div class="storico"><b>📜 STORICO:</b><div id="storico">Vuoto</div><div style="margin-top:6px"><span onclick="clearStor()" style="color:#ff3b3b;cursor:pointer">🗑️ Pulisci</span></div></div>
<script>
let ctx=null,ok=false,expMin=2,warned40=false;
let stor=JSON.parse(localStorage.getItem('v104sl_stor')||'[]');
function updStor(){let h=''; stor.slice(0,30).forEach(s=>{h+=`<div>${s}</div>`}); document.getElementById('storico').innerHTML=h||'Vuoto';}
updStor(); function clearStor(){stor=[]; localStorage.setItem('v104sl_stor',JSON.stringify(stor)); updStor();}
function att(){try{ctx=new (window.AudioContext||window.webkitAudioContext)(); ctx.resume().then(()=>{ok=true; document.getElementById('s').className='on'; document.getElementById('s').innerText='🔊 ON SUPER LARGO'; beep(900,0.4); scan();});}catch(e){}}
function beep(f,d){if(!ctx) return; try{let o=ctx.createOscillator(),g=ctx.createGain(); o.type='square'; o.frequency.value=f; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(1,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+d); o.start(); o.stop(ctx.currentTime+d);}catch(e){}}
function avviso40(){if(!ok) return; beep(1000,0.5); setTimeout(()=>beep(1500,0.6),500); document.getElementById('warn40box').innerHTML='<div class="warn40">⏰ 40 SEC - PREPARA!!</div>'; setTimeout(()=>{document.getElementById('warn40box').innerHTML='';},12000);}
let cur=[],ent=0; function getN(){let n=new Date(); let nx=new Date(n); nx.setSeconds(0,0); nx.setMilliseconds(0); nx.setMinutes(n.getMinutes()+1); return nx;}
function scan(){document.getElementById('info').innerText='⏳ Scan super largo (fix sabato)...'; fetch('/api/scan').then(r=>r.json()).then(d=>{cur=d.signals; ent=getN().getTime(); warned40=false; document.getElementById('info').innerText=`✅ ${d.debug} candele - ${d.signals.length} segnali`; if(d.signals.length>0){let now=new Date().toLocaleTimeString('it-IT'); d.signals.forEach(s=>{stor.unshift(`${now} - ${s.score} ${s.dir} ${s.pair}`);}); localStorage.setItem('v104sl_stor',JSON.stringify(stor.slice(0,50))); updStor(); if(ok) beep(1100,0.6);} render();});}
function render(){let now=Date.now(); let diff=Math.ceil((ent-now)/1000); let h=''; cur.forEach(s=>{let col=s.dir=='BUY'?'#00ff88':'#ff3b3b'; h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><div class="badge"><div class="score" style="color:${col}">${s.score}</div><div style="color:${col}">${s.dir}</div><div>RSI${s.rsi}</div><div class="tag ${s.tag.includes('RSI')?'tag-rsi':'tag-perf'}">${s.tag}</div></div><div style="width:58%"><b style="color:${col}">${s.pair}</b><br><span style="font-size:11px;color:#aaa">${s.reason}</span><br>${s.price}</div><div class="prepara ${s.dir=='SELL'?'sellbg':''}">ENTRA ${diff}s</div></div>`;}); document.getElementById('live').innerHTML=h||`Nessun segnale - riprova`;}
setInterval(render,1000); setInterval(scan,35000);
</script></body></html>"""

@app.route('/api/scan')
def api():
    out=[]; total_candles=0
    for otc, real in OTC_MAP.items():
        try:
            # FIX SABATO: 5d prende venerdì anche se oggi sabato
            df=yf.download(real, period="5d", interval="1m", progress=False, auto_adjust=True, threads=False)
            df=fix(df)
            if df is None or len(df)<20: continue
            total_candles=len(df)
            c=float(df.iloc[-1]['Close']); o=float(df.iloc[-1]['Open']); h=float(df.iloc[-1]['High']); l=float(df.iloc[-1]['Low'])
            rt=h-l
            if rt<=0: continue
            body=abs(c-o); up=h-max(c,o); down=min(c,o)-l
            rsi=calc_rsi(df['Close'], 14)
            pct_up=int((up/rt)*100); pct_down=int((down/rt)*100); body_pct=int((body/rt)*100)
            
            # SUPER LARGO
            cond_base_bull = (down > rt*0.60) and (body < rt*0.35)
            cond_base_bear = (up > rt*0.60) and (body < rt*0.35)
            cond_perf_bull = (down > rt*0.70) and (body < rt*0.25)
            cond_perf_bear = (up > rt*0.70) and (body < rt*0.25)
            
            dire=None; tag=""; pct=0; score=0; reason=""
            if cond_base_bull and (15 <= rsi <= 45):
                dire="BUY"; pct=pct_down; score=78; tag="ZONA RSI BUY"; reason=f"RSI {int(rsi)} 15-45 + Pin {pct}% >60% corpo {body_pct}% <35% LARGO"
            elif cond_base_bear and (55 <= rsi <= 85):
                dire="SELL"; pct=pct_up; score=78; tag="ZONA RSI SELL"; reason=f"RSI {int(rsi)} 55-85 + Pin {pct}% >60% corpo {body_pct}% <35% LARGO"
            elif cond_perf_bull and (10 <= rsi <= 55):
                dire="BUY"; pct=pct_down; score=88; tag="PERFETTA LARGO"; reason=f"PERFETTA {pct}% >70% corpo {body_pct}% <25% RSI {int(rsi)}"
            elif cond_perf_bear and (45 <= rsi <= 90):
                dire="SELL"; pct=pct_up; score=88; tag="PERFETTA LARGO"; reason=f"PERFETTA {pct}% >70% corpo {body_pct}% <25% RSI {int(rsi)}"
            else: continue
            
            fmt=f"{c:.5f}" if "JPY" not in otc else f"{c:.3f}"
            out.append({"pair":otc,"dir":dire,"price":fmt,"score":score,"pct":pct,"rsi":int(rsi),"tag":tag,"reason":reason})
            del df; gc.collect()
        except: gc.collect(); continue
    out=sorted(out, key=lambda x: x['score'], reverse=True)[:15]
    return jsonify({"signals":out,"debug":total_candles})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
