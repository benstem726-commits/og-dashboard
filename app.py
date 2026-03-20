from flask import Flask, render_template, jsonify, request
import yfinance as yf
import numpy as np
import os

app = Flask(__name__)

ASSETS = [
    "BTC-USD","ETH-USD","SOL-USD","XRP-USD",
    "BNB-USD","ADA-USD","DOGE-USD",
    "AVAX-USD","MATIC-USD","DOT-USD"
]

# ✅ SAFE RSI (NO NAN EVER)
def calculate_rsi(prices, period=14):
    prices = np.array(prices)

    if len(prices) < period + 1:
        return 50

    if np.isnan(prices).any():
        return 50

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def get_data():
    results = []

    for asset in ASSETS:
        try:
            data = yf.download(asset, period="1d", interval="5m", progress=False)

            if data is None or data.empty:
                continue

            data = data.dropna()

            if len(data) < 30:
                continue

            ohlc = data.tail(40)

            # ✅ CLEAN CANDLES
            candles = []
            for i, row in ohlc.iterrows():
                if any(np.isnan([row["Open"], row["High"], row["Low"], row["Close"]])):
                    continue

                candles.append({
                    "time": int(i.timestamp()),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"])
                })

            closes = ohlc["Close"].dropna().values

            if len(closes) < 20:
                continue

            price = float(closes[-1])
            prev_price = float(closes[-2])
            change = (price - prev_price) / prev_price

            ema_short = np.mean(closes[-5:])
            ema_long = np.mean(closes[-15:])
            rsi = calculate_rsi(closes)

            if np.isnan(rsi):
                rsi = 50

            # ✅ BALANCED SIGNAL SYSTEM
            score = 0

            if ema_short > ema_long:
                score += 1
            else:
                score -= 1

            if change > 0.005:
                score += 1
            elif change < -0.005:
                score -= 1

            if rsi < 30:
                score += 2
            elif rsi > 70:
                score -= 2

            if score >= 3:
                signal = "STRONG BUY"
            elif score == 2:
                signal = "BUY"
            elif score in [0,1]:
                signal = "HOLD"
            elif score == -1:
                signal = "SELL"
            else:
                signal = "STRONG SELL"

            confidence = min(max((score + 3) * 20, 10), 100)

            results.append({
                "asset": asset,
                "price": round(price, 2),
                "change": round(change * 100, 2),
                "rsi": round(rsi, 2),
                "signal": signal,
                "confidence": confidence,
                "chart": candles
            })

        except Exception as e:
            print("ERROR:", asset, e)
            continue

    bullish = len([x for x in results if "BUY" in x["signal"]])
    bearish = len(results) - bullish

    summary = "Bullish Market 🚀" if bullish >= bearish else "Bearish Market 🔻"

    best_trade = max(results, key=lambda x: x["confidence"]) if results else None

    return results, summary, best_trade


@app.route("/")
def home():
    data, summary, best_trade = get_data()
    return render_template("index.html", data=data, summary=summary, best_trade=best_trade)


@app.route("/predict/<asset>")
def predict(asset):
    data, _, _ = get_data()
    for item in data:
        if item["asset"].lower() == asset.lower():
            return jsonify(item)
    return jsonify({"error": "Not found"})


@app.route("/search")
def search():
    q = request.args.get("q", "").upper()
    return jsonify([a for a in ASSETS if q in a])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
