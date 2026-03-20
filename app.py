from flask import Flask, render_template, jsonify
import yfinance as yf
import pandas as pd
import os

app = Flask(__name__)

# -------------------------------
# RSI FUNCTION (SAFE)
# -------------------------------
def calculate_rsi(series, period=14):
    try:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    except:
        return 50.0


# -------------------------------
# SAFE DATA FETCH
# -------------------------------
def safe_download(asset):
    try:
        data = yf.download(asset, period="5d", interval="15m", progress=False)
        if data is None or data.empty:
            return None
        return data
    except Exception as e:
        print("DOWNLOAD ERROR:", asset, e)
        return None


# -------------------------------
# MAIN LOGIC
# -------------------------------
def get_data():
    assets = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"]
    results = []

    for asset in assets:
        try:
            data = safe_download(asset)
            if data is None:
                continue

            close = data["Close"]

            # Fix multi-column bug
            if hasattr(close, "shape") and len(close.shape) > 1:
                close = close.iloc[:, 0]

            if len(close) < 30:
                continue

            price = float(close.iloc[-1])
            change = float((close.iloc[-1] - close.iloc[-10]) / close.iloc[-10])

            # Indicators
            ema_short = close.ewm(span=9).mean().iloc[-1]
            ema_long = close.ewm(span=21).mean().iloc[-1]
            rsi = calculate_rsi(close)
            volatility = close.pct_change().std()

            trend = "Bullish" if change > 0 else "Bearish"
            risk = "High" if volatility > 0.02 else "Low"

            # SIGNAL (balanced)
            score = 0
            score += 1 if ema_short > ema_long else -1
            score += 1 if change > 0 else -1

            if rsi < 30:
                score += 1
            elif rsi > 70:
                score -= 1

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

            confidence = min(50 + abs(score) * 20, 100)

            chart = list(close.tail(20).values)

            results.append({
                "asset": asset,
                "price": round(price, 2),
                "change": round(change * 100, 2),
                "rsi": round(rsi, 2),
                "trend": trend,
                "risk": risk,
                "signal": signal,
                "confidence": confidence,
                "chart": chart
            })

        except Exception as e:
            print("PROCESS ERROR:", asset, e)
            continue

    # Summary
    if not results:
        return [], "Market Loading...", None

    bullish = sum(1 for x in results if "BUY" in x["signal"])
    bearish = sum(1 for x in results if "SELL" in x["signal"])

    summary = "Bullish Market 🚀" if bullish > bearish else "Bearish Market 🔻"
    best = max(results, key=lambda x: x["confidence"])

    return results, summary, best


# -------------------------------
# ROUTES (SAFE)
# -------------------------------
@app.route("/")
def home():
    try:
        data, summary, best = get_data()
    except Exception as e:
        print("HOME ERROR:", e)
        data, summary, best = [], "Error loading market", None

    return render_template(
        "index.html",
        data=data,
        summary=summary,
        best=best
    )


@app.route("/predict/<asset>")
def predict(asset):
    try:
        data, _, _ = get_data()

        for item in data:
            if item["asset"].lower() == asset.lower():
                return jsonify(item)

        return jsonify({"error": "Asset not found"})

    except Exception as e:
        print("API ERROR:", e)
        return jsonify({"error": "Server error"})


# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
