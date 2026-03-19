from flask import Flask, render_template
import yfinance as yf
import pandas as pd
import numpy as np

app = Flask(__name__)

# -----------------------------
# FETCH DATA + SIGNAL LOGIC
# -----------------------------
def get_data():
    assets = ["BTC-USD", "ETH-USD", "AAPL"]
    results = []

    for asset in assets:
        try:
            data = yf.download(asset, period="7d", interval="5m")

            if data is None or data.empty:
                continue

            close = data["Close"]

            # Fix multi-column issue
            if len(close.shape) > 1:
                close = close.iloc[:, 0]

            if len(close) < 20:
                continue

            # -----------------------------
            # CALCULATIONS
            # -----------------------------
            change = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]
            vol = close.pct_change().std()

            # Moving averages (basic signal logic)
            ema_short = close.ewm(span=5).mean().iloc[-1]
            ema_long = close.ewm(span=15).mean().iloc[-1]

            # Trend
            trend = "Bullish" if change > 0 else "Bearish"

            # Risk
            risk = "High" if vol > 0.02 else "Low"

            # Signal logic
            if ema_short > ema_long:
                signal = "BUY"
            else:
                signal = "SELL"

            results.append({
                "asset": asset,
                "price": round(close.iloc[-1], 2),
                "change": round(change * 100, 2),
                "trend": trend,
                "risk": risk,
                "signal": signal
            })

        except Exception as e:
            print("ERROR:", e)
            continue

    return results


# -----------------------------
# ROUTE
# -----------------------------
@app.route("/")
def home():
    try:
        data = get_data()
        return render_template("index.html", data=data)
    except Exception as e:
        print("ERROR:", e)
        return "⚠️ App running but data failed"


# -----------------------------
# RUN (Railway compatible)
# -----------------------------
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
