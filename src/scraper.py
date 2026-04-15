"""
Scraper v1 SNIPER — Solo quote calcio.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import (
    ODDS_API_KEY, ODDS_API_BASE, FOOTBALL_LEAGUES,
    REGIONS, MARKETS, ODDS_FORMAT, REPORTS_DIR
)


def fetch_odds_for_league(sport_key: str) -> list[dict] | None:
    """Recupera le quote per un campionato (tutti i mercati in una chiamata)."""
    url = f"{ODDS_API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": ",".join(REGIONS),
        "markets": ",".join(MARKETS),
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": "iso",
    }

    try:
        resp = requests.get(url, params=params, timeout=30)

        remaining = resp.headers.get("x-requests-remaining", "?")
        used = resp.headers.get("x-requests-used", "?")
        print(f"    API: {used} usate, {remaining} rimanenti")

        if resp.status_code == 401:
            print("❌ API key non valida. Configura ODDS_API_KEY nei secrets.")
            sys.exit(1)
        if resp.status_code == 429:
            print("⚠️  Rate limit. Attendo 60s...")
            time.sleep(60)
            return fetch_odds_for_league(sport_key)
        if resp.status_code == 404:
            print("    ⏸️  Lega non attiva, skip")
            return None

        resp.raise_for_status()
        data = resp.json()
        return data if data else None

    except requests.RequestException as e:
        print(f"    ⚠️  Errore: {e}")
        return None


def normalize_events(raw_events: list[dict]) -> list[dict]:
    """Normalizza gli eventi grezzi, separando per mercato."""
    normalized = []

    for event in raw_events:
        for market in MARKETS:
            bookmakers_data = []

            for bk in event.get("bookmakers", []):
                for mkt in bk.get("markets", []):
                    if mkt["key"] != market:
                        continue

                    outcomes = {}
                    for outcome in mkt["outcomes"]:
                        label = outcome["name"]
                        if market == "totals":
                            label = f"{outcome['name']} {outcome.get('point', '')}"
                        elif market == "spreads":
                            label = f"{outcome['name']} ({outcome.get('point', '')})"
                        outcomes[label] = outcome["price"]

                    bookmakers_data.append({
                        "bookmaker": bk["key"],
                        "title": bk["title"],
                        "last_update": bk.get("last_update", ""),
                        "outcomes": outcomes,
                    })

            if bookmakers_data:
                normalized.append({
                    "id": event["id"],
                    "sport": event["sport_key"],
                    "league": event.get("sport_title", event["sport_key"]),
                    "home_team": event["home_team"],
                    "away_team": event["away_team"],
                    "commence_time": event["commence_time"],
                    "market": market,
                    "bookmakers": bookmakers_data,
                })

    return normalized


def scrape_all() -> list[dict]:
    """Scraping di tutti i campionati calcio."""
    all_events = []
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")

    print("=" * 60)
    print(f"⚽ SCRAPING CALCIO v1 SNIPER — {timestamp}")
    print("=" * 60)
    print(f"Leghe: {len(FOOTBALL_LEAGUES)}")
    print(f"Mercati per lega: {', '.join(MARKETS)}")
    print(f"Chiamate API stimate: {len(FOOTBALL_LEAGUES)}")
    print()

    for league in FOOTBALL_LEAGUES:
        print(f"  ⚽ {league}")
        raw = fetch_odds_for_league(league)

        if not raw:
            continue

        events = normalize_events(raw)
        all_events.extend(events)
        print(f"    ✅ {len(raw)} eventi → {len(events)} record")
        time.sleep(0.5)

    # Salva
    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    raw_path = os.path.join(REPORTS_DIR, "latest_odds.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "version": "v1-sniper",
            "sport": "football_only",
            "total_events": len(all_events),
            "events": all_events
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📁 Salvati {len(all_events)} record in {raw_path}")
    return all_events


if __name__ == "__main__":
    if not ODDS_API_KEY:
        print("❌ ODDS_API_KEY non configurata!")
        print("   → https://the-odds-api.com/")
        sys.exit(1)

    scrape_all()
