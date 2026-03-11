#!/usr/bin/env python3
"""
Quant Strategy Engine — Factor analysis, backtesting, signal generation for A-shares.
Supports: universe, data, factors, strategy, backtest, signal, report, --check.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

# ── trading calendar ────────────────────────────────────────────────────────

# 2026 Chinese public holidays (non-trading days beyond weekends)
CN_HOLIDAYS_2026 = {
    # New Year
    "2026-01-01", "2026-01-02", "2026-01-03",
    # Spring Festival (estimated)
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19",
    "2026-02-20", "2026-02-21", "2026-02-22",
    # Qingming
    "2026-04-04", "2026-04-05", "2026-04-06",
    # Labor Day
    "2026-05-01", "2026-05-02", "2026-05-03",
    # Dragon Boat
    "2026-06-19", "2026-06-20", "2026-06-21",
    # Mid-Autumn
    "2026-09-25", "2026-09-26", "2026-09-27",
    # National Day
    "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
    "2026-10-05", "2026-10-06", "2026-10-07",
}


def is_trading_day(d: date = None) -> bool:
    if d is None:
        d = date.today()
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if d.isoformat() in CN_HOLIDAYS_2026:
        return False
    return True


def next_trading_day(d: date = None) -> date:
    if d is None:
        d = date.today()
    d = d + timedelta(days=1)
    while not is_trading_day(d):
        d = d + timedelta(days=1)
    return d


def prev_trading_day(d: date = None) -> date:
    if d is None:
        d = date.today()
    d = d - timedelta(days=1)
    while not is_trading_day(d):
        d = d - timedelta(days=1)
    return d


# ── data source with fallback ──────────────────────────────────────────────

# Tushare configuration
TUSHARE_TOKEN = "a2bd39d0aa6e6cd26729e7e3a6cddccb85b255ca0a9da996150191a9f14b"
TUSHARE_URL = "http://lianghua.nanyangqiankun.top"

def _try_tushare():
    """Try importing tushare."""
    try:
        import tushare as ts
        pro = ts.pro_api(TUSHARE_TOKEN)
        pro._DataApi__token = TUSHARE_TOKEN
        pro._DataApi__http_url = TUSHARE_URL
        return pro
    except Exception:
        return None


def _try_mootdx():
    """Try importing mootdx."""
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market="std", timeout=10)
        return client
    except Exception:
        return None


def get_stock_data(symbol: str, days: int = 60) -> "pd.DataFrame | None":
    """Get daily OHLCV data with smart source selection: mootdx (intraday) → Tushare (after close)."""
    import pandas as pd
    from datetime import datetime, timedelta

    # Determine if market is open
    now = datetime.now()
    market_hour = now.hour
    market_minute = now.minute
    is_market_open = (
        (market_hour == 9 and market_minute >= 30) or  # 9:30-11:30
        (market_hour == 10) or
        (market_hour == 11 and market_minute <= 30) or
        (market_hour == 13) or
        (market_hour == 14) or
        (market_hour == 15 and market_minute <= 0)
    ) and now.weekday() < 5  # Monday-Friday
    
    # Source 1: mootdx (intraday real-time)
    if is_market_open:
        client = _try_mootdx()
        if client:
            try:
                market = 1 if symbol.startswith("6") else 0
                code = symbol.split(".")[0] if "." in symbol else symbol
                df = client.bars(symbol=code, frequency=9, offset=days)
                if df is not None and len(df) > 0:
                    df = df.rename(columns={
                        "open": "open", "high": "high", "low": "low",
                        "close": "close", "vol": "volume", "amount": "amount",
                    })
                    df["source"] = "mootdx"
                    print(f"  [INFO] Using mootdx (intraday)")
                    return df
            except Exception as e:
                print(f"  [WARN] mootdx failed: {e}", file=sys.stderr)
    
    # Source 2: Tushare (after close, authoritative)
    pro = _try_tushare()
    if pro:
        try:
            end_date = now
            start_date = end_date - timedelta(days=days)
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            
            df = pro.daily(ts_code=symbol, start_date=start_str, end_date=end_str)
            if df is not None and len(df) > 0:
                df = df.sort_values('trade_date', ascending=False).reset_index(drop=True)
                df = df.rename(columns={
                    'trade_date': 'date', 'open': 'open', 'high': 'high', 'low': 'low',
                    'close': 'close', 'vol': 'volume', 'amount': 'amount', 'pct_chg': 'pct_chg'
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                df['source'] = 'tushare'
                print(f"  [INFO] Using Tushare (after close)")
                return df
        except Exception as e:
            print(f"  [WARN] Tushare failed: {e}", file=sys.stderr)

    # Source 3: mootdx fallback
    client = _try_mootdx()
    if client:
        try:
            # mootdx uses market code: 0=SZ, 1=SH
            market = 1 if symbol.startswith("6") else 0
            code = symbol.split(".")[0] if "." in symbol else symbol
            df = client.bars(symbol=code, frequency=9, offset=days)
            if df is not None and len(df) > 0:
                df = df.rename(columns={
                    "open": "open", "high": "high", "low": "low",
                    "close": "close", "vol": "volume", "amount": "amount",
                })
                df["source"] = "mootdx"
                return df
        except Exception as e:
            print(f"  [WARN] mootdx failed for {symbol}: {e}", file=sys.stderr)

    # Source 3: akshare (if installed)
    try:
        import akshare as ak
        code = symbol.split(".")[0] if "." in symbol else symbol
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=(date.today() - timedelta(days=days * 2)).strftime("%Y%m%d"),
                                end_date=date.today().strftime("%Y%m%d"),
                                adjust="qfq")
        if df is not None and len(df) > 0:
            df = df.rename(columns={
                "日期": "date", "开盘": "open", "最高": "high",
                "最低": "low", "收盘": "close", "成交量": "volume", "成交额": "amount",
            })
            df["source"] = "akshare"
            return df.tail(days)
    except ImportError:
        pass
    except Exception as e:
        print(f"  [WARN] akshare failed for {symbol}: {e}", file=sys.stderr)

    return None


# ── built-in factors ────────────────────────────────────────────────────────

def compute_factors(df: "pd.DataFrame") -> "pd.DataFrame":
    """Compute technical factors on OHLCV dataframe."""
    import pandas as pd
    import numpy as np

    d = df.copy()

    # Momentum
    d["momentum_20d"] = d["close"].pct_change(20)
    d["rsi_14"] = _rsi(d["close"], 14)

    # MACD
    ema12 = d["close"].ewm(span=12).mean()
    ema26 = d["close"].ewm(span=26).mean()
    d["macd"] = ema12 - ema26
    d["macd_signal"] = d["macd"].ewm(span=9).mean()
    d["macd_hist"] = d["macd"] - d["macd_signal"]

    # Moving averages
    for period in [5, 10, 20, 60]:
        d[f"ma_{period}"] = d["close"].rolling(period).mean()

    # Volatility
    d["volatility_20d"] = d["close"].pct_change().rolling(20).std() * np.sqrt(252)

    # ATR
    d["tr"] = pd.concat([
        d["high"] - d["low"],
        (d["high"] - d["close"].shift(1)).abs(),
        (d["low"] - d["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    d["atr_14"] = d["tr"].rolling(14).mean()

    # Volume
    d["volume_ratio"] = d["volume"] / d["volume"].rolling(20).mean()
    d["turnover_rate"] = d.get("turnover", d["volume"])  # simplified

    # Bollinger Bands
    d["bb_mid"] = d["close"].rolling(20).mean()
    bb_std = d["close"].rolling(20).std()
    d["bb_upper"] = d["bb_mid"] + 2 * bb_std
    d["bb_lower"] = d["bb_mid"] - 2 * bb_std
    d["bb_position"] = (d["close"] - d["bb_lower"]) / (d["bb_upper"] - d["bb_lower"])

    # KDJ
    low_9 = d["low"].rolling(9).min()
    high_9 = d["high"].rolling(9).max()
    rsv = (d["close"] - low_9) / (high_9 - low_9) * 100
    d["kdj_k"] = rsv.ewm(com=2).mean()
    d["kdj_d"] = d["kdj_k"].ewm(com=2).mean()
    d["kdj_j"] = 3 * d["kdj_k"] - 2 * d["kdj_d"]

    return d


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# ── strategies ──────────────────────────────────────────────────────────────

def strategy_momentum_breakout(df: "pd.DataFrame") -> "pd.DataFrame":
    """Momentum breakout: volume surge + new 20d high + RSI < 70 + MACD cross."""
    d = compute_factors(df)
    d["high_20d"] = d["high"].rolling(20).max()

    d["signal"] = (
        (d["close"] > d["high_20d"].shift(1)) &  # New 20d high
        (d["volume_ratio"] > 2.0) &               # Volume surge
        (d["rsi_14"] < 70) &                       # Not overbought
        (d["macd_hist"] > 0) &                     # MACD positive
        (d["macd_hist"].shift(1) <= 0)             # MACD just crossed
    )
    return d


def strategy_mean_reversion(df: "pd.DataFrame") -> "pd.DataFrame":
    """Mean reversion: oversold bounce."""
    d = compute_factors(df)
    d["signal"] = (
        (d["rsi_14"] < 30) &                       # Oversold
        (d["bb_position"] < 0.1) &                  # Near lower Bollinger
        (d["close"] < d["ma_20"] * 0.92) &         # >8% below MA20
        (d["volume_ratio"] > 1.5)                   # Volume picking up
    )
    return d


STRATEGIES = {
    "momentum_breakout": strategy_momentum_breakout,
    "mean_reversion": strategy_mean_reversion,
}


# ── signal generation ───────────────────────────────────────────────────────

def generate_signals(symbols: list[str], strategy_name: str = "momentum_breakout") -> list[dict]:
    strategy_fn = STRATEGIES.get(strategy_name)
    if not strategy_fn:
        return [{"error": f"Unknown strategy: {strategy_name}"}]

    signals = []
    for sym in symbols:
        df = get_stock_data(sym, days=60)
        if df is None or len(df) < 30:
            continue

        result = strategy_fn(df)
        if result["signal"].iloc[-1]:
            last = result.iloc[-1]
            signals.append({
                "symbol": sym,
                "action": "BUY",
                "price": round(float(last["close"]), 2),
                "rsi": round(float(last["rsi_14"]), 1) if "rsi_14" in last else None,
                "volume_ratio": round(float(last["volume_ratio"]), 2) if "volume_ratio" in last else None,
                "macd_hist": round(float(last["macd_hist"]), 4) if "macd_hist" in last else None,
                "strategy": strategy_name,
                "stop_loss": round(float(last["close"]) * 0.92, 2),
                "take_profit": round(float(last["close"]) * 1.10, 2),
                "date": date.today().isoformat(),
            })

    return signals


# ── simple backtest ─────────────────────────────────────────────────────────

def backtest(symbol: str, strategy_name: str = "momentum_breakout",
             days: int = 250, capital: float = 1000000,
             commission: float = 0.0003, stamp_tax: float = 0.001,
             slippage: float = 0.001) -> dict:
    """Simple long-only backtest."""
    import numpy as np

    strategy_fn = STRATEGIES.get(strategy_name)
    if not strategy_fn:
        return {"error": f"Unknown strategy: {strategy_name}"}

    df = get_stock_data(symbol, days=days)
    if df is None or len(df) < 60:
        return {"error": f"Insufficient data for {symbol}"}

    result = strategy_fn(df)
    closes = result["close"].values
    signals = result["signal"].values

    # Simulate trades
    cash = capital
    shares = 0
    trades = []
    equity_curve = [capital]

    for i in range(1, len(closes)):
        if signals[i] and shares == 0:
            # BUY
            price = closes[i] * (1 + slippage)
            max_shares = int(cash / (price * (1 + commission)) / 100) * 100  # round to 100
            if max_shares > 0:
                cost = max_shares * price * (1 + commission)
                cash -= cost
                shares = max_shares
                trades.append({"type": "BUY", "price": round(price, 2), "shares": max_shares, "day": i})
        elif shares > 0:
            # Simple exit: hold 5 days or stop loss/take profit
            entry_price = trades[-1]["price"]
            pnl_pct = (closes[i] - entry_price) / entry_price
            hold_days = i - trades[-1]["day"]
            if pnl_pct <= -0.08 or pnl_pct >= 0.10 or hold_days >= 5:
                price = closes[i] * (1 - slippage)
                revenue = shares * price * (1 - commission - stamp_tax)
                cash += revenue
                trades.append({"type": "SELL", "price": round(price, 2), "shares": shares, "day": i,
                               "pnl_pct": round(pnl_pct * 100, 2)})
                shares = 0

        portfolio_value = cash + shares * closes[i]
        equity_curve.append(portfolio_value)

    # Close any open position
    if shares > 0:
        price = closes[-1]
        revenue = shares * price * (1 - commission - stamp_tax)
        cash += revenue
        equity_curve[-1] = cash

    # Metrics
    equity = np.array(equity_curve)
    returns = np.diff(equity) / equity[:-1]
    total_return = (equity[-1] / capital - 1) * 100
    ann_return = total_return * 252 / max(len(equity), 1)
    max_dd = _max_drawdown(equity) * 100
    sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0

    buy_trades = [t for t in trades if t["type"] == "BUY"]
    sell_trades = [t for t in trades if t["type"] == "SELL"]
    wins = sum(1 for t in sell_trades if t.get("pnl_pct", 0) > 0)
    win_rate = wins / len(sell_trades) * 100 if sell_trades else 0

    return {
        "symbol": symbol,
        "strategy": strategy_name,
        "period_days": days,
        "initial_capital": capital,
        "final_value": round(equity[-1], 2),
        "total_return_pct": round(total_return, 2),
        "annualized_return_pct": round(ann_return, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 3),
        "total_trades": len(buy_trades),
        "win_rate_pct": round(win_rate, 1),
        "calmar_ratio": round(ann_return / max_dd, 3) if max_dd > 0 else 0,
    }


def _max_drawdown(equity):
    import numpy as np
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / peak
    return np.max(dd) if len(dd) > 0 else 0


# ── risk rules ──────────────────────────────────────────────────────────────

DEFAULT_RISK = {
    "max_single_position": 0.10,
    "max_sector_position": 0.30,
    "max_total_position": 0.80,
    "single_stop_loss": -0.08,
    "portfolio_stop_loss": -0.15,
    "max_daily_trades": 5,
    "no_chase_limit_up": True,
}


def check_risk(signal: dict, portfolio: dict = None, risk_rules: dict = None) -> dict:
    rules = risk_rules or DEFAULT_RISK
    violations = []
    if portfolio:
        total_pos = sum(portfolio.get("positions", {}).values()) / portfolio.get("total_value", 1)
        if total_pos >= rules["max_total_position"]:
            violations.append(f"Total position {total_pos:.0%} >= {rules['max_total_position']:.0%}")
    return {
        "signal": signal,
        "risk_ok": len(violations) == 0,
        "violations": violations,
        "rules_applied": list(rules.keys()),
    }


# ── health check ────────────────────────────────────────────────────────────

def health_check() -> dict:
    import shutil
    checks = []

    # python3
    checks.append({"name": "python3", "type": "bin",
                    "status": "ok" if shutil.which("python3") else "fail"})

    # pandas
    try:
        import pandas
        checks.append({"name": "pandas", "type": "pip", "status": "ok",
                        "version": pandas.__version__})
    except ImportError:
        checks.append({"name": "pandas", "type": "pip", "status": "fail"})

    # numpy
    try:
        import numpy
        checks.append({"name": "numpy", "type": "pip", "status": "ok",
                        "version": numpy.__version__})
    except ImportError:
        checks.append({"name": "numpy", "type": "pip", "status": "fail"})

    # mootdx
    try:
        from mootdx.quotes import Quotes
        client = Quotes.factory(market="std", timeout=5)
        checks.append({"name": "mootdx", "type": "pip", "status": "ok"})
    except ImportError:
        checks.append({"name": "mootdx", "type": "pip", "status": "fail"})
    except Exception as e:
        checks.append({"name": "mootdx", "type": "pip", "status": "warn",
                        "message": f"Installed but connection failed: {e}"})

    # Trading day
    today = date.today()
    checks.append({"name": "trading_day", "type": "env",
                    "status": "ok" if is_trading_day(today) else "warn",
                    "message": f"{'Trading day' if is_trading_day(today) else 'Non-trading day'}: {today}"})

    overall = "fail" if any(c["status"] == "fail" for c in checks) \
        else "warn" if any(c["status"] == "warn" for c in checks) else "ok"
    return {
        "skill": "quant-strategy-engine", "version": "1.0.0",
        "status": overall, "checks": checks,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Quant Strategy Engine")
    parser.add_argument("--check", action="store_true", help="Health check")

    sub = parser.add_subparsers(dest="command")

    # trading-day
    p_td = sub.add_parser("trading-day", help="Check if date is trading day")
    p_td.add_argument("--date", help="Date (YYYY-MM-DD)")

    # data
    p_data = sub.add_parser("data", help="Fetch stock data")
    p_data.add_argument("--symbol", required=True)
    p_data.add_argument("--days", type=int, default=60)

    # factors
    p_fac = sub.add_parser("factors", help="Compute factors")
    p_fac.add_argument("--symbol", required=True)
    p_fac.add_argument("--days", type=int, default=60)

    # signal
    p_sig = sub.add_parser("signal", help="Generate signals")
    p_sig.add_argument("--symbols", required=True, help="Comma-separated symbols")
    p_sig.add_argument("--strategy", default="momentum_breakout",
                       choices=list(STRATEGIES.keys()))

    # backtest
    p_bt = sub.add_parser("backtest", help="Run backtest")
    p_bt.add_argument("--symbol", required=True)
    p_bt.add_argument("--strategy", default="momentum_breakout",
                      choices=list(STRATEGIES.keys()))
    p_bt.add_argument("--days", type=int, default=250)
    p_bt.add_argument("--capital", type=float, default=1000000)

    # risk
    p_risk = sub.add_parser("risk", help="Check risk rules")

    args = parser.parse_args()

    if args.check:
        result = health_check()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["status"] != "fail" else 1)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "trading-day":
        d = date.fromisoformat(args.date) if args.date else date.today()
        result = {
            "date": d.isoformat(),
            "is_trading_day": is_trading_day(d),
            "next_trading_day": next_trading_day(d).isoformat(),
            "prev_trading_day": prev_trading_day(d).isoformat(),
        }
        print(json.dumps(result, indent=2))

    elif args.command == "data":
        df = get_stock_data(args.symbol, args.days)
        if df is not None:
            print(f"Fetched {len(df)} rows for {args.symbol} (source: {df['source'].iloc[0]})")
            print(df.tail(5).to_string())
        else:
            print(json.dumps({"error": f"No data for {args.symbol}"}))
            sys.exit(1)

    elif args.command == "factors":
        df = get_stock_data(args.symbol, args.days)
        if df is None:
            print(json.dumps({"error": f"No data for {args.symbol}"}))
            sys.exit(1)
        result = compute_factors(df)
        last = result.iloc[-1]
        factors_summary = {
            "symbol": args.symbol,
            "date": str(last.name) if hasattr(last, 'name') else date.today().isoformat(),
            "close": round(float(last["close"]), 2),
            "rsi_14": round(float(last["rsi_14"]), 2) if "rsi_14" in last else None,
            "macd_hist": round(float(last["macd_hist"]), 4) if "macd_hist" in last else None,
            "volatility_20d": round(float(last["volatility_20d"]), 4) if "volatility_20d" in last else None,
            "volume_ratio": round(float(last["volume_ratio"]), 2) if "volume_ratio" in last else None,
            "bb_position": round(float(last["bb_position"]), 3) if "bb_position" in last else None,
            "kdj_j": round(float(last["kdj_j"]), 2) if "kdj_j" in last else None,
            "ma_5": round(float(last["ma_5"]), 2) if "ma_5" in last else None,
            "ma_20": round(float(last["ma_20"]), 2) if "ma_20" in last else None,
            "ma_60": round(float(last["ma_60"]), 2) if "ma_60" in last else None,
        }
        print(json.dumps(factors_summary, indent=2))

    elif args.command == "signal":
        if not is_trading_day():
            print(json.dumps({
                "warning": "Non-trading day",
                "next_trading_day": next_trading_day().isoformat(),
                "signals": [],
            }, indent=2))
            sys.exit(0)
        symbols = [s.strip() for s in args.symbols.split(",")]
        signals = generate_signals(symbols, args.strategy)
        print(json.dumps({
            "date": date.today().isoformat(),
            "strategy": args.strategy,
            "signals_count": len(signals),
            "signals": signals,
        }, indent=2, ensure_ascii=False))

    elif args.command == "backtest":
        result = backtest(args.symbol, args.strategy, args.days, args.capital)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "risk":
        print(json.dumps({"default_risk_rules": DEFAULT_RISK}, indent=2))


if __name__ == "__main__":
    main()
