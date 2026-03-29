"""MHIDSS Web Application."""

from __future__ import annotations

import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

# Add project root to sys.path so engine/config/data modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, jsonify

from engine.entry_score import EntryScoreEngine
from engine.horizons.base import HorizonResult, classify_signal

app = Flask(__name__)
_engine: EntryScoreEngine | None = None


def get_engine() -> EntryScoreEngine:
    global _engine
    if _engine is None:
        _engine = EntryScoreEngine()
    return _engine


def _resolve_ticker(query: str) -> tuple[str, str]:
    import yfinance as yf
    stripped = query.strip()
    cleaned = stripped.upper()
    if stripped == cleaned and cleaned.isalpha() and len(cleaned) <= 6:
        return cleaned, cleaned
    try:
        results = yf.Search(query, max_results=5).quotes
        for r in results:
            if r.get("quoteType") in ("EQUITY", "ETF") and "." not in r.get("symbol", ""):
                symbol = r["symbol"].upper()
                name = r.get("longname") or r.get("shortname") or symbol
                return symbol, name
    except Exception:
        pass
    return cleaned, cleaned


def _horizon_result_to_dict(r: HorizonResult) -> dict:
    sector_info = ""
    if "_sector" in r.indicator_scores:
        raw = str(r.indicator_scores["_sector"])
        sector_info = raw.split("(")[0].strip()
    return {
        "horizon": r.horizon,
        "entry_score": round(r.entry_score, 1),
        "signal": r.signal,
        "resolution": r.resolution,
        "group_scores": {k: round(v, 1) for k, v in r.group_scores.items()},
        "weight_version": r.weight_version,
        "as_of_date": r.as_of_date,
        "sector": sector_info,
    }


def _run_analysis(query: str, as_of_date: str) -> dict:
    ticker, company = _resolve_ticker(query)
    engine = get_engine()
    results = engine.run(ticker=ticker, as_of_date=as_of_date)
    return {
        "ticker": ticker,
        "company": company,
        "as_of_date": as_of_date,
        "horizons": {k: _horizon_result_to_dict(v) for k, v in results.items()},
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json(silent=True) or {}
    query = (data.get("ticker") or "").strip()
    as_of = data.get("date") or date.today().isoformat()

    if not query:
        return jsonify({"error": "Ticker is required"}), 400

    try:
        result = _run_analysis(query, as_of)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/compare", methods=["POST"])
def api_compare():
    data = request.get_json(silent=True) or {}
    query_a = (data.get("ticker_a") or "").strip()
    query_b = (data.get("ticker_b") or "").strip()
    as_of = data.get("date") or date.today().isoformat()

    if not query_a or not query_b:
        return jsonify({"error": "Both tickers are required"}), 400

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_a = executor.submit(_run_analysis, query_a, as_of)
            fut_b = executor.submit(_run_analysis, query_b, as_of)
            result_a = fut_a.result()
            result_b = fut_b.result()
        return jsonify({"ticker_a": result_a, "ticker_b": result_b})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
