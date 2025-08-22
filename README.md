# Resonance.ai 🚨 Breakout Scanner 🚨

Real-time crypto breakout detection powered by **Resonance.ai** (beta-version pre-ML).
This scanner monitors Coinbase trading pairs and pushes instant alerts to Discord when breakout conditions are detected.

---

## ✨ Features

* **Multi-band breakout detection**

  * Fast (10 candles)
  * Medium (15 candles)
  * Slow (20 candles)
* **Two alert modes**

  * Simple mode → quick clean alerts
  * Pro mode → detailed analytics (volume ratios, over-max %, \$/min flow)
* **Discord integration** → sends rich alerts directly to your server
* **Volume protection** → filters out low-liquidity pairs with a dollar/minute floor
* **Lightweight loop** → runs smoothly on cloud platforms like Railway

---

## 📊 Alert Example

**Simple Mode**

```
🚨 BREAKOUT DETECTED 🚨
Pair: `DOGE-USD`
Δ: `+2.45%` | W: `1.30%`
Bands: FAST, MEDIUM
Time: 12:34:56 UTC
```

**Pro Mode**

```
🚨 BREAKOUT DETECTED 🚨
Pair: `DOGE-USD`
Price: $0.08234500
Δ: +2.45%  |  W: 1.30%
Candle: 60s
• FAST (n=10): over max by 1.45%, vol 1200 vs avg 850 (x1.41), $98,000/min
• MEDIUM (n=15): over max by 2.10%, vol 1800 vs avg 1050 (x1.71), $148,000/min
Time: 12:34:56 UTC
```

---

## ⚙️ Configuration

Set parameters via environment variables:

* `SIMPLE_MODE=0` → enables Pro mode
* `ABS_VOL_MIN_USD=2000` → minimum dollar/minute volume filter (default: 2000)
* `DISCORD_WEBHOOK` → your Discord webhook URL

Breakout thresholds (can be tuned in code settings):

* FAST → 1.3% price over previous high + 1.3× volume spike
* MEDIUM → 1.8% price over + 1.7× volume spike
* SLOW → 2.4% price over + 2.2× volume spike

---

## 🚀 Deployment

### Local (Python 3.10+)

```bash
git clone https://github.com/yourname/resonance-breakout-scanner.git
cd resonance-breakout-scanner
pip install -r requirements.txt
python breakout_scanner.py
```

### Cloud (Railway / Render / etc.)

* Add environment variables in your service dashboard
* Deploy the script → logs will show scanning activity
* Alerts will flow to your Discord channel

---

### Discord Setup

To receive alerts in your Discord server:

Create a Webhook
In Discord, right-click your channel → Edit Channel
Go to Integrations → Webhooks → New Webhook
Give it a name (e.g. Resonance Alerts)
Copy the Webhook URL
Add the Webhook to the Scanner paste it directly into the code under DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."

Run the Scanner

Once active, the bot will send breakout alerts directly into your channel.

## 🔮 Roadmap

* Auto-trading integration/dry run learning tool
* Smarter auto coin list rotation (top gainers/losers)
* Machine learning plugin (**WaveScore and HFT hunter)
* Parachute Bot (scans current trades, sets limit orders, cancels and quickly market sells within 1 sec)
* Soliton.ai Trading Arsenal - a free ML powered autotrader/HFT skimmer with multiple trading strategies and three easy set modes (MONK, HAWK and MADMAN) 

---
## 📜 License  
This project is licensed under the **Apache License 2.0** — free and open source.  
You are free to use, modify, and distribute this code (including commercially),  
provided you keep the copyright notice and license text.  

⚠️ No warranties or guarantees are provided.  Use at your own risk. Not financial advice. Always paper trade after making changes to the scanner. 

