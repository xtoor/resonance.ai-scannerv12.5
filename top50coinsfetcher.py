import time, math, json, statistics
from datetime import datetime, timedelta, timezone
import requests

TOP_N = 50
GRANULARITY_SEC = 60
LOOKBACK_MIN = 45
MIN_USD_PER_MIN = 2000.0
MAX_SPREAD_PCT = .5/100
MIN_PRICE_USD = 0.0001
EXCLUDE_BASES = {"USDC","DAI","USDT","PYUSD"}
OUTPUT_PATH = "top50_usd_pairs.txt"

EXCHANGE_API = "https://api.exchange.coinbase.com"

session = requests.Session()
session.headers.update({"User-Agent": "usd-curator/1.0"})

def get_products_usd():
    r = session.get(f"{EXCHANGE_API}/products", timeout=20)
    r.raise_for_status()
    products = r.json()
    usd = []
    for p in products:
        if p.get("quote_currency") == "USD" and p.get("status") == "online" and not p.get("trading_disabled", False):
            base = p.get("base_currency", "")
            if base in EXCLUDE_BASES:
                continue
            usd.append(p["id"])
    return usd

def get_l1_spread_pct(product_id):
    try:
        r = session.get(f"{EXCHANGE_API}/products/{product_id}/book", params={"level": 1}, timeout=10)
        r.raise_for_status()
        data = r.json()
        bids = data.get("bids", []); asks = data.get("asks", [])
        if not bids or not asks: return None
        bid = float(bids[0][0]); ask = float(asks[0][0])
        mid = (bid + ask) / 2.0
        if mid <= 0: return None
        return (ask - bid) / mid
    except:
        return None

def get_recent_candles(product_id, granularity=60, lookback_min=30):
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=lookback_min + 2)
    params = {"start": start.isoformat(), "end": end.isoformat(), "granularity": granularity}
    try:
        r = session.get(f"{EXCHANGE_API}/products/{product_id}/candles", params=params, timeout=20)
        if r.status_code == 200:
            data = r.json()
            data.sort(key=lambda x: x[0])
            return data
    except:
        return []

def candle_metrics_usd(candles):
    if not candles: return None
    closes = [c[4] for c in candles]
    vols_base = [c[5] for c in candles]
    usd_vols = [vols_base[i] * closes[i] for i in range(len(candles))]
    avg_usd_per_min = sum(usd_vols) / max(1, len(usd_vols))
    last_close = closes[-1]
    rets = [math.log(closes[i] / closes[i-1]) for i in range(1, len(closes)) if closes[i-1] > 0]
    stdev = statistics.pstdev(rets) if len(rets) >= 2 else 0.0
    highs = [c[2] for c in candles]; lows = [c[1] for c in candles]
    hi = max(highs); lo = min(lows)
    rng_pct = (hi - lo) / lo if lo > 0 else 0.0
    return {"avg_usd_per_min": avg_usd_per_min, "last_close": last_close, "ret_stdev": stdev, "range_pct": rng_pct}

def score_coin(m):
    vol_score = (m["ret_stdev"] * 10000.0) + (m["range_pct"] * 100.0)
    liq_bonus = min(1.0, (m["avg_usd_per_min"] / (MIN_USD_PER_MIN*3.0)))
    return vol_score + liq_bonus

def main():
    products = get_products_usd()
    print(f"Found {len(products)} USD pairs. Scanning...\n")

    rows = []
    for i, pid in enumerate(products, 1):
        spread = get_l1_spread_pct(pid)
        if spread is None or spread > MAX_SPREAD_PCT:
            print(f"[{i}/{len(products)}] {pid:<12} ❌ skipped (spread {spread*100 if spread else 0:.3f}%)")
            continue

        candles = get_recent_candles(pid, GRANULARITY_SEC, LOOKBACK_MIN)
        if not candles:
            print(f"[{i}/{len(products)}] {pid:<12} ❌ skipped (no candles)")
            continue

        m = candle_metrics_usd(candles)
        if not m:
            print(f"[{i}/{len(products)}] {pid:<12} ❌ skipped (metrics fail)")
            continue

        if m["last_close"] < MIN_PRICE_USD:
            print(f"[{i}/{len(products)}] {pid:<12} ❌ skipped (price {m['last_close']:.6f} < min)")
            continue
        if m["avg_usd_per_min"] < MIN_USD_PER_MIN:
            print(f"[{i}/{len(products)}] {pid:<12} ❌ skipped ($/min {m['avg_usd_per_min']:.0f} < {MIN_USD_PER_MIN})")
            continue

        s = score_coin(m)
        rows.append({"product_id": pid, "score": s})
        print(f"[{i}/{len(products)}] {pid:<12} ✅ kept | price={m['last_close']:.6f} $/min={m['avg_usd_per_min']:.0f} spread={spread*100:.3f}% score={s:.2f}")

        if i % 10 == 0:
            time.sleep(0.5)

    rows.sort(key=lambda x: x["score"], reverse=True)
    top_ids = [r["product_id"] for r in rows[:TOP_N]]

    with open(OUTPUT_PATH, "w") as f:
        f.write(json.dumps(top_ids))

    print(f"\nSaved {len(top_ids)} pairs to {OUTPUT_PATH}")
    print("Top 10 preview:", top_ids[:10])

if __name__ == "__main__":
    main()
