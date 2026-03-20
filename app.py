from flask import Flask, render_template, jsonify, request
import yfinance as yf
import numpy as np
import os

app = Flask(__name__)

assets = [
    "BTC-USD","ETH-USD","SOL-USD","XRP-USD",
    "BNB-USD","ADA-USD","DOGE-USD",
    "AVAX-USD","MATIC-USD","DOT-USD"
]

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    gain = np.maximum(deltas, 0)
    loss = -np.minimum(deltas, 0)

    avg_gain = np.mean(gain[:period]) if len(gain) >= period else 0
    avg_loss = np.mean(loss[:period]) if len(loss) >= period else 1

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def get_data():
    results = []

    for asset in assets:
        try:
            data = yf.download(asset, period="1d", interval="5m", progress=False)

            if data.empty:
                continue

            closes = data["Close"].dropna().values

            if len(closes) < 20:
                continue

            price = float(closes[-1])
            prev_price = float(closes[-2])
            change = (price - prev_price) / prev_price

            ema_short = np.mean(closes[-5:])
            ema_long = np.mean(closes[-15:])
            rsi = calculate_rsi(closes)

            # 🔥 PRO SIGNAL LOGIC
            score = 0

            if ema_short > ema_long:
                score += 1
            else:
                score -= 1

            if change > 0.003:
                score += 1
            elif change < -0.003:
                score -= 1

            if rsi < 30:
                score += 1
            elif rsi > 70:
                score -= 2

            if score >= 2:
                signal = "STRONG BUY"
            elif score == 1:
                signal = "BUY"
            elif score == 0:
                signal = "HOLD"
            elif score == -1:
                signal = "SELL"
            else:
                signal = "STRONG SELL"

            confidence = min(max((score + 2) * 25, 10), 100)

            results.append({
                "asset": asset,
                "price": round(price, 2),
                "change": round(change * 100, 2),
                "rsi": round(rsi, 2),
                "signal": signal,
                "confidence": confidence,
                "chart": closes[-30:].tolist()
            })

        except Exception as e:
            print("ERROR:", asset, e)
            continue

    # Market summary
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
    return jsonify([a for a in assets if q in a])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
