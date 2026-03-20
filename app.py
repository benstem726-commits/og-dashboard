from flask import Flask, render_template, jsonify
import yfinance as yf
import pandas as pd
import os

app = Flask(__name__)

# -------------------------------
# RSI CALCULATION
# -------------------------------
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]


# -------------------------------
# MAIN DATA FUNCTION
# -------------------------------
def get_data():
    assets = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"]
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

            if len(close) < 50:
                continue

            price = float(close.iloc[-1])
            change = float((close.iloc[-1] - close.iloc[-10]) / close.iloc[-10])

            # -------------------------------
            # INDICATORS
            # -------------------------------
            ema_short = close.ewm(span=9).mean().iloc[-1]
            ema_long = close.ewm(span=21).mean().iloc[-1]
            rsi_value = calculate_rsi(close)

            volatility = close.pct_change().std()

            # -------------------------------
            # TREND
            # -------------------------------
            trend = "Bullish" if change > 0 else "Bearish"
            risk = "High" if volatility > 0.02 else "Low"

            # -------------------------------
            # SMART SIGNAL LOGIC (BALANCED)
            # -------------------------------
            signal_score = 0

            if ema_short > ema_long:
                signal_score += 1
            else:
                signal_score -= 1

            if rsi_value < 35:
                signal_score += 1
            elif rsi_value > 65:
                signal_score -= 1

            if change > 0:
                signal_score += 1
            else:
                signal_score -= 1

            # Final Signal
            if signal_score >= 2:
                signal = "STRONG BUY"
            elif signal_score == 1:
                signal = "BUY"
            elif signal_score == 0:
                signal = "HOLD"
            elif signal_score == -1:
                signal = "SELL"
            else:
                signal = "STRONG SELL"

            # -------------------------------
            # CONFIDENCE
            # -------------------------------
            confidence = 50 + abs(signal_score) * 20
            confidence = min(confidence, 100)

            # -------------------------------
            # CHART DATA
            # -------------------------------
            chart_data = list(close.tail(20).values)

            results.append({
                "asset": asset,
                "price": round(price, 2),
                "change": round(change * 100, 2),
                "rsi": round(rsi_value, 2),
                "trend": trend,
                "risk": risk,
                "signal": signal,
                "confidence": confidence,
                "chart": chart_data
            })

        except Exception as e:
            print("ERROR:", asset, e)
            continue

    # -------------------------------
    # MARKET SUMMARY
    # -------------------------------
    if len(results) == 0:
        summary = "No Data"
        best_trade = None
    else:
        bullish = sum(1 for x in results if "BUY" in x["signal"])
        bearish = sum(1 for x in results if "SELL" in x["signal"])

        summary = "Bullish Market 🚀" if bullish > bearish else "Bearish Market 🔻"

        best_trade = max(results, key=lambda x: x["confidence"])

    return results, summary, best_trade 
     
# -------------------------------
# HOME ROUTE (FIXED)
# -------------------------------
@app.route("/")
def home():
    data, summary, best = get_data()
    return render_template(
        "index.html",
        data=data,
        summary=summary,
        best=best
    )


# -------------------------------
# API ROUTE (AGENT MODE)
# -------------------------------
@app.route("/predict/<asset>")
def predict(asset):
    data, _, _ = get_data()

    for item in data:
        if item["asset"].lower() == asset.lower():
            return jsonify(item)

    return jsonify({"error": "Asset not found"})


# -------------------------------
# RUN (RAILWAY SAFE)
# -------------------------------
    if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
  
