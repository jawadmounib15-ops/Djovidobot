import yfinance as yf, requests, time, os
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
COPPIE = [("EURUSD=X","EUR/USD"),("GBPUSD=X","GBP/USD"),("AUDUSD=X","AUD/USD"),("USDJPY=X","USD/JPY"),("GBPJPY=X","GBP/JPY"),("EURJPY=X","EUR/JPY")]

def send(m):
  try:
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"})
  except: pass

send("✅ Bot PRE-AVVISO attivo! Ti avviso 1 min prima della PinBar")

while True:
  for ticker, nome in COPPIE:
    try:
      df = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
      if len(df) < 60: continue

      # Raggruppiamo a candele da 5 minuti ma guardiamo quella CORRENTE che si sta formando
      # Prendiamo gli ultimi 5 minuti
      ultimi_5 = df.tail(5)
      open_5 = float(ultimi_5.iloc[0]['Open'])
      close_5 = float(ultimi_5.iloc[-1]['Close'])
      high_5 = float(ultimi_5['High'].max())
      low_5 = float(ultimi_5['Low'].min())

      corpo = abs(close_5 - open_5)
      if corpo == 0: corpo = 0.00001
      sotto = min(open_5, close_5) - low_5
      sopra = high_5 - max(open_5, close_5)

      # Quanto manca alla chiusura candela 5m? (es. 17:43 -> mancano 2 min a 17:45)
      minuto = datetime.now().minute % 5
      manca = 5 - minuto
      secondi = datetime.now().second

      # PRE-AVVISO: wick già grande, siamo negli ultimi 90 secondi
      is_pin_forming = sotto > corpo * 2.0 and sopra < corpo * 1.0 and close_5 > open_5

      if is_pin_forming and manca <= 1:
        send(f"⚠️ *PRE-AVVISO {nome}*\nPinBar rialzista SI STA FORMANDO!\nPrezzo: {close_5:.5f}\nChiusura tra {60 - secondi} sec\nPreparati su Pocket Option! 🔥")
        time.sleep(240) # evita spam 4 min

      # CONFERMA dopo chiusura
      elif is_pin_forming and manca == 0 and secondi < 15:
        send(f"✅ *CONFERMA PIN BAR {nome}*\nEntra ORA! Prezzo {close_5:.5f}")
        time.sleep(240)

    except Exception as e:
      print(e)
      pass
  time.sleep(15) # controlla ogni 15 sec, non ogni 5 min!
