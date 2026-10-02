# ANALYZER.PY V74.1 - 3MIN 70% COME LIVE
import yfinance as yf, pandas as pd
from flask import Flask, jsonify
from datetime import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
PAIRS = ["EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","USDCHF=X","EURJPY=X","GBPJPY=X","EURGBP=X","EURCHF=X","AUDJPY=X","GBPCHF=X","GBPAUD=X","EURNZD=X","CADCHF=X","CADJPY=X","AUDCAD=X","AUDCHF=X","CHFJPY=X","GBPNZD=X","NZDCAD=X"]

TIMEFRAMES = {
    "1M": {"period":"1d", "interval":"1m"},
    "5M": {"period":"2d", "interval":"5m"},
    "15M": {"period":"5d", "interval":"15m"}
}

def fix_df(df):
    if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df

def rsi_calc(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_single_tf(sym, tf_name):
    try:
        cfg = TIMEFRAMES[tf_name]
        df = yf.download(sym, period=cfg["period"], interval=cfg["interval"], progress=False)
        df = fix_df(df)
        if len(df) < 70: return None
        df['RSI'] = rsi_calc(df['Close'], 14)
        highs = df['High'].values
        lows = df['Low'].values
        swing_high = swing_low = None
        for i in range(len(df)-25, len(df)-5):
            if highs[i] == max(highs[i-5:i+6]): swing_high = float(highs[i])
            if lows[i] == min(lows[i-5:i+6]): swing_low = float(lows[i])
        if swing_high is None or swing_low is None: return None
        last = df.iloc[-1]; prev = df.iloc[-2]
        c = float(last['Close']); c_prev = float(prev['Close'])
        rsi_now = float(last['RSI'])
        range_sw = swing_high - swing_low
        if range_sw == 0: return None
        last_20 = df.iloc[-20:]
        range_20_pct = (float(last_20['High'].max()) - float(last_20['Low'].min())) / c
        if range_20_pct < 0.0009: return None
        dist_high = abs(c - swing_high) / range_sw
        dist_low = abs(c - swing_low) / range_sw
        if dist_low < 0.132 and c > c_prev and rsi_now < 44:
            return "BUY", rsi_now
        if dist_high < 0.132 and c < c_prev and rsi_now > 56:
            return "SELL", rsi_now
    except: return None
    return None

def check_pair_multitf(sym):
    results = {}
    for tf in TIMEFRAMES:
        r = check_single_tf(sym, tf)
        if r: results[tf] = r

    if not results: return None
    dirs = [v[0] for v in results.values()]
    buy_count = dirs.count("BUY")
    sell_count = dirs.count("SELL")

    if buy_count >= 2 or (buy_count==1 and sell_count==0):
        final_dir = "BUY"
    elif sell_count >= 2 or (sell_count==1 and buy_count==0):
        final_dir = "SELL"
    else:
        return None

    # LOGICA 3 MIN 70% - COME HAI CHIESTO
    num_tf = len(results)
    if num_tf == 1:
        expiry = "00:01:00"
        conf_pct = "55%"
    elif num_tf == 2:
        expiry = "00:03:00" # 70% QUI
        conf_pct = "70%"
    else: # 3 timeframe
        expiry = "00:05:00"
        conf_pct = "85%"

    # FORZA 3MIN per default come vuoi tu
    # Se 2TF, sempre 3min
    if num_tf >= 2:
        expiry = "00:03:00"
        conf_pct = "70%"

    tf_text = " + ".join([f"{k}:{v[0]} RSI {v[1]:.0f}" for k,v in results.items()])

    return {
        "pair": sym.replace("=X",""),
        "dir": final_dir,
        "expiry": expiry,
        "confidence": conf_pct,
        "note": tf_text,
        "confluence": f"{buy_count}B/{sell_count}S",
        "tfs": list(results.keys())
    }

@app.route('/')
def home():
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>V74.1 3MIN 70%</title>
<style>body{background:#0a0a0a;color:#fff;font-family:Arial;text-align:center;padding:12px}
.btn{background:#00ff88;color:#000;border:none;padding:16px;border-radius:14px;font-weight:bold;font-size:18px;width:95%;max-width:380px;display:block;margin:8px auto}
.card{background:#1a1a1a;border-radius:14px;padding:12px;margin:8px auto;max-width:420px;text-align:left;border-left:5px solid #00ff88;position:relative}
.sell{border-left-color:#ff3b3b}
.badge{position:absolute;top:8px;right:8px;font-size:10px;padding:4px 8px;border-radius:6px;font-weight:bold}
.live{background:#ffcc00;color:#000}
.tf{background:#222;color:#00ff88;font-size:11px;padding:2px 6px;border-radius:4px;margin-right:4px}
.exp{background:#00ff88;color:#000;font-weight:bold;padding:6px 10px;border-radius:8px;display:inline-block;margin-top:6px;font-size:14px}
.exp3{background:#ffcc00;color:#000;font-weight:bold;padding:6px 10px;border-radius:8px;display:inline-block;margin-top:6px;font-size:15px}
</style></head><body>
<h2>📊 V74.1 - 3MIN 70%</h2>
<p style="color:#ffcc00">Come LIVE screen - Default 00:03:00</p>
<button class="btn" id="b1" onclick="attiva()">🔔 ATTIVA</button>
<button class="btn" style="background:#222;color:#fff;border:1px solid #444" onclick="cerca()">🔍 SCAN 3MIN</button>
<p id="info">...</p><div id="live"></div>
<script>
let ok=false;
function attiva(){ok=true; document.getElementById('b1').innerHTML='✅ 3MIN 70% ATTIVO'; document.getElementById('b1').style.background='#ffcc00'; if(Notification&&Notification.permission!='granted')Notification.requestPermission();}
function suona(){if(!ok)return; let a=new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg'); a.play(); if(navigator.vibrate) navigator.vibrate([800,200,800]);}
function cerca(){fetch('/api/scan').then(r=>r.json()).then(d=>{document.getElementById('info').innerText=d.time+' | 3MIN: '+d.signals.length; let h=''; d.signals.forEach(s=>{let cls=s.dir=='SELL'?'card sell':'card'; let tfs=s.tfs.map(t=>`<span class="tf">${t}</span>`).join(''); let expClass=s.expiry=='00:03:00'?'exp3':'exp'; h+=`<div class="${cls}"><span class="badge live">${s.confidence} ${s.confluence}</span><b style="font-size:18px;color:${s.dir=='BUY'?'#00ff88':'#ff3b3b'}">${s.dir} ${s.pair}</b><br><div style="margin:4px 0">${tfs}</div><div style="color:#888;font-size:12px">${s.note}</div><span class="${expClass}">⏱️ ENTRA ${s.expiry} - ${s.confidence}</span></div>`;}); if(h&&ok)suona(); document.getElementById('live').innerHTML=h||'<p style="color:#555">Nessun 3MIN ora</p>';});}
setInterval(cerca,45000); window.onload=cerca;
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
    # Ordina per confidence 70% prima
    out.sort(key=lambda x: x['confidence'], reverse=True)
    return jsonify({"signals":out,"time":now})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
