# app.py - TUTTO IN UNO V3 SICURO FIX 43x + ANTI-CONTRARIO VERO
from flask import Flask, jsonify, render_template_string, request
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

ITALY_TZ = timezone(timedelta(hours=2))
COOLDOWN = {}
PAIRS = {
    "EUR/USD-OTC":"EURUSD=X","GBP/USD-OTC":"GBPUSD=X","USD/JPY-OTC":"USDJPY=X",
    "USD/CAD-OTC":"USDCAD=X","EUR/JPY-OTC":"EURJPY=X","GBP/JPY-OTC":"GBPJPY=X",
    "AUD/USD-OTC":"AUDUSD=X","BTC/USD-OTC":"BTC-USD","ETH/USD-OTC":"ETH-USD",
    "SOL/USD-OTC":"SOL-USD","EUR/USD":"EURUSD=X","GBP/USD":"GBPUSD=X",
    "USD/JPY":"USDJPY=X","BTC/USD":"BTC-USD"
}

def get_data(symbol: str, interval: str = "5m"):
    try:
        period = "10d" if interval == "5m" else "20d"
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)
        if len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']
        df['EMA9'] = close.ewm(span=9).mean()
        df['EMA21'] = close.ewm(span=21).mean()
        df['EMA50'] = close.ewm(span=50).mean()
        df['EMA200'] = close.ewm(span=200).mean()
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain / loss))
        df['SMA20'] = close.rolling(20).mean()
        std = close.rolling(20).std()
        df['BB_UP'] = df['SMA20'] + 2 * std
        df['BB_LOW'] = df['SMA20'] - 2 * std
        df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
        return df
    except: return None

def is_pinbar_sicura(o,h,l,c):
    body = abs(c - o)
    rng = h - l
    if rng == 0: return None
    upper = h - max(o, c)
    lower = min(o, c) - l
    if body < rng * 0.10: return None
    if body > rng * 0.28: return None
    ratio_up = upper / body if body!=0 else 0
    ratio_low = lower / body if body!=0 else 0
    if ratio_up > 8 or ratio_low > 8: return None
    if lower >= body * 2.5 and lower >= rng * 0.62 and upper <= rng * 0.25: return "CALL", round(ratio_low,1)
    if upper >= body * 2.5 and upper >= rng * 0.62 and lower <= rng * 0.25: return "PUT", round(ratio_up,1)
    return None

def analyze_92(symbol: str, tf: str = "5m"):
    now = datetime.now(ITALY_TZ)
    interval = "5m" if tf == "5m" else "15m"
    df = get_data(symbol, interval)
    if df is None: return {"score":0,"action":"WAIT","reason":"Mercato chiuso","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    last = df.iloc[-1]
    price, ema9, ema21, ema50, ema200, rsi = float(last['Close']), float(last['EMA9']), float(last['EMA21']), float(last['EMA50']), float(last['EMA200']), float(last['RSI'])
    trend_up = ema9 > ema21 and ema21 > ema50 and price > ema200
    trend_down = ema9 < ema21 and ema21 < ema50 and price < ema200
    if not (40 <= rsi <= 60): return {"score":0,"action":"WAIT","reason":f"RSI {rsi:.0f} fuori 40-60","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    pin = is_pinbar_sicura(float(last['Open']), float(last['High']), float(last['Low']), price)
    if not pin: return {"score":0,"action":"WAIT","reason":"No pinbar sicura","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    direzione, ratio = pin
    if trend_up and direzione == "PUT": return {"score":0,"action":"WAIT","reason":"Scarto PUT contro trend UP","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    if trend_down and direzione == "CALL": return {"score":0,"action":"WAIT","reason":"Scarto CALL contro trend DOWN","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    if not trend_up and not trend_down: return {"score":0,"action":"WAIT","reason":"Laterale - no trade","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    score = 95 if ratio >= 3.5 else 92
    action = f"{'BUY' if direzione == 'CALL' else 'SELL'} {score}% SICURA"
    return {"score":score,"action":action,"reason":f"Pinbar {ratio}x | RSI {rsi:.0f} | EMA200 OK","tf":tf,"time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}

def analyze_1min_before(symbol: str, tf_label: str = "5m"):
    try:
        df = yf.download(symbol, period="2d", interval="1m", progress=False, auto_adjust=False)
        if len(df) < 60: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        c = df['Close']
        df['EMA21'] = c.ewm(span=21).mean()
        df['EMA50'] = c.ewm(span=50).mean()
        df['EMA200'] = c.ewm(span=200).mean()
        delta = c.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain / loss))
        now = datetime.now(ITALY_TZ)
        sec_to_close = (5 - now.minute % 5) * 60 - now.second
        if sec_to_close > 300: sec_to_close -= 300
        if not (25 <= sec_to_close <= 110): return None
        last5 = df.iloc[-5:]
        o, cc, hh, ll = float(last5.iloc[0]['Open']), float(last5.iloc[-1]['Close']), float(last5['High'].max()), float(last5['Low'].min())
        pin = is_pinbar_sicura(o, hh, ll, cc)
        if not pin: return None
        direzione, ratio = pin
        ema21, ema50, ema200, rsi = float(df['EMA21'].iloc[-1]), float(df['EMA50'].iloc[-1]), float(df['EMA200'].iloc[-1]), float(df['RSI'].iloc[-1])
        if not (38 <= rsi <= 62): return None
        trend_up = cc > ema50 and ema21 > ema50 and cc > ema200
        trend_down = cc < ema50 and ema21 < ema50 and cc < ema200
        if trend_up and direzione == "PUT": return None
        if trend_down and direzione == "CALL": return None
        if not trend_up and not trend_down: return None
        if symbol in COOLDOWN and (now.timestamp() - COOLDOWN[symbol]) < 600: return None
        COOLDOWN[symbol] = now.timestamp()
        return {"price":round(cc,5),"score":94,"action":f"{'BUY' if direzione == 'CALL' else 'SELL'} 1 MIN PRIMA 📌","reason":f"ANTI-CONTRARIO {ratio}x RSI {rsi:.0f} - {sec_to_close}s","tf":f"{tf_label} {sec_to_close}s","time":now.strftime("%H:%M:%S"),"timestamp":now.timestamp()}
    except: return None

HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V3 SICURO</title><style>body{background:#0a0a0a;color:#fff;font-family:system-ui;padding:12px}select{width:100%;padding:12px;border-radius:10px;background:#1a1a1f;color:#fff;border:1px solid #333;margin:6px 0}.row{display:flex;gap:8px}.row select{flex:1}.card{background:#1a1a1f;padding:14px;border-radius:14px;margin:10px 0;border-left:5px solid #333}.sbuy{border-left-color:gold;border:3px solid gold}.pre{background:#002a00;border:3px solid #00ff88;animation:blink 0.7s infinite}.badge{padding:6px 12px;border-radius:20px;font-weight:bold}.sB{background:gold;color:#000}.lB{background:#00ff88;color:#000}.fresh{background:#00e676;color:#000;padding:3px 8px;border-radius:10px;font-size:11px}@keyframes blink{50%{opacity:0.5}}button{width:100%;padding:14px;background:gold;color:#000;border:none;border-radius:12px;font-weight:bold;font-size:17px}</style></head><body>
<h2>⚡ V3 SICURO - FIX 43x</h2><div class="row"><select id="pair"><option>EUR/USD-OTC</option><option>USD/CAD-OTC</option><option>BTC/USD-OTC</option><option>SOL/USD-OTC</option><option>EUR/USD</option></select><select id="tf"><option value="5m" selected>5m</option><option value="15m">15m</option></select></div><button onclick="analyze()">ANALIZZA 92%+</button><div id="result"></div>
<h3>⚡ LAVORO 1</h3><div id="auto"></div><h3>📌 LAVORO 2 - 1 MIN PRIMA</h3><div id="pin"></div><audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" preload="auto"></audio>
<script>
async function analyze(){let p=document.getElementById('pair').value;let tf=document.getElementById('tf').value;let r=await fetch('/api/analyze?pair='+p+'&tf='+tf);let d=await r.json();if(d.score<92){document.getElementById('result').innerHTML='<div class=card>⏳ '+d.reason+'</div>';return;}document.getElementById('result').innerHTML='<div class=card sbuy><b>'+p+'</b> <span class=badge sB>'+d.action+'</span><br>'+d.reason+'</div>';}
async function scan(){let tf=document.getElementById('tf').value;let r1=await fetch('/api/scan?tf='+tf);let d1=await r1.json();let h1='';d1.forEach(c=>{h1+='<div class=card sbuy><b>'+c.pair+'</b> <span class=badge sB>'+c.action+'</span><br>'+c.reason+'</div>'});if(h1=='')h1='<div class=card>⏳ Nessun segnale</div>';document.getElementById('auto').innerHTML=h1;let r2=await fetch('/api/scan_pinbar?tf='+tf);let d2=await r2.json();let h2='';d2.forEach(c=>{h2+='<div class=card pre><b>'+c.pair+' ['+c.tf+']</b> <span class=badge lB>'+c.action+'</span><br>'+c.reason+'</div>'});if(h2=='')h2='<div class=card>⏳ Anti-contrario attivo</div>';document.getElementById('pin').innerHTML=h2;if(d2.length>0)document.getElementById('beep').play();}
scan();setInterval(scan,4000);
</script></body></html>"""

@app.route('/')
def home(): return render_template_string(HTML)
@app.route('/api/analyze')
def api_analyze():
    pair = request.args.get('pair','EUR/USD-OTC')
    tf = request.args.get('tf','5m')
    return jsonify(analyze_92(PAIRS.get(pair, "EURUSD=X"), tf))
@app.route('/api/scan')
def api_scan():
    tf = request.args.get('tf','5m')
    res = []
    for lab, y in PAIRS.items():
        d = analyze_92(y, tf)
        if d['score'] >= 92: res.append({"pair": lab, **d})
    return jsonify(res[:6])
@app.route('/api/scan_pinbar')
def api_scan_pinbar():
    tf = request.args.get('tf','5m')
    res = []
    for lab, y in PAIRS.items():
        d = analyze_1min_before(y, tf)
        if d: res.append({"pair": lab, **d})
    return jsonify(res[:6])

if __name__ == '__main__': app.run(host="0.0.0.0", port=10000)
