from flask import Flask, render_template
import yfinance as yf
import pandas as pd
import numpy as np
import json

app = Flask(__name__)

# -----------------------------
# FETCH DATA + SMART SIGNAL
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

            if len(close.shape) > 1:
                close = close.iloc[:, 0]

            if len(close) < 20:
                continue

            # CHANGE + VOL
            change = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]
            vol = close.pct_change().std()

            # EMA
            ema_short = close.ewm(span=5).mean().iloc[-1]
            ema_long = close.ewm(span=15).mean().iloc[-1]

            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1]

            # TREND
            trend = "Bullish" if change > 0 else "Bearish"

            # RISK
            risk = "High" if vol > 0.02 else "Low"

            # SMART SIGNAL
            if ema_short > ema_long and rsi_value < 70:
                signal = "BUY"
            elif ema_short < ema_long and rsi_value > 30:
                signal = "SELL"
            else:
                signal = "HOLD"

            # CHART DATA (last 30 points)
            chart_data = close.tail(30).tolist()

            results.append({
                "asset": asset,
                "price": round(close.iloc[-1], 2),
                "change": round(change * 100, 2),
                "trend": trend,
                "risk": risk,
                "signal": signal,
                "rsi": round(rsi_value, 2),
                "chart": chart_data
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
    data = get_data()
    return render_template("index.html", data=data)


# -----------------------------
# RUN
# -----------------------------
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
