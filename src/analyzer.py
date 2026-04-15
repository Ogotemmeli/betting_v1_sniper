"""
Analyzer v1 SNIPER — Solo calcio, analisi diretta senza portfolio management.
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import (
    MIN_ARB_MARGIN_PCT, MAX_ARB_MARGIN_PCT,
    MIN_VALUE_EDGE_PCT, MAX_ODDS_VALUE_BET, MIN_ODDS_VALUE_BET,
    MIN_BOOKMAKERS, KELLY_FRACTION, MAX_STAKE_PCT,
    DEFAULT_BANKROLL, REPORTS_DIR, HISTORY_FILE
)


# ════════════════════════════════════════════════════════════════════
#  ARBITRAGGIO
# ════════════════════════════════════════════════════════════════════

def find_arbitrage(event: dict) -> dict | None:
    """Cerca opportunità di arbitraggio in un evento."""
    bookmakers = event["bookmakers"]
    if len(bookmakers) < MIN_BOOKMAKERS:
        return None

    all_outcomes = set()
    for bk in bookmakers:
        all_outcomes.update(bk["outcomes"].keys())

    if len(all_outcomes) < 2:
        return None

    # Per ogni esito, trova la quota migliore
    best_odds = {}
    for outcome in all_outcomes:
        best = None
        for bk in bookmakers:
            odd = bk["outcomes"].get(outcome)
            if odd and (best is None or odd > best["odds"]):
                best = {"odds": odd, "bookmaker": bk["title"], "key": bk["bookmaker"]}
        if best:
            best_odds[outcome] = best

    if len(best_odds) < len(all_outcomes):
        return None

    implied_sum = sum(1.0 / v["odds"] for v in best_odds.values())

    if implied_sum >= 1.0:
        return None

    margin_pct = (1.0 - implied_sum) * 100

    if margin_pct < MIN_ARB_MARGIN_PCT or margin_pct > MAX_ARB_MARGIN_PCT:
        return None

    stakes = {}
    for outcome, data in best_odds.items():
        stake_fraction = (1.0 / data["odds"]) / implied_sum
        stakes[outcome] = {
            "bookmaker": data["bookmaker"],
            "odds": data["odds"],
            "stake_pct": round(stake_fraction * 100, 2),
            "stake_amount": round(stake_fraction * DEFAULT_BANKROLL, 2)
        }

    return {
        "type": "ARBITRAGE",
        "event_id": event["id"],
        "league": event["league"],
        "match": f"{event['home_team']} vs {event['away_team']}",
        "commence": event["commence_time"],
        "market": event["market"],
        "margin_pct": round(margin_pct, 3),
        "guaranteed_profit": round(margin_pct / 100 * DEFAULT_BANKROLL, 2),
        "stakes": stakes,
        "num_bookmakers": len(bookmakers),
        "found_at": datetime.now(timezone.utc).isoformat()
    }


# ════════════════════════════════════════════════════════════════════
#  VALUE BET
# ════════════════════════════════════════════════════════════════════

def find_value_bets(event: dict) -> list[dict]:
    """Cerca value bet in un evento."""
    bookmakers = event["bookmakers"]
    if len(bookmakers) < MIN_BOOKMAKERS:
        return []

    all_outcomes = set()
    for bk in bookmakers:
        all_outcomes.update(bk["outcomes"].keys())

    # Overround medio
    total_implied_per_bk = []
    for bk in bookmakers:
        total = sum(1.0 / o for o in bk["outcomes"].values() if o > 1.0)
        if total > 0:
            total_implied_per_bk.append(total)

    if not total_implied_per_bk:
        return []

    avg_overround = sum(total_implied_per_bk) / len(total_implied_per_bk)

    value_bets = []
    for outcome in all_outcomes:
        implied_probs = []
        for bk in bookmakers:
            odd = bk["outcomes"].get(outcome)
            if odd and odd > 1.0:
                implied_probs.append(1.0 / odd)

        if len(implied_probs) < MIN_BOOKMAKERS:
            continue

        avg_implied = sum(implied_probs) / len(implied_probs)
        true_prob = avg_implied / avg_overround
        fair_odds = 1.0 / true_prob if true_prob > 0 else 999

        for bk in bookmakers:
            odd = bk["outcomes"].get(outcome)
            if not odd or odd < MIN_ODDS_VALUE_BET or odd > MAX_ODDS_VALUE_BET:
                continue

            implied_prob = 1.0 / odd
            edge = (true_prob - implied_prob) / implied_prob * 100

            if edge >= MIN_VALUE_EDGE_PCT:
                kelly_full = (true_prob * odd - 1) / (odd - 1)
                kelly_stake = max(0, kelly_full * KELLY_FRACTION)
                kelly_stake = min(kelly_stake, MAX_STAKE_PCT / 100)

                confidence = "ALTA" if edge >= 8 else ("MEDIA" if edge >= 5 else "BASSA")

                value_bets.append({
                    "type": "VALUE_BET",
                    "event_id": event["id"],
                    "league": event["league"],
                    "match": f"{event['home_team']} vs {event['away_team']}",
                    "commence": event["commence_time"],
                    "market": event["market"],
                    "outcome": outcome,
                    "bookmaker": bk["title"],
                    "odds": odd,
                    "fair_odds": round(fair_odds, 3),
                    "true_prob_pct": round(true_prob * 100, 2),
                    "implied_prob_pct": round(implied_prob * 100, 2),
                    "edge_pct": round(edge, 2),
                    "kelly_stake_pct": round(kelly_stake * 100, 2),
                    "suggested_stake": round(kelly_stake * DEFAULT_BANKROLL, 2),
                    "expected_value": round((true_prob * odd - 1) * 100, 2),
                    "confidence": confidence,
                    "found_at": datetime.now(timezone.utc).isoformat()
                })

    return value_bets


# ════════════════════════════════════════════════════════════════════
#  REPORT
# ════════════════════════════════════════════════════════════════════

def generate_report(arbitrages: list, value_bets: list, timestamp: str):
    """Genera report Markdown + CSV + summary JSON."""
    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)

    # ── Markdown ──
    report_path = os.path.join(REPORTS_DIR, "latest_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# ⚽ Report v1 Sniper — Solo Calcio\n")
        f.write(f"**Generato:** {timestamp}\n")
        f.write(f"**Bankroll:** €{DEFAULT_BANKROLL:.0f}\n\n")

        f.write("---\n## 🎯 Arbitraggi\n\n")
        if arbitrages:
            arbitrages.sort(key=lambda x: x["margin_pct"], reverse=True)
            for i, arb in enumerate(arbitrages, 1):
                f.write(f"### #{i} — {arb['match']}\n")
                f.write(f"- **Lega:** {arb['league']} | **Mercato:** {arb['market']}\n")
                f.write(f"- **Inizio:** {arb['commence']}\n")
                f.write(f"- **Margine:** {arb['margin_pct']:.2f}% "
                        f"(€{arb['guaranteed_profit']:.2f})\n\n")
                f.write("| Esito | Bookmaker | Quota | Stake % | Stake € |\n")
                f.write("|-------|-----------|-------|---------|---------|\n")
                for outcome, data in arb["stakes"].items():
                    f.write(f"| {outcome} | {data['bookmaker']} | "
                            f"{data['odds']:.2f} | {data['stake_pct']:.1f}% | "
                            f"€{data['stake_amount']:.2f} |\n")
                f.write("\n")
        else:
            f.write("_Nessun arbitraggio trovato in questo ciclo._\n\n")

        f.write("---\n## 📈 Value Bet\n\n")
        if value_bets:
            value_bets.sort(key=lambda x: x["edge_pct"], reverse=True)
            f.write("| # | Match | Esito | Book | Quota | Fair | Edge% | Conf | Stake |\n")
            f.write("|---|-------|-------|------|-------|------|-------|------|-------|\n")
            conf_emoji = {"ALTA": "🟢", "MEDIA": "🟡", "BASSA": "🔴"}
            for i, vb in enumerate(value_bets[:30], 1):
                f.write(
                    f"| {i} | {vb['match'][:28]} | {vb['outcome'][:15]} | "
                    f"{vb['bookmaker'][:12]} | {vb['odds']:.2f} | "
                    f"{vb['fair_odds']:.2f} | {vb['edge_pct']:.1f}% | "
                    f"{conf_emoji.get(vb['confidence'], '⚪')} | "
                    f"€{vb['suggested_stake']:.0f} |\n"
                )
            f.write(f"\n_Top {min(30, len(value_bets))} su {len(value_bets)}._\n\n")
        else:
            f.write("_Nessuna value bet sopra soglia._\n\n")

        f.write("---\n⚠️ Strumento di analisi. Non garantisce profitti.\n")

    print(f"📄 Report: {report_path}")

    # ── CSV storico ──
    history_rows = []
    for arb in arbitrages:
        history_rows.append({
            "timestamp": timestamp, "type": "ARBITRAGE",
            "match": arb["match"], "league": arb["league"],
            "market": arb["market"], "edge_pct": arb["margin_pct"],
            "confidence": "SURE", "suggested_stake": arb["guaranteed_profit"],
            "details": json.dumps(arb["stakes"], ensure_ascii=False)
        })
    for vb in value_bets:
        history_rows.append({
            "timestamp": timestamp, "type": "VALUE_BET",
            "match": vb["match"], "league": vb["league"],
            "market": vb["market"], "edge_pct": vb["edge_pct"],
            "confidence": vb["confidence"], "suggested_stake": vb["suggested_stake"],
            "details": f"{vb['outcome']}@{vb['odds']} ({vb['bookmaker']})"
        })

    if history_rows:
        file_exists = os.path.exists(HISTORY_FILE)
        with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as csvf:
            writer = csv.DictWriter(csvf, fieldnames=history_rows[0].keys())
            if not file_exists:
                writer.writeheader()
            writer.writerows(history_rows)
        print(f"📊 Storico: +{len(history_rows)} righe")

    # ── Summary JSON ──
    summary = {
        "timestamp": timestamp,
        "version": "v1-sniper",
        "sport": "football_only",
        "arbitrages_found": len(arbitrages),
        "value_bets_found": len(value_bets),
        "best_arb_margin": max((a["margin_pct"] for a in arbitrages), default=0),
        "best_value_edge": max((v["edge_pct"] for v in value_bets), default=0),
        "arbitrages": arbitrages[:5],
        "value_bets": [vb for vb in value_bets if vb["confidence"] in ("ALTA", "MEDIA")][:10]
    }
    with open(os.path.join(REPORTS_DIR, "latest_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


# ════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════

def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    odds_path = os.path.join(REPORTS_DIR, "latest_odds.json")
    if not os.path.exists(odds_path):
        print("❌ Nessun dato. Esegui lo scraper prima.")
        sys.exit(1)

    with open(odds_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    events = data["events"]

    print(f"\n{'='*60}")
    print(f"⚽ ANALISI v1 SNIPER — {timestamp}")
    print(f"{'='*60}")
    print(f"Record da analizzare: {len(events)}")

    all_arbs = []
    all_values = []

    for event in events:
        arb = find_arbitrage(event)
        if arb:
            all_arbs.append(arb)

        values = find_value_bets(event)
        all_values.extend(values)

    print(f"\n🎯 Arbitraggi: {len(all_arbs)}")
    print(f"📈 Value bet:  {len(all_values)}")

    if all_arbs:
        best = max(all_arbs, key=lambda x: x["margin_pct"])
        print(f"   Miglior arb: {best['margin_pct']:.2f}% — {best['match']}")
    if all_values:
        best_v = max(all_values, key=lambda x: x["edge_pct"])
        print(f"   Miglior VB:  {best_v['edge_pct']:.1f}% — {best_v['match']}")

    summary = generate_report(all_arbs, all_values, timestamp)
    print(f"\n✅ Analisi completata.")
    return summary


if __name__ == "__main__":
    main()
