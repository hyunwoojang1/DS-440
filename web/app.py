"""MHIDSS Web Application."""

from __future__ import annotations

import os
import re
import sys
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

# Add project root to sys.path so engine/config/data modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from engine.entry_score import EntryScoreEngine
from engine.horizons.base import HorizonResult, classify_signal
from config.settings import WRDS_USERNAME, WRDS_PASSWORD

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"])
_engine: EntryScoreEngine | None = None


def _ensure_wrds_auth() -> None:
    """Authenticate WRDS at startup using credentials from .env."""
    if not WRDS_USERNAME:
        return

    import builtins
    import getpass as gp_mod

    orig_input   = builtins.input
    orig_getpass = gp_mod.getpass

    def _auto_input(prompt: str = "") -> str:
        if "y/n" in prompt:
            print(prompt + "y", flush=True)
            return "y"
        print(f"{prompt}{WRDS_USERNAME}", flush=True)
        return WRDS_USERNAME

    def _auto_password(prompt: str = "", stream=None) -> str:
        print(prompt, flush=True)
        return WRDS_PASSWORD

    # Bypass stale pgpass only when we have a fresh password to send.
    # Without bypass: libpq uses saved pgpass token (works if not yet expired).
    # With bypass + WRDS_PASSWORD: libpq sends the real password → server PAM triggers Duo.
    prev_pgpassfile = None
    if WRDS_PASSWORD:
        prev_pgpassfile = os.environ.pop("PGPASSFILE", None)
        os.environ["PGPASSFILE"] = os.path.join(os.environ.get("TEMP", "C:\\"), "nonexistent_pgpass")

    builtins.input   = _auto_input
    gp_mod.getpass   = _auto_password
    try:
        import wrds
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeout
        if WRDS_PASSWORD:
            print(f"[WRDS] Connecting as {WRDS_USERNAME} — approve Duo push on your phone...", flush=True)
        else:
            print(f"[WRDS] Connecting as {WRDS_USERNAME} using saved credentials...", flush=True)
        ex = ThreadPoolExecutor(max_workers=1)
        fut = ex.submit(wrds.Connection, wrds_username=WRDS_USERNAME)
        try:
            fut.result(timeout=5)
            print("[WRDS] Connected! Fundamental scores enabled.", flush=True)
        except FutTimeout:
            print("[WRDS] Connection timed out (5s). Fundamental scores will be 0.", flush=True)
        except Exception as e:
            print(f"[WRDS] Connection failed: {e}. Fundamental scores will be 0.", flush=True)
        finally:
            ex.shutdown(wait=False)
    finally:
        builtins.input   = orig_input
        gp_mod.getpass   = orig_getpass
        if WRDS_PASSWORD:
            os.environ.pop("PGPASSFILE", None)
            if prev_pgpassfile is not None:
                os.environ["PGPASSFILE"] = prev_pgpassfile


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
@limiter.limit("10 per minute")
def api_analyze():
    data = request.get_json(silent=True) or {}
    query = (data.get("ticker") or "").strip()
    as_of = data.get("date") or date.today().isoformat()

    if not query:
        return jsonify({"error": "Ticker is required"}), 400

    if not re.match(r'^[A-Za-z0-9]{1,10}$', query):
        return jsonify({"error": "Invalid ticker: letters and numbers only, max 10 characters"}), 400

    try:
        as_of_date = date.fromisoformat(as_of)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if as_of_date > date.today():
        return jsonify({"error": "Date cannot be in the future"}), 400

    try:
        result = _run_analysis(query, as_of)
        return jsonify(result)
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


@app.route("/api/compare", methods=["POST"])
@limiter.limit("10 per minute")
def api_compare():
    data = request.get_json(silent=True) or {}
    query_a = (data.get("ticker_a") or "").strip()
    query_b = (data.get("ticker_b") or "").strip()
    as_of = data.get("date") or date.today().isoformat()

    if not query_a or not query_b:
        return jsonify({"error": "Both tickers are required"}), 400

    for q in (query_a, query_b):
        if not re.match(r'^[A-Za-z0-9]{1,10}$', q):
            return jsonify({"error": f"Invalid ticker '{q}': letters and numbers only, max 10 characters"}), 400

    try:
        as_of_date = date.fromisoformat(as_of)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if as_of_date > date.today():
        return jsonify({"error": "Date cannot be in the future"}), 400

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_a = executor.submit(_run_analysis, query_a, as_of)
            fut_b = executor.submit(_run_analysis, query_b, as_of)
            result_a = fut_a.result()
            result_b = fut_b.result()
        return jsonify({"ticker_a": result_a, "ticker_b": result_b})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    import threading
    import webbrowser
    # WERKZEUG_RUN_MAIN is set only in the child (actual server) process.
    # Without this guard, debug mode's reloader runs __main__ twice → browser opens twice.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=_ensure_wrds_auth, daemon=True).start()
        threading.Timer(1.0, lambda: webbrowser.open("http://localhost:5000")).start()
    app.run(debug=True, port=5000)
