"""Crypto AI V5 — educational simulated trading dashboard; never places real orders."""
import datetime as dt
import json
import math
import pandas as pd
import streamlit as st
from engine import COINS, fetch_prices, fetch_history, indicators, signal_from_indicators, portfolio_value, backtest

st.set_page_config(page_title="Crypto AI V5", page_icon="📈", layout="wide")
st.title("📈 Crypto AI V5 — Laboratoire de trading virtuel")
st.warning("Argent 100 % fictif. Signaux techniques déterministes, pas d'IA prédictive. Aucun ordre réel.")
st.caption("Données CoinGecko indicatives et parfois indisponibles. Les simulations ne prédisent pas les performances futures.")
START_CASH = 10000.0
FEE = 0.001

@st.cache_data(ttl=90, show_spinner=False)
def cached_prices():
    return fetch_prices()

@st.cache_data(ttl=1800, show_spinner=False)
def cached_history(symbol, days):
    return fetch_history(symbol, days)

if "cash" not in st.session_state:
    st.session_state.cash = START_CASH
    st.session_state.positions = {s: 0.0 for s in COINS}
    st.session_state.trades = []

with st.sidebar:
    st.header("Paramètres du robot fictif")
    auto_amount = st.number_input("Budget par achat (€)", 10.0, 500.0, 100.0, 10.0)
    max_allocation = st.slider("Allocation maximale par crypto (%)", 5, 30, 20, 5) / 100
    if st.button("🔄 Actualiser les cours"):
        cached_prices.clear()
        st.rerun()
    st.caption("Le robot ne s'exécute que sur clic, jamais en arrière-plan.")

try:
    prices = cached_prices()
except Exception as exc:
    st.error("Impossible de récupérer les cours actuellement.")
    st.caption(str(exc))
    st.stop()

value = portfolio_value(st.session_state.cash, st.session_state.positions, prices)
a, b, c = st.columns(3)
a.metric("Portefeuille virtuel", f"{value:,.2f} €")
b.metric("Liquidités virtuelles", f"{st.session_state.cash:,.2f} €")
c.metric("Performance virtuelle", f"{(value / START_CASH - 1) * 100:+.2f} %")

st.subheader("Marché crypto")
st.dataframe(pd.DataFrame([{"Crypto": s, "Nom": d["name"], "Prix (€)": d["price"], "Variation 24 h (%)": d["change_24h"]} for s, d in prices.items()]), hide_index=True, use_container_width=True)

st.subheader("Analyse technique et explication")
symbol = st.selectbox("Crypto à analyser", list(COINS))
try:
    history = cached_history(symbol, 90)
    analysis = indicators(history)
    latest = analysis.iloc[-1]
    decision, reason = signal_from_indicators(latest)
    st.line_chart(analysis[["price", "sma10", "sma30"]].rename(columns={"price": "Prix", "sma10": "SMA 10", "sma30": "SMA 30"}))
    st.write(f"**Signal technique : {decision}** — {reason}")
    st.write(f"RSI : {latest['rsi']:.1f} | MACD : {latest['macd']:.4f} | Signal MACD : {latest['macd_signal']:.4f}")
    st.caption("Ces règles sont des hypothèses pédagogiques, pas des recommandations d'achat ou de vente.")
except Exception as exc:
    st.info("Analyse historique indisponible pour cette crypto.")
    st.caption(str(exc))

st.subheader("🧪 Backtesting historique")
st.caption("Le signal d'une journée est appliqué au cours de clôture du jour suivant. Hypothèse optimiste : aucun slippage ni spread. Les frais fictifs sont de 0,1 % par transaction.")
back_symbol = st.selectbox("Crypto pour le backtest", list(COINS), key="back_symbol")
back_days = st.selectbox("Période historique", [90, 180, 365], index=0, format_func=lambda n: f"{n} jours")
if st.button("Lancer le backtest"):
    try:
        series = cached_history(back_symbol, back_days)
        result = backtest(series, START_CASH, FEE)
        st.session_state.backtest_result = result
        st.session_state.backtest_label = f"{back_symbol} — {back_days} jours"
    except Exception as exc:
        st.session_state.pop("backtest_result", None)
        st.error(f"Backtest indisponible : {exc}")
if "backtest_result" in st.session_state:
    result = st.session_state.backtest_result
    st.write(f"**Résultats : {st.session_state.backtest_label}**")
    x, y, z = st.columns(3)
    x.metric("Stratégie simulée", f"{result['return_pct']:+.2f} %")
    y.metric("Achat-conservation", f"{result['hold_pct']:+.2f} %")
    z.metric("Perte maximale depuis un sommet", f"{result['max_drawdown_pct']:.2f} %")
    st.line_chart(result["equity"])
    st.caption(f"Volatilité annualisée indicative : {result['volatility_pct']:.1f} % | Transactions : {len(result['trades'])}. Backtest simplifié, sans validation hors échantillon.")
    if not result["trades"].empty:
        st.dataframe(result["trades"], hide_index=True, use_container_width=True)


def trade(symbol, side, amount, source):
    price = prices[symbol]["price"]
    fee = amount * FEE
    if not math.isfinite(amount) or amount <= 0:
        return "Montant invalide."
    if side == "ACHAT":
        if amount + fee > st.session_state.cash + 1e-8:
            return "Liquidités insuffisantes."
        st.session_state.cash -= amount + fee
        st.session_state.positions[symbol] += amount / price
    else:
        if amount / price > st.session_state.positions[symbol] + 1e-10:
            return "Position insuffisante."
        st.session_state.positions[symbol] = max(0.0, st.session_state.positions[symbol] - amount / price)
        st.session_state.cash += amount - fee
    st.session_state.trades.append({"Date UTC": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "Crypto": symbol, "Action": side, "Montant (€)": round(amount, 2), "Prix (€)": price, "Frais (€)": round(fee, 4), "Source": source})
    return None

st.subheader("🤖 Robot virtuel — un cycle sur demande")
st.caption("Le robot consulte cinq historiques, au maximum un ordre fictif par crypto et par clic. Les requêtes peuvent être limitées par CoinGecko.")
if st.button("Analyser et simuler un cycle", type="primary"):
    notes = []
    for sym in COINS:
        try:
            series = cached_history(sym, 90)
            row = indicators(series).iloc[-1]
            action, reason = signal_from_indicators(row)
            holding = st.session_state.positions[sym] * prices[sym]["price"]
            total = portfolio_value(st.session_state.cash, st.session_state.positions, prices)
            if action == "ACHETER" and holding < 0.01:
                amount = min(auto_amount, max(0.0, total * max_allocation - holding), st.session_state.cash / (1 + FEE))
                if amount >= 10:
                    error = trade(sym, "ACHAT", amount, "Robot virtuel")
                    notes.append(f"{sym} : achat fictif {amount:.2f} €" if error is None else f"{sym} : {error}")
                else:
                    notes.append(f"{sym} : budget insuffisant")
            elif action == "VENDRE" and holding >= 0.01:
                error = trade(sym, "VENTE", holding, "Robot virtuel")
                notes.append(f"{sym} : vente fictive {holding:.2f} €" if error is None else f"{sym} : {error}")
            else:
                notes.append(f"{sym} : {action.lower()} — aucun ordre")
        except Exception as exc:
            notes.append(f"{sym} : données indisponibles ({str(exc)[:160]})")
    st.session_state.last_cycle = notes
    st.rerun()
if "last_cycle" in st.session_state:
    for note in st.session_state.last_cycle:
        st.write("• " + note)

st.subheader("Transaction manuelle fictive")
with st.form("manual"):
    sym = st.selectbox("Cryptomonnaie", list(COINS), key="manual_coin")
    side = st.radio("Opération", ["ACHAT", "VENTE"], horizontal=True)
    amount = st.number_input("Montant (€)", min_value=1.0, value=100.0, step=10.0)
    submit = st.form_submit_button("Valider l'ordre virtuel")
if submit:
    error = trade(sym, side, amount, "Manuel")
    if error:
        st.error(error)
    else:
        st.rerun()

st.subheader("📊 Positions et risques")
rows = [{"Crypto": s, "Unités": q, "Valeur (€)": q * prices[s]["price"], "Part du portefeuille (%)": (q * prices[s]["price"] / value * 100) if value > 0 else 0} for s, q in st.session_state.positions.items()]
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
exposure = sum(r["Valeur (€)"] for r in rows)
largest = max((r["Part du portefeuille (%)"] for r in rows), default=0)
col1, col2, col3 = st.columns(3)
col1.metric("Exposition crypto", f"{exposure / value * 100:.1f} %" if value > 0 else "0 %")
col2.metric("Plus grande position", f"{largest:.1f} %")
col3.metric("Liquidités disponibles", f"{st.session_state.cash:,.2f} €")
st.caption("L'exposition et la concentration sont des indicateurs de risque, pas une estimation de perte future.")

st.subheader("Historique des transactions")
if st.session_state.trades:
    frame = pd.DataFrame(st.session_state.trades)
    st.dataframe(frame.iloc[::-1], hide_index=True, use_container_width=True)
    st.download_button("Télécharger l'historique CSV", frame.to_csv(index=False).encode("utf-8-sig"), "crypto-ai-v5-transactions.csv", "text/csv")
else:
    st.info("Aucune transaction virtuelle pour le moment.")

st.subheader("Sauvegarde du portefeuille")
backup = {"version": 5, "cash": st.session_state.cash, "positions": st.session_state.positions, "trades": st.session_state.trades}
st.download_button("💾 Sauvegarder (JSON)", json.dumps(backup, ensure_ascii=False, indent=2), "crypto-ai-v5-sauvegarde.json", "application/json")
restore = st.file_uploader("Restaurer une sauvegarde V4 ou V5 au format JSON", type="json")
if restore is not None and st.button("Restaurer ce portefeuille"):
    try:
        data = json.load(restore)
        cash = float(data["cash"])
        positions = data["positions"]
        trades = data["trades"]
        if not math.isfinite(cash) or not (0 <= cash <= 1e12) or not isinstance(positions, dict) or set(positions) != set(COINS) or not isinstance(trades, list):
            raise ValueError("Format invalide")
        positions = {s: float(positions[s]) for s in COINS}
        if any(not math.isfinite(q) or not (0 <= q <= 1e12) for q in positions.values()):
            raise ValueError("Position invalide")
        st.session_state.cash = cash
        st.session_state.positions = positions
        st.session_state.trades = trades
        st.session_state.pop("last_cycle", None)
        st.rerun()
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        st.error(f"Sauvegarde invalide : {exc}")
if st.button("Réinitialiser le portefeuille virtuel"):
    st.session_state.cash = START_CASH
    st.session_state.positions = {s: 0.0 for s in COINS}
    st.session_state.trades = []
    st.session_state.pop("last_cycle", None)
    st.rerun()
st.caption("Portefeuille en mémoire de session : sauvegarde JSON manuelle conseillée. Frais fictifs 0,1 %, sans spread, slippage ni impôts. Aucun conseil financier.")
