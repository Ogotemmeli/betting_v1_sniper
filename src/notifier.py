"""
Notifiche Telegram v1 SNIPER — Solo calcio.
"""

import json
import os
import sys

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, REPORTS_DIR


def send_telegram(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram non configurato, skip.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"❌ Errore Telegram: {e}")
        return False


def format_arbitrage_alert(arb: dict) -> str:
    lines = [
        f"🎯 <b>[v1 SNIPER] ARBITRAGGIO</b>",
        f"",
        f"⚽ <b>{arb['match']}</b>",
        f"🏆 {arb['league']} — {arb['market']}",
        f"📅 {arb['commence']}",
        f"",
        f"💰 <b>Margine: {arb['margin_pct']:.2f}%</b> (€{arb['guaranteed_profit']:.2f})",
        f"",
    ]
    for outcome, data in arb["stakes"].items():
        lines.append(
            f"  • {outcome}: <b>{data['odds']:.2f}</b> su {data['bookmaker']}"
            f" → €{data['stake_amount']:.2f}"
        )
    lines.append(f"\n⏰ <i>Quote cambiano rapidamente!</i>")
    return "\n".join(lines)


def format_value_bet_alert(vb: dict) -> str:
    conf_emoji = {"ALTA": "🟢", "MEDIA": "🟡", "BASSA": "🔴"}

    return (
        f"📈 <b>[v1 SNIPER] VALUE BET</b> "
        f"{conf_emoji.get(vb['confidence'], '⚪')} {vb['confidence']}\n\n"
        f"⚽ <b>{vb['match']}</b>\n"
        f"🏆 {vb['league']} — {vb['market']}\n\n"
        f"🎲 <b>{vb['outcome']}</b>\n"
        f"📊 Quota: <b>{vb['odds']:.2f}</b> su {vb['bookmaker']}\n"
        f"📐 Fair: {vb['fair_odds']:.2f} | Edge: <b>{vb['edge_pct']:.1f}%</b>\n"
        f"💶 Stake: €{vb['suggested_stake']:.0f}\n\n"
        f"<i>EV: +{vb['expected_value']:.1f}%</i>"
    )


def format_summary(summary: dict) -> str:
    lines = [
        f"📊 <b>[v1 SNIPER] ⚽ Solo Calcio</b>",
        f"🕐 {summary['timestamp']}",
        f"",
        f"🎯 Arbitraggi: <b>{summary['arbitrages_found']}</b>",
        f"📈 Value bet: <b>{summary['value_bets_found']}</b>",
    ]
    if summary.get("best_arb_margin", 0) > 0:
        lines.append(f"💰 Miglior arb: {summary['best_arb_margin']:.2f}%")
    if summary.get("best_value_edge", 0) > 0:
        lines.append(f"📊 Miglior edge: {summary['best_value_edge']:.1f}%")

    if summary["arbitrages_found"] == 0 and summary["value_bets_found"] == 0:
        lines.append(f"\n😴 Nessuna opportunità. Prossimo ciclo tra 3 ore.")

    return "\n".join(lines)


def main():
    summary_path = os.path.join(REPORTS_DIR, "latest_summary.json")
    if not os.path.exists(summary_path):
        print("❌ Nessun summary.")
        sys.exit(0)

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    send_telegram(format_summary(summary))

    for arb in summary.get("arbitrages", []):
        send_telegram(format_arbitrage_alert(arb))

    high_conf = [vb for vb in summary.get("value_bets", [])
                 if vb.get("confidence") == "ALTA"]
    for vb in high_conf[:5]:
        send_telegram(format_value_bet_alert(vb))

    count = len(summary.get("arbitrages", [])) + len(high_conf[:5])
    print(f"📬 {count + 1} notifiche inviate")


if __name__ == "__main__":
    main()
