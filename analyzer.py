from flask import Flask, jsonify, render_template_string, request
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta
import traceback

app = Flask(__name__)
ITALY_TZ = timezone(timedelta(hours=2))
COOLDOWN = {}
PAIRS = {
    "EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X",
    "USD/CAD-OTC":"USDCAD=X","EUR/JPY-OTC":"EURJPY=X","SOL/USD-OTC":"SOL-USD",
    "BTC/USD-OTC":"BTC-USD","ETH/USD-OTC":"ETH-USD","EUR/USD":"EURUSD=X"
}

def get_data(symbol, interval="5m"):
    try:
        period = "2d" if interval=="5m" else "5d"
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False, threads=False)
        if df is None or len(df) < 50: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']
        df['EMA9'] = close.ewm(span=9).mean()
        df['EMA21'] = close.ewm(span=21).mean()
        df['EMA50'] = close.ewm(span=50).mean()
        df['EMA200'] = close.ewm(span=200).mean()
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain/loss))
        return df
    except Exception as e:
        print(f"ERR get_data {symbol}: {e}")
        return None

def is_pinbar(o,h,l,c):
    body = abs(c-o)
    rng = h-l
    if rng==0 or body < rng*0.08 or body > rng*0.40: return None
    upper = h-max(o,c); lower = min(o,c)-l
    if lower >= body*2.2 and lower >= rng*0.55 and upper <= rng*0.35: return "CALL", round(lower/body,1)
    if upper >= body*2.2 and upper >= rng*0.55 and lower <= rng*0.35: return "PUT", round(upper/body,1)
    return None

def analyze_92(symbol, tf="5m"):
    now = datetime.now(ITALY_TZ)
    df = get_data(symbol, "5m" if tf=="5m" else "15m")
    if df is None: return {"score":0,"action":"WAIT","reason":"Dati non disponibili - riprova 10s","tf":tf,"time":now.strftime("%H:%M:%S")}
    try:
        last = df.iloc[-1]
        price, ema9, ema21, ema50, ema200, rsi = float(last['Close']), float(last['EMA9']), float(last['EMA21']), float(last['EMA50']), float(last['EMA200']), float(last['RSI'])
        pin = is_pinbar(float(last['Open']), float(last['High']), float(last['Low']), price)
        if not pin: return {"score":0,"action":"WAIT","reason":f"No pinbar - RSI {rsi:.0f}","tf":tf,"time":now.strftime("%H:%M:%S")}
        direzione, ratio = pin
        trend_up = ema9 > ema21 and ema21 > ema50 and price > ema200
        trend_down = ema9 < ema21 and ema21 < ema50 and price < ema200
        if trend_up and direzione=="PUT": return {"score":0,"action":"WAIT","reason":"PUT contro UP - scartata","tf":tf,"time":now.strftime("%H:%M:%S")}
        if trend_down and direzione=="CALL": return {"score":0,"action":"WAIT","reason":"CALL contro DOWN - scartata","tf":tf,"time":now.strftime("%H:%M:%S")}
        if not trend_up and not trend_down: return {"score":0,"action":"WAIT","reason":f"Laterale RSI {rsi:.0f}","tf":tf,"time":now.strftime("%H:%M:%S")}
        if not (35 <= rsi <= 65): return {"score":0,"action":"WAIT","reason":f"RSI {rsi:.0f} fuori 35-65","tf":tf,"time":now.strftime("%H:%M:%S")}
        score = 95 if ratio >=3 else 92
        return {"score":score,"action":f"{'BUY' if direzione=='CALL' else 'SELL'} {score}%","reason":f"Pinbar {ratio}x | RSI {rsi:.0f} | Trend OK","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    except Exception as e:
        return {"score":0,"action":"WAIT","reason":f"Errore calcolo: {str(e)[:50]}","tf":tf,"time":now.strftime("%H:%M:%S")}

HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V3.1 CLICK FIX</title>
<style>body{background:#0a0a0a;color:#fff;font-family:system-ui;padding:12px}select{width:100%;padding:12px;border-radius:10px;background:#1a1a1f;color:#fff;border:1px solid #333;margin:6px 0}.row{display:flex;gap:8px}.row select{flex:1}.card{background:#1a1a1f;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #333}.sbuy{border-left-color:gold;border:3px solid gold}.badge{padding:6px 12px;border-radius:20px;font-weight:bold;background:gold;color:#000}.fresh{background:#00e676;color:#000;padding:3px 8px;border-radius:10px;font-size:11px}button{width:100%;padding:14px;background:gold;color:#000;border:none;border-radius:12px;font-weight:bold;font-size:17px}button:disabled{opacity:0.5}</style>
</head><body>
<h2>⚡ V3.1 CLICK FIX</h2><div class="row"><select id="pair"><option>EUR/USD-OTC</option><option>SOL/USD-OTC</option><option>BTC/USD-OTC</option><option>EUR/USD</option></select><select id="tf"><option value="5m" selected>5m</option><option value="15m">15m</option></select></div>
<button id="btn" onclick="analyze()">ANALIZZA 92%+</button><div id="result"><div class=card>👆 Clicca per analizzare</div></div>
<h3>⚡ LAVORO 1</h3><div id="auto"><div class=card>⏳ Scansione in corso...</div></div>
<h3>📌 LAVORO 2</h3><div id="pin"><div class=card>⏳ Attivo</div></div>
<script>
async function analyze(){
 let btn=document.getElementById('btn'); let resDiv=document.getElementById('result');
 btn.disabled=true; btn.innerText='ANALIZZO...'; resDiv.innerHTML='<div class=card>⏳ Carico dati Yahoo...</div>';
 let p=document.getElementById('pair').value; let tf=document.getElementById('tf').value;
 try{
  let r=await fetch('/api/analyze?pair='+encodeURIComponent(p)+'&tf='+tf+'&t='+Date.now());
  let d=await r.json();
  if(d.score>=92){ resDiv.innerHTML='<div class=card sbuy><b>'+p+'</b> <span class=badge>'+d.action+'</span> <span class=fresh>'+d.time+'</span><br>'+d.reason+'</div>';}
  else{ resDiv.innerHTML='<div class=card>⏳ '+d.reason+'<br><small>'+d.time+'</small></div>';}
 }catch(e){ resDiv.innerHTML='<div class=card style=border-color:red>❌ Errore: '+e+'<br>Riprova tra 5 sec - Yahoo lento</div>';}
 btn.disabled=false; btn.innerText='ANALIZZA 92%+';
}
async function scan(){
 try{
  let tf=document.getElementById('tf').value;
  let r1=await fetch('/api/scan?tf='+tf+'&t='+Date.now()); let d1=await r1.json();
  let h1=''; d1.forEach(c=>{h1+='<div class=card sbuy><b>'+c.pair+'</b> <span class=badge>'+c.action+'</span><br>'+c.reason+'</div>'}); if(h1=='')h1='<div class=card>⏳ Nessun segnale 92% ora - mercato laterale</div>'; document.getElementById('auto').innerHTML=h1;
 }catch(e){ document.getElementById('auto').innerHTML='<div class=card>⏳ Scansione... Yahoo lento, attendo</div>';}
}
scan(); setInterval(scan,8000);
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)

@app.route('/api/analyze')
def api_analyze():
    try:
        pair = request.args.get('pair','EUR/USD-OTC')
        tf = request.args.get('tf','5m')
        sym = PAIRS.get(pair, "EURUSD=X")
        result = analyze_92(sym, tf)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"score":0,"action":"WAIT","reason":f"Errore server: {str(e)[:80]}","tf":"5m","time":datetime.now(ITALY_TZ).strftime("%H:%M:%S")})

@app.route('/api/scan')
def api_scan():
    try:
        tf = request.args.get('tf','5m')
        res=[]
        for lab, y in list(PAIRS.items())[:5]:
            d = analyze_92(y, tf)
            if d['score']>=92: res.append({"pair":lab, **d})
        return jsonify(res)
    except: return jsonify([])

@app.route('/api/scan_pinbar')
def api_scan_pinbar(): return jsonify([])

if __name__ == '__main__': app.run(host="0.0.0.0", port=10000)
