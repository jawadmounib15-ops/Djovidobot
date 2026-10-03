# V104 ULTRA LARGO - FIX about:blank DEFINITIVO
from flask import Flask, jsonify
import os, gc
app = Flask(__name__)

OTC_MAP = {
    "EURUSD-OTC":"EURUSD=X", "GBPUSD-OTC":"GBPUSD=X", "USDJPY-OTC":"USDJPY=X",
    "AUDUSD-OTC":"AUDUSD=X", "EURJPY-OTC":"EURJPY=X", "EURGBP-OTC":"EURGBP=X",
    "GBPJPY-OTC":"GBPJPY=X", "AUDJPY-OTC":"AUDJPY=X", "EURCHF-OTC":"EURCHF=X",
    "CADJPY-OTC":"CADJPY=X", "EURAUD-OTC":"EURAUD=X", "GBPAUD-OTC":"GBPAUD=X",
    "Gold":"GC=F", "Silver":"SI=F"
}

def calc_rsi(series, period=14):
    try:
        delta=series.diff()
        gain=(delta.where(delta>0,0)).rolling(window=period).mean()
        loss=(-delta.where(delta<0,0)).rolling(window=period).mean()
        if loss.iloc[-1]==0: return 50.0
        rs=gain/loss
        rsi=100-(100/(1+rs))
        v=float(rsi.iloc[-1])
        return v if str(v)!='nan' else 50.0
    except: return 50.0

@app.route('/')
def home():
    return """
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V104 FIX</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:10px}
.btn{padding:18px;border-radius:14px;font-weight:bold;font-size:18px;width:95%;max-width:430px;margin:10px auto;display:block}
.g{background:#00ff88;color:#000}.d{background:#222;color:#fff;border:2px solid #555}
.card{background:#1e1e1e;border-radius:16px;padding:14px;margin:10px auto;max-width:440px;text-align:left;border-left:8px solid #00ff88}
.sell{border-left-color:#ff3b3b}
</style></head><body>
<h2>✅ V104 ULTRA LARGO 60/35 FIX</h2>
<p>Fix about:blank - ora carica</p>
<div class="btn g" onclick="scan()">🔍 SCAN ORA</div>
<p id="info">Pronto</p><div id="live"></div>
<script>
function scan(){
 document.getElementById('info').innerText='⏳ Scan...';
 fetch('/api/scan').then(r=>r.json()).then(d=>{
   let h='';
   if(d.signals.length==0){document.getElementById('info').innerText='Nessun segnale - sabato mercato chiuso, ma pagina OK'; return;}
   d.signals.forEach(s=>{
     let col=s.dir=='BUY'?'#00ff88':'#ff3b3b';
     h+=`<div class="card ${s.dir=='SELL'?'sell':''}"><b style="color:${col}">${s.pair} ${s.dir} ${s.score}</b><br>RSI ${s.rsi} - ${s.reason}<br>${s.price}</div>`;
   });
   document.getElementById('live').innerHTML=h;
   document.getElementById('info').innerText=d.signals.length+' segnali';
 }).catch(e=>{document.getElementById('info').innerText='Errore: '+e;});
}
</script></body></html>
"""

@app.route('/api/scan')
def api():
    # import DENTRO per non crashare home
    try:
        import yfinance as yf, pandas as pd
    except Exception as e:
        return jsonify({"signals":[],"error":f"yfinance error {e}"})
    
    out=[]
    for otc, real in OTC_MAP.items():
        try:
            df=yf.download(real, period="5d", interval="1m", progress=False, auto_adjust=True, threads=False)
            if df is None or len(df)<20: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns=df.columns.get_level_values(0)
            c=float(df.iloc[-1]['Close']); o=float(df.iloc[-1]['Open']); h=float(df.iloc[-1]['High']); l=float(df.iloc[-1]['Low'])
            rt=h-l
            if rt<=0: continue
            body=abs(c-o); up=h-max(c,o); down=min(c,o)-l
            rsi=calc_rsi(df['Close'])
            pct_up=int((up/rt)*100); pct_down=int((down/rt)*100); body_pct=int((body/rt)*100)

            # ULTRA LARGO 60/35 + 70/25
            cond_base_bull = (down > rt*0.60) and (body < rt*0.35)
            cond_base_bear = (up > rt*0.60) and (body < rt*0.35)
            cond_perf_bull = (down > rt*0.70) and (body < rt*0.25)
            cond_perf_bear = (up > rt*0.70) and (body < rt*0.25)

            dire=None; reason=""; score=0
            if cond_base_bull and (15 <= rsi <= 45):
                dire="BUY"; score=78; reason=f"RSI {int(rsi)} 15-45 + Pin {pct_down}% >60% corpo {body_pct}% <35%"
            elif cond_base_bear and (55 <= rsi <= 85):
                dire="SELL"; score=78; reason=f"RSI {int(rsi)} 55-85 + Pin {pct_up}% >60% corpo {body_pct}% <35%"
            elif cond_perf_bull and (10 <= rsi <= 55):
                dire="BUY"; score=88; reason=f"PERFETTA {pct_down}% >70% corpo {body_pct}% <25% RSI {int(rsi)}"
            elif cond_perf_bear and (45 <= rsi <= 90):
                dire="SELL"; score=88; reason=f"PERFETTA {pct_up}% >70% corpo {body_pct}% <25% RSI {int(rsi)}"
            else: continue

            fmt=f"{c:.5f}" if "JPY" not in otc else f"{c:.3f}"
            out.append({"pair":otc,"dir":dire,"price":fmt,"score":score,"rsi":int(rsi),"reason":reason})
            del df; gc.collect()
        except: gc.collect(); continue
    out=sorted(out, key=lambda x:x['score'], reverse=True)[:15]
    return jsonify({"signals":out})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
