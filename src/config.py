"""
Configurazione v1 SNIPER — Solo calcio, 3 mercati.
"""

import os

# ─── API ────────────────────────────────────────────────────────────
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# ─── Sport e Leghe (SOLO CALCIO) ───────────────────────────────────
FOOTBALL_LEAGUES = [
    "soccer_epl",               # Premier League
    "soccer_italy_serie_a",     # Serie A
    "soccer_spain_la_liga",     # La Liga
    "soccer_germany_bundesliga",# Bundesliga
    "soccer_france_ligue_one",  # Ligue 1
    "soccer_uefa_champs_league",# Champions League
    "soccer_uefa_europa_league",# Europa League
]

# ─── Bookmaker ──────────────────────────────────────────────────────
REGIONS = ["eu", "uk"]
MARKETS = ["h2h", "totals", "spreads"]  # 1X2, Over/Under, Handicap
ODDS_FORMAT = "decimal"

# ─── Soglie Arbitraggio ────────────────────────────────────────────
MIN_ARB_MARGIN_PCT = float(os.getenv("MIN_ARB_MARGIN", "0.5"))
MAX_ARB_MARGIN_PCT = 15.0

# ─── Soglie Value Bet ──────────────────────────────────────────────
MIN_VALUE_EDGE_PCT = 3.0
MAX_ODDS_VALUE_BET = 5.0
MIN_ODDS_VALUE_BET = 1.30
MIN_BOOKMAKERS = 4

# ─── Kelly Criterion ───────────────────────────────────────────────
KELLY_FRACTION = 0.25
MAX_STAKE_PCT = 5.0
DEFAULT_BANKROLL = float(os.getenv("BANKROLL", "1000.0"))

# ─── Output ─────────────────────────────────────────────────────────
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
HISTORY_FILE = os.path.join(REPORTS_DIR, "history.csv")

# ─── Telegram ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
