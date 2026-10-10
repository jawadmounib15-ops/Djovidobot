# Analyzer.py - OTC FORCE FINAL FIX - 1MIN->3MIN
import os, json, time, requests, pandas as pd, yfinance as yf
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, render_template_string
TOKEN = (os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN") or "").strip()
CHAT_ID = (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or "").strip()
ITALIA = ZoneInfo("Europe/Rome")
def send_telegram(msg):
    if not TOKEN or not CHAT_ID: return
    try: requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", params={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except: pass
class OTCForceAnalyzer:
    def __init__(self):
        self.file = "storico_otc_force.json"; self.storico = []
        if os.path.exists(self.file):
            try:
                with open(self.file,'r') as f: self.storico=json.load(f)
            except: self.storico=[]
    def save(self):
        try: 
            with open(self.file,'w') as f: json.dump(self.storico,f,indent=2)
        except: pass
    def analyze(self, df, pair_otc):
        if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        df.columns=[c.lower() for c in df.columns]
        if len(df)<10: return None
        last=df.iloc[-1]; o,h,l,c=float(last['open']),float(last['high']),float(last['low']),float(last['close'])
        body=abs(c-o); upper=h-max(c,o); lower=min(c,o)-l; total=h-l
        if total==0: return None
        score_buy=(lower/total)*100; score_sell=(upper/total)*100; signal=None; score=0; xf=0
        if lower>body*1.2 and score_buy>=55: signal="BUY"; score=score_buy; xf=round(lower/max(body,0.00001),1)
        elif upper>body*1.2 and score_sell>=55: signal="SELL"; score=score_sell; xf=round(upper/max(body,0.00001),1)
        elif body>total*0.1:
            if c>o and lower>upper: signal="BUY"; score=62; xf=1.3
            elif c<o and upper>lower: signal="SELL"; score=62; xf=1.3
        if not signal: return None
        now=datetime.now(ITALIA); expiry=now+timedelta(minutes=3)
        if any(s['pair']==pair_otc and abs(s['timestamp']-now.timestamp())<75 for s in self.storico[-12:]): return None
        seg={"pair":pair_otc,"signal":signal,"score":round(score,1),"x_factor":xf,"prezzo":round(c,5),"time_str":now.strftime("%d/%m %H:%M:%S"),"expiry_time":expiry.strftime("%H:%M:%S"),"expiry_full":expiry.strftime("%d/%m %H:%M:%S"),"timestamp":now.timestamp(),"expiry_timestamp":expiry.timestamp(),"timeframe":"1 MIN OTC","scadenza":"3 MIN","status":"ATTIVO"}
        self.storico.append(seg); self.save()
        send_telegram(f"🔥 {signal} {pair_otc} 3MIN {xf}x {round(score)}% {seg['time_str']}->{seg['expiry_full']} IT")
        return seg
    def get_pending(self):
        now=datetime.now(ITALIA).timestamp()
        for s in self.storico:
            if s['status']=="ATTIVO" and now>s['expiry_timestamp']: s['status']="SCADUTO"
        self.save()
        return [s for s in self.storico if s['status']=="ATTIVO" and now-s['timestamp']<200]
    def get_history(self): return self.storico[-50:][::-1]

OTC_MAP={"EURUSD-OTC":"EURUSD=X","GBPUSD-OTC":"GBPUSD=X","USDJPY-OTC":"USDJPY=X","AUDUSD-OTC":"AUDUSD=X","USDCAD-OTC":"USDCAD=X","EURJPY-OTC":"EURJPY=X","GBPJPY-OTC":"GBPJPY=X","EURGBP-OTC":"EURGBP=X","AUDJPY-OTC":"AUDJPY=X","USDCHF-OTC":"USDCHF=X"}
app=Flask(__name__); analyzer=OTCForceAnalyzer(); scan_count=0; pair_index=0; last_scan=0; last_debug="FORCE FINAL FIX"
HTML_PAGE='''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FORCE OTC FINAL</title><style>body{background:#0a0614;color:#fff;font-family:Arial;padding:10px;margin:0}.top{text-align:center;color:#ff55ff;font-size:26px;font-weight:bold;padding:12px;background:#1a102a;border-radius:12px;border:2px solid #ff55ff}.sub{text-align:center;color:#ffeb00;font-size:12px;margin:6px 0;font-weight:bold}.badge{text-align:center;background:#1e142e;padding:8px;border-radius:8px;margin:8px 0;font-size:11px;border:1px solid #5a2a5a}.card{border-left:6px solid #ff55ff;border-radius:12px;padding:12px;margin-bottom:8px;background:#2a1430}.sell{border-left-color:#ff4444;background:#2a141f}.otc{color:#ff55ff;font-size:10px;font-weight:bold;background:#4a1a4a;padding:3px 6px;border-radius:4px}.exp{background:#ffeb00;color:#000;padding:4px 6px;border-radius:5px;font-weight:bold;font-size:11px}.r{color:#ccc;font-size:11px;margin-top:5px}.old{padding:8px 10px;margin-bottom:4px;background:#161022;color:#888;font-size:11px;display:flex;justify-content:space-between;border-radius:6px}</style></head><body><div class="top" id="clock">00:00:00 ITALIA</div><div class="sub">🔥 FORCE OTC WEEKEND - ANTI LAG 5x - 1MIN → 3MIN</div><div class="badge">🔥 LIVE: {{pending|length}} | SCAN: {{scan_count}} | BATCH: {{batch_info}} | {{last_debug}} | {{now_italia}}</div>{% for h in pending[::-1] %}<div class="card {{'sell' if h.signal=='SELL' else ''}}"><div><span class="otc">FORCE</span> <b>{{h.pair}}</b> <span style="color:{% if h.signal=='BUY' %}#ff55ff{% else %}#ff5555{% endif %};font-weight:bold">{{h.signal}}</span> <span class="exp">SCAD {{h.expiry_time}} IT</span></div><div class="r">⏰ {{h.time_str}} IT | {{h.x_factor}}x {{h.score}}% | {{h.prezzo}}</div></div>{% endfor %}<div style="margin-top:16px"><h3 style="color:#aaa;font-size:12px">📜 STORICO 50</h3>{% for h in history %}<div class="old"><span>{{h.time_str}} <b>{{h.pair}}</b> {{h.signal}} {{h.x_factor}}x</span><span>SCAD {{h.expiry_time}} {{h.status}}</span></div>{% endfor %}</div><audio id="beep" preload="auto"><source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="audio/ogg"></audio><script>function upd(){let now=new Date().toLocaleString('it-IT',{timeZone:'Europe/Rome',hour12:false});document.getElementById('clock').innerText=now+" ITALIA"}setInterval(upd,1000);upd();function playSound(){try{document.getElementById('beep').play()}catch(e){}}if({{pending|length}}>0){setTimeout(playSound,400);setInterval(playSound,2500)}setTimeout(()=>location.reload(),10000);</script></body></html>'''
def do_scan():
    global scan_count,pair_index,last_scan,last_debug
    if time.time()-last_scan<10: return
    last_scan=time.time(); scan_count+=1; all_otc=list(OTC_MAP.items()); batch=[all_otc[(pair_index+i)%len(all_otc)] for i in range(5)]; pair_index=(pair_index+5)%len(all_otc); f=0; names=[]
    for otc_name,real_symbol in batch:
        names.append(otc_name[:3])
        try:
            df=yf.Ticker(real_symbol).history(period="2d",interval="1m",auto_adjust=False)
            if len(df)<10: continue
            if analyzer.analyze(df,otc_name): f+=1
        except: continue
    last_debug=f"FORCE:{f} {','.join(names)} {datetime.now(ITALIA).strftime('%H:%M:%S')}"
@app.route('/')
def home():
    do_scan(); batch_info=f"{pair_index+1}-{(pair_index+5)%len(OTC_MAP)} di {len(OTC_MAP)}"
    return render_template_string(HTML_PAGE,pending=analyzer.get_pending(),history=analyzer.get_history(),scan_count=scan_count,batch_info=batch_info,last_debug=last_debug,now_italia=datetime.now(ITALIA).strftime("%d/%m %H:%M:%S IT"))
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
