"""Crypto AI V5: market data and educational paper-trading calculations."""
import time
import requests
import numpy as np
import pandas as pd

COINS = {"BTC": ("bitcoin", "Bitcoin"), "ETH": ("ethereum", "Ethereum"), "SOL": ("solana", "Solana"), "ADA": ("cardano", "Cardano"), "XRP": ("ripple", "XRP")}
BASE = "https://api.coingecko.com/api/v3"
HEADERS = {"accept": "application/json", "User-Agent": "crypto-ai-v5-educational/1.0"}


def _get(path, params):
    for attempt in range(2):
        try:
            r = requests.get(BASE + path, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 429:
                raise RuntimeError("CoinGecko : quota de requêtes atteint (HTTP 429). Réessaie dans quelques minutes.")
            r.raise_for_status()
            return r.json()
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 0:
                time.sleep(2)
            else:
                raise


def fetch_prices():
    ids = ",".join(x[0] for x in COINS.values())
    data = _get("/simple/price", {"ids": ids, "vs_currencies": "eur", "include_24hr_change": "true"})
    out = {}
    for symbol, (coin_id, name) in COINS.items():
        item = data.get(coin_id, {})
        price = item.get("eur")
        if not isinstance(price, (float, int)) or price <= 0:
            raise ValueError(f"Cours indisponible : {symbol}")
        out[symbol] = {"name": name, "price": float(price), "change_24h": item.get("eur_24h_change")}
    return out


def fetch_history(symbol, days=90):
    if symbol not in COINS:
        raise ValueError("Cryptomonnaie inconnue")
    coin_id = COINS[symbol][0]
    data = _get(f"/coins/{coin_id}/market_chart", {"vs_currency": "eur", "days": days})
    points = data.get("prices", [])
    if len(points) < 35:
        raise ValueError("Historique insuffisant")
    frame = pd.DataFrame(points, columns=["timestamp", "price"])
    frame["date"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
    series = frame.set_index("date")["price"].astype(float).resample("1D").last().dropna()
    if len(series) < 35:
        raise ValueError("Moins de 35 jours de cours disponibles")
    return series


def indicators(prices):
    s = pd.Series(prices, dtype=float).dropna()
    delta = s.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.where(loss.ne(0), 100).where(gain.ne(0), 0)
    rsi = rsi.where(~(gain.eq(0) & loss.eq(0)), 50)
    ema12 = s.ewm(span=12, adjust=False).mean()
    ema26 = s.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    return pd.DataFrame({"price": s, "sma10": s.rolling(10).mean(), "sma30": s.rolling(30).mean(), "rsi": rsi, "macd": macd, "macd_signal": macd_signal})


def signal_from_indicators(row):
    if pd.isna(row["sma10"]) or pd.isna(row["sma30"]) or pd.isna(row["rsi"]):
        return "ATTENDRE", "Données insuffisantes"
    up = row["sma10"] > row["sma30"]
    macd_up = row["macd"] > row["macd_signal"]
    if up and macd_up and row["rsi"] < 70:
        return "ACHETER", "Moyennes mobiles et MACD haussiers, RSI inférieur à 70"
    if not up or row["rsi"] > 75:
        return "VENDRE", "Tendance baissière ou RSI supérieur à 75"
    return "CONSERVER", "Conditions d'achat non réunies"


def portfolio_value(cash, positions, prices):
    return float(cash) + sum(float(q) * prices[s]["price"] for s, q in positions.items())


def backtest(series, initial=10000.0, fee_rate=0.001):
    """Daily long/cash simulation: yesterday's signal trades at today's observed close.

    Educational approximation: close execution is optimistic; no slippage or taxes.
    """
    frame = indicators(series)
    cash, qty = float(initial), 0.0
    records, trades = [], []
    # Yesterday's completed bar produces the instruction for the following bar.
    for i, (date, row) in enumerate(frame.iterrows()):
        price = float(row["price"])
        if i > 0:
            prior = frame.iloc[i - 1]
            action, _ = signal_from_indicators(prior)
            if action == "ACHETER" and qty == 0 and cash > 0:
                gross = cash / (1 + fee_rate)
                fee = gross * fee_rate
                qty = gross / price
                cash = max(0.0, cash - gross - fee)
                trades.append({"Date": date, "Action": "ACHAT", "Prix (€)": price, "Frais (€)": fee})
            elif action == "VENDRE" and qty > 0:
                gross = qty * price
                fee = gross * fee_rate
                cash += gross - fee
                qty = 0.0
                trades.append({"Date": date, "Action": "VENTE", "Prix (€)": price, "Frais (€)": fee})
        records.append({"Date": date, "Portefeuille": cash + qty * price, "Achat-conservation": initial * price / float(frame.iloc[0]["price"])})
    equity = pd.DataFrame(records).set_index("Date")
    peak = equity["Portefeuille"].cummax()
    drawdown = equity["Portefeuille"] / peak - 1
    returns = equity["Portefeuille"].pct_change().dropna()
    return {
        "equity": equity,
        "trades": pd.DataFrame(trades),
        "return_pct": (equity["Portefeuille"].iloc[-1] / initial - 1) * 100,
        "hold_pct": (equity["Achat-conservation"].iloc[-1] / initial - 1) * 100,
        "max_drawdown_pct": drawdown.min() * 100,
        "volatility_pct": returns.std() * np.sqrt(365) * 100 if len(returns) > 1 else 0.0,
    }
