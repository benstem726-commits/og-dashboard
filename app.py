from flask import Flask, render_template
import yfinance as yf

app = Flask(__name__)

# -----------------------------
# GET MARKET DATA (SAFE)
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

            # Not enough data safety
            if len(close) < 6:
                continue

            # Calculations
            change = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]
            vol = close.pct_change().std()

            # Trend
            trend = "Bullish" if change > 0 else "Bearish"

            # Risk
            risk = "High" if vol > 0.02 else "Low"

            results.append({
                "asset": asset,
                "price": round(close.iloc[-1], 2),
                "trend": trend,
                "risk": risk
            })

        except Exception as e:
            print("ERROR fetching data:", e)
            continue

    return results


# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def home():
    return "🚀 OG Dashboard is LIVE"

# -----------------------------
# LOCAL RUN (not used in Railway but safe)
# -----------------------------
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
