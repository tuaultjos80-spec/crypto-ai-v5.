# Crypto AI V5

Laboratoire pédagogique de trading de cryptomonnaies **100 % fictif**.

Fonctionnalités : cours CoinGecko indicatifs, indicateurs SMA/RSI/MACD, signaux déterministes, robot à exécution manuelle, portefeuille virtuel, exposition au risque, backtesting simplifié et sauvegardes JSON compatibles V4/V5.

## Déploiement Streamlit

Déposez `app.py`, `engine.py`, `requirements.txt` à la racine d'un dépôt GitHub. Sur Streamlit Community Cloud, choisissez le dépôt, la branche `main`, et le chemin principal `app.py`.

## Limites

- Aucune IA prédictive, aucun ordre de bourse réel.
- Backtest à clôtures quotidiennes, sans slippage, spread, fiscalité ni validation hors échantillon ; ses résultats peuvent être irréalistes.
- Les limites de l'API publique CoinGecko peuvent rendre les cours/historiques indisponibles.
- Portefeuille en session uniquement : exporter régulièrement le JSON.
