"""Renders a main.run_scan() result into a single self-contained HTML
dashboard - no external requests at render time (fonts are embedded, see
dashboard/fonts.py), no JS framework, just a static report of one scan."""
import dataclasses
import html

from dashboard.fonts import FONT_FACES_CSS

def esc(s):
    return html.escape(str(s))

def _inr(n, decimals=0):
    n = float(n)
    sign = "-" if n < 0 else ""
    n = abs(n)
    return f"{sign}₹{n:,.{decimals}f}"

def _badge_class(decision):
    return {"BUY": "badge-buy", "SELL": "badge-sell", "AVOID": "badge-avoid"}.get(decision, "badge-avoid")

def _pattern_chip(pattern, bias):
    if not pattern:
        return ""
    bias_class = {"BULLISH": "chip-buy", "BEARISH": "chip-sell", "NEUTRAL": "chip-avoid"}.get(bias, "chip-avoid")
    return f'<span class="chip {bias_class}">{esc(pattern.replace("_", " "))} &middot; {esc(bias.title())}</span>'

def _reason_line(reason):
    cls = ""
    if "confirms setup" in reason:
        cls = "reason-confirm"
    elif "conflicts with setup" in reason or "Conflicting evidence" in reason:
        cls = "reason-conflict"
    return f'<li class="{cls}">{esc(reason)}</li>'

def _order_status_html(o):
    if o["allowed"]:
        order = o["order"] or {}
        order_id = order.get("order_id", "?")
        qty = order.get("quantity", o["quantity"])
        price = order.get("price", 0)
        return (
            f'<div class="status-stripe status-placed"><span class="status-dot"></span>'
            f'PAPER ORDER PLACED &middot; {esc(order_id)} &middot; qty {esc(qty)} @ {esc(round(float(price), 2))}</div>'
        )
    reason = o["reason"] or ""
    if "WATCHLIST" in reason:
        return '<div class="status-stripe status-watch"><span class="status-dot"></span>WATCHLIST ONLY &middot; below auto-eligibility threshold</div>'
    return f'<div class="status-stripe status-blocked"><span class="status-dot"></span>ORDER BLOCKED &middot; {esc(reason)}</div>'

def _signal_card(o, mode):
    s = o["signal"]
    entry, stop, t1, t2 = s["entry"], s["stop_loss"], s["target1"], s["target2"]
    exit_plan = (
        f"Book at Target 1 ({round(t1, 2)}); trail remainder to Target 2 ({round(t2, 2)}). "
        f"Exit immediately on Stop Loss ({round(stop, 2)}) or if: {s['invalidation']}"
    )
    reasons_html = "\n".join(_reason_line(r) for r in s["reasons"])
    pattern_html = _pattern_chip(s["pattern"], s["pattern_bias"])
    risk_level = {"A+": "Low", "A": "Moderate", "B": "Elevated"}.get(s["grade"], "High")

    return f"""
      <article class="card">
        {_order_status_html(o)}
        <div class="card-head">
          <div>
            <div class="card-symbol">{esc(s['symbol'])}</div>
            <div class="card-sub">{esc(s['side'])} &middot; {esc(mode)}</div>
          </div>
          <div class="card-head-right">
            <span class="badge {_badge_class(s['decision'])}">{esc(s['decision'])}</span>
            <div class="score">{esc(s['score'])}<span class="score-max">/100</span></div>
            <div class="grade">{esc(s['grade'])}</div>
          </div>
        </div>

        {f'<div class="pattern-row">{pattern_html}</div>' if pattern_html else ''}

        <div class="price-ladder">
          <div class="price-cell">
            <div class="price-label">Entry</div>
            <div class="price-value">{esc(round(entry, 2))}</div>
          </div>
          <div class="price-cell price-stop">
            <div class="price-label">Stop Loss</div>
            <div class="price-value">{esc(round(stop, 2))}</div>
          </div>
          <div class="price-cell price-target">
            <div class="price-label">Target 1</div>
            <div class="price-value">{esc(round(t1, 2))}</div>
          </div>
          <div class="price-cell price-target">
            <div class="price-label">Target 2</div>
            <div class="price-value">{esc(round(t2, 2))}</div>
          </div>
        </div>

        <div class="meta-row">
          <div><span class="meta-label">Risk/Reward</span><span class="meta-value">1:{esc(s['risk_reward'])}</span></div>
          <div><span class="meta-label">Position Size</span><span class="meta-value">{esc(o['quantity'])}</span></div>
          <div><span class="meta-label">Risk Level</span><span class="meta-value">{esc(risk_level)}</span></div>
        </div>

        <div class="exit-plan"><span class="section-label">Exit Plan</span><p>{esc(exit_plan)}</p></div>

        <div class="reasons"><span class="section-label">Reason</span>
          <ul>{reasons_html}</ul>
        </div>

        <div class="context-row">
          <div><span class="meta-label">Market Context</span><span class="meta-value">{esc(s['market_context'])}</span></div>
          <div><span class="meta-label">Sector Context</span><span class="meta-value">{esc(s['sector_context'])}</span></div>
        </div>
        <div class="invalidation"><span class="section-label">Invalidation</span><p>{esc(s['invalidation'])}</p></div>
      </article>"""

_REGIME_CHIP_CLASS = {
    "BULLISH": "chip-buy", "BEARISH": "chip-sell", "SIDEWAYS": "chip-avoid",
    "HIGH VOLATILITY": "chip-sell", "UNCERTAIN": "chip-avoid",
}

def render_dashboard(result: dict, data_note: str = None) -> str:
    """result is exactly what main.run_scan() returns. data_note, if given,
    is shown as a banner (e.g. to disclose synthetic/demo data)."""
    orders = [
        {**o, "signal": dataclasses.asdict(o["signal"])}
        for o in result["orders"]
    ]
    summary_rows = result["summary"]
    risk = result["risk_snapshot"]
    mode = result["mode"]
    regime = result["regime"]

    if result["blocked_reason"] and not orders:
        return _render_blocked(result, data_note)

    buy_count = sum(1 for r in summary_rows if r[1] == "BUY")
    sell_count = sum(1 for r in summary_rows if r[1] == "SELL")
    avoid_count = sum(1 for r in summary_rows if r[1] == "AVOID")
    placed_count = sum(1 for o in orders if o["allowed"])
    blocked_count = sum(1 for o in orders if not o["allowed"])
    open_risk_pct = (risk["open_risk"] / risk["max_open_risk_amount"] * 100) if risk and risk["max_open_risk_amount"] else 0

    summary_table_rows = "\n".join(
        f'''        <tr>
          <td class="sym">{esc(sym)}</td>
          <td><span class="badge {_badge_class(dec)}">{esc(dec)}</span></td>
          <td class="num">{esc(score)}</td>
          <td class="pattern-cell">{esc(pat) if pat != "-" else '<span class="muted">&mdash;</span>'}</td>
        </tr>'''
        for sym, dec, score, pat in summary_rows
    )
    cards_html = "\n".join(_signal_card(o, mode) for o in orders)
    regime_class = _REGIME_CHIP_CLASS.get(regime, "chip-avoid")

    banner_html = f"""
  <div class="banner">
    <span class="banner-dot"></span>
    <span>{esc(data_note)}</span>
  </div>""" if data_note else ""

    signals_section = f"""
  <section>
    <div class="section-title"><h2>Signal Detail</h2><span class="muted">Full breakdown for every BUY/SELL candidate this scan produced</span></div>
    <div class="cards">
{cards_html}
    </div>
  </section>""" if orders else """
  <section>
    <div class="section-title"><h2>Signal Detail</h2><span class="muted">No BUY/SELL candidates cleared the watchlist floor this scan</span></div>
  </section>"""

    return f"""<title>NSE Signal Desk</title>
<style>
{FONT_FACES_CSS}
{_CSS}
</style>

<div class="wrap">
  <header>
    <div class="brand">
      <span class="brand-label">AI Trading Algorithm Agent</span>
      <h1>Scan Dashboard</h1>
    </div>
    <div class="header-meta">
      <span class="chip {regime_class}">NIFTY {esc(regime)}</span>
      <span>&middot;</span>
      <span>{esc(mode)}</span>
      <span>&middot;</span>
      <span>F&amp;O {'Enabled' if result['fo_enabled'] else 'Disabled'}</span>
      <span>&middot;</span>
      <span>Cash Equity</span>
    </div>
  </header>
{banner_html}
  <div class="stats">
    <div class="tile">
      <span class="tile-label">Signals Found</span>
      <span class="tile-value">{buy_count + sell_count}<span class="score-max"> / {len(summary_rows)} scanned</span></span>
      <span class="tile-sub">{buy_count} buy &middot; {sell_count} sell &middot; {avoid_count} avoid</span>
    </div>
    <div class="tile">
      <span class="tile-label">Orders Placed</span>
      <span class="tile-value">{placed_count}<span class="score-max"> / {len(orders)} attempted</span></span>
      <span class="tile-sub">{blocked_count} blocked by risk checks</span>
    </div>
    <div class="tile">
      <span class="tile-label">Open Risk Used</span>
      <span class="tile-value">{open_risk_pct:.1f}<span class="score-max">%</span></span>
      <div class="progress"><div class="progress-fill" style="width:{min(open_risk_pct, 100):.1f}%"></div></div>
      <span class="tile-sub num">{_inr(risk['open_risk'], 2)} of {_inr(risk['max_open_risk_amount'], 2)} cap</span>
    </div>
    <div class="tile">
      <span class="tile-label">Capital &amp; Daily P&amp;L</span>
      <span class="tile-value num">{_inr(risk['capital'])}</span>
      <span class="tile-sub">Daily P&amp;L {_inr(risk['daily_pnl'], 2)} &middot; {risk['trade_count']}/{risk['max_trades']} trades closed today</span>
    </div>
  </div>

  <section>
    <div class="section-title"><h2>Scan Summary</h2><span class="muted">All {len(summary_rows)} symbols in the universe, ranked as scanned</span></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Symbol</th><th>Decision</th><th>Score</th><th>Chart Pattern</th></tr></thead>
        <tbody>
{summary_table_rows}
        </tbody>
      </table>
    </div>
  </section>
{signals_section}
  <footer>
    <span>Deterministic risk controls (Risk Manager + Order Manager) have final authority over execution &mdash; the AI layer only explains and ranks setups it did not invent. This dashboard never guarantees profit; historical or simulated results do not predict future returns.</span>
    <span class="mono">Generated by AI Trading Algorithm Agent &middot; main.run_scan() &middot; Mode: {esc(mode)}</span>
  </footer>
</div>
"""

def _render_blocked(result: dict, data_note: str) -> str:
    banner_html = f"""
  <div class="banner">
    <span class="banner-dot"></span>
    <span>{esc(data_note)}</span>
  </div>""" if data_note else ""

    return f"""<title>NSE Signal Desk</title>
<style>
{FONT_FACES_CSS}
{_CSS}
</style>

<div class="wrap">
  <header>
    <div class="brand">
      <span class="brand-label">AI Trading Algorithm Agent</span>
      <h1>Scan Dashboard</h1>
    </div>
    <div class="header-meta">
      <span class="chip chip-avoid">{esc(result['regime'] or 'DATA UNAVAILABLE')}</span>
      <span>&middot;</span>
      <span>{esc(result['mode'])}</span>
    </div>
  </header>
{banner_html}
  <div class="banner" style="border-color: var(--sell-border); background: var(--sell-bg);">
    <span class="banner-dot" style="background: var(--sell);"></span>
    <span><b style="color: var(--sell);">NO SAFE TRADE TODAY.</b> {esc(result['blocked_reason'])}</span>
  </div>

  <footer>
    <span>Deterministic risk controls (Risk Manager + Order Manager) have final authority over execution. This dashboard never guarantees profit.</span>
  </footer>
</div>
"""

_CSS = """
:root {
  --bg: #F2F3F6;
  --surface: #FFFFFF;
  --surface-2: #F7F8FA;
  --border: #DDE1E7;
  --text: #1A2029;
  --text-muted: #5B6572;
  --accent: #A8721E;
  --accent-text: #FFFFFF;
  --buy: #1F8A5A; --buy-bg: rgba(31,138,90,0.10); --buy-border: rgba(31,138,90,0.35);
  --sell: #A8402E; --sell-bg: rgba(168,64,46,0.10); --sell-border: rgba(168,64,46,0.35);
  --watch: #A8721E; --watch-bg: rgba(168,114,30,0.10); --watch-border: rgba(168,114,30,0.35);
  --avoid: #7A8391; --avoid-bg: rgba(122,131,145,0.10); --avoid-border: rgba(122,131,145,0.30);
  --shadow: 0 1px 2px rgba(20,24,30,0.06), 0 8px 24px -12px rgba(20,24,30,0.12);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #10151B;
    --surface: #171E26;
    --surface-2: #1D2530;
    --border: #2A323D;
    --text: #E7EAEE;
    --text-muted: #8B95A3;
    --accent: #D9A441;
    --accent-text: #10151B;
    --buy: #4CB47F; --buy-bg: rgba(76,180,127,0.14); --buy-border: rgba(76,180,127,0.32);
    --sell: #D9694F; --sell-bg: rgba(217,105,79,0.14); --sell-border: rgba(217,105,79,0.32);
    --watch: #D9A441; --watch-bg: rgba(217,164,65,0.16); --watch-border: rgba(217,164,65,0.36);
    --avoid: #8B95A3; --avoid-bg: rgba(139,149,163,0.12); --avoid-border: rgba(139,149,163,0.28);
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 12px 28px -14px rgba(0,0,0,0.55);
  }
}

:root[data-theme="dark"] {
  --bg: #10151B;
  --surface: #171E26;
  --surface-2: #1D2530;
  --border: #2A323D;
  --text: #E7EAEE;
  --text-muted: #8B95A3;
  --accent: #D9A441;
  --accent-text: #10151B;
  --buy: #4CB47F; --buy-bg: rgba(76,180,127,0.14); --buy-border: rgba(76,180,127,0.32);
  --sell: #D9694F; --sell-bg: rgba(217,105,79,0.14); --sell-border: rgba(217,105,79,0.32);
  --watch: #D9A441; --watch-bg: rgba(217,164,65,0.16); --watch-border: rgba(217,164,65,0.36);
  --avoid: #8B95A3; --avoid-bg: rgba(139,149,163,0.12); --avoid-border: rgba(139,149,163,0.28);
  --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 12px 28px -14px rgba(0,0,0,0.55);
}

* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: 'Plex Sans', ui-sans-serif, system-ui, sans-serif;
  font-size: 15px;
  line-height: 1.55;
  padding: 2.5rem 1.5rem 4rem;
}
.wrap { max-width: 1180px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.75rem; }

.mono { font-family: 'Plex Mono', ui-monospace, monospace; }
.num { font-family: 'Plex Mono', ui-monospace, monospace; font-variant-numeric: tabular-nums; }
.muted { color: var(--text-muted); }

header { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 0.75rem 1.5rem; }
.brand { display: flex; flex-direction: column; gap: 0.3rem; }
.brand-label { font-family: 'Plex Mono', monospace; font-weight: 500; font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--accent); }
h1 { margin: 0; font-family: 'Plex Mono', monospace; font-weight: 600; font-size: clamp(1.4rem, 2.4vw, 1.85rem); letter-spacing: -0.01em; text-wrap: balance; }
.header-meta { display: flex; align-items: center; gap: 0.6rem; font-family: 'Plex Mono', monospace; font-size: 0.82rem; color: var(--text-muted); flex-wrap: wrap; }

.chip {
  display: inline-flex; align-items: center; gap: 0.4em;
  padding: 0.32em 0.75em; border-radius: 999px;
  font-family: 'Plex Mono', monospace; font-weight: 600; font-size: 0.78rem;
  letter-spacing: 0.02em; border: 1px solid transparent; white-space: nowrap;
}
.chip-buy { background: var(--buy-bg); color: var(--buy); border-color: var(--buy-border); }
.chip-sell { background: var(--sell-bg); color: var(--sell); border-color: var(--sell-border); }
.chip-avoid { background: var(--avoid-bg); color: var(--avoid); border-color: var(--avoid-border); }

.badge {
  display: inline-flex; align-items: center; padding: 0.28em 0.7em; border-radius: 6px;
  font-family: 'Plex Mono', monospace; font-weight: 600; font-size: 0.74rem; letter-spacing: 0.03em;
  border: 1px solid transparent;
}
.badge-buy { background: var(--buy-bg); color: var(--buy); border-color: var(--buy-border); }
.badge-sell { background: var(--sell-bg); color: var(--sell); border-color: var(--sell-border); }
.badge-avoid { background: var(--avoid-bg); color: var(--avoid); border-color: var(--avoid-border); }

.banner {
  border: 1px solid var(--watch-border); background: var(--watch-bg); color: var(--text);
  border-radius: 10px; padding: 0.85rem 1.1rem; font-size: 0.86rem; display: flex; gap: 0.7rem; align-items: flex-start;
}
.banner-dot { width: 0.5rem; height: 0.5rem; border-radius: 999px; background: var(--watch); margin-top: 0.45em; flex: none; }
.banner b { color: var(--watch); font-family: 'Plex Mono', monospace; letter-spacing: 0.02em; }

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
.tile {
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  padding: 1.1rem 1.2rem; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 0.5rem;
}
.tile-label { font-family: 'Plex Mono', monospace; font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-muted); }
.tile-value { font-family: 'Plex Mono', monospace; font-weight: 600; font-size: 1.5rem; letter-spacing: -0.01em; }
.tile-sub { font-size: 0.8rem; color: var(--text-muted); }
.progress { height: 6px; border-radius: 999px; background: var(--surface-2); overflow: hidden; border: 1px solid var(--border); }
.progress-fill { height: 100%; background: var(--watch); }

section { display: flex; flex-direction: column; gap: 0.9rem; }
.section-title { display: flex; align-items: baseline; gap: 0.6rem; }
.section-title h2 { margin: 0; font-family: 'Plex Mono', monospace; font-weight: 600; font-size: 1rem; letter-spacing: 0.01em; }
.section-title .muted { font-size: 0.82rem; }

.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); box-shadow: var(--shadow); }
table { width: 100%; border-collapse: collapse; min-width: 560px; }
thead th {
  text-align: left; font-family: 'Plex Mono', monospace; font-weight: 500; font-size: 0.7rem;
  letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-muted);
  padding: 0.8rem 1.1rem; border-bottom: 1px solid var(--border); background: var(--surface-2);
}
tbody td { padding: 0.7rem 1.1rem; border-bottom: 1px solid var(--border); font-size: 0.88rem; vertical-align: middle; }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: var(--surface-2); }
td.sym { font-family: 'Plex Mono', monospace; font-weight: 600; }
td.pattern-cell { font-size: 0.82rem; color: var(--text-muted); }

.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1.1rem; }
.card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
  box-shadow: var(--shadow); overflow: hidden; display: flex; flex-direction: column;
}
.status-stripe {
  padding: 0.55rem 1.2rem; font-family: 'Plex Mono', monospace; font-size: 0.72rem; font-weight: 600;
  letter-spacing: 0.03em; display: flex; align-items: center; gap: 0.5rem;
}
.status-dot { width: 0.5rem; height: 0.5rem; border-radius: 999px; flex: none; }
.status-placed { background: var(--buy-bg); color: var(--buy); }
.status-placed .status-dot { background: var(--buy); }
.status-blocked { background: var(--sell-bg); color: var(--sell); }
.status-blocked .status-dot { background: var(--sell); }
.status-watch { background: var(--watch-bg); color: var(--watch); }
.status-watch .status-dot { background: var(--watch); }

.card-head { display: flex; justify-content: space-between; align-items: flex-start; padding: 1.1rem 1.2rem 0; gap: 0.75rem; }
.card-symbol { font-family: 'Plex Mono', monospace; font-weight: 600; font-size: 1.15rem; }
.card-sub { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem; }
.card-head-right { display: flex; flex-direction: column; align-items: flex-end; gap: 0.3rem; }
.score { font-family: 'Plex Mono', monospace; font-weight: 600; font-size: 1.3rem; line-height: 1; }
.score-max { font-size: 0.75rem; color: var(--text-muted); font-weight: 500; }
.grade { font-family: 'Plex Mono', monospace; font-size: 0.72rem; color: var(--text-muted); }

.pattern-row { padding: 0.7rem 1.2rem 0; }

.price-ladder { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.6rem; padding: 1rem 1.2rem; }
.price-cell { background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 0.55rem 0.6rem; }
.price-label { font-family: 'Plex Mono', monospace; font-size: 0.64rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-muted); }
.price-value { font-family: 'Plex Mono', monospace; font-weight: 600; font-size: 1rem; font-variant-numeric: tabular-nums; margin-top: 0.15rem; }
.price-stop .price-value { color: var(--sell); }
.price-target .price-value { color: var(--buy); }

.meta-row { display: flex; flex-wrap: wrap; gap: 1.2rem; padding: 0 1.2rem 0.9rem; }
.meta-label { display: block; font-family: 'Plex Mono', monospace; font-size: 0.64rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-muted); }
.meta-value { display: block; font-family: 'Plex Mono', monospace; font-weight: 600; font-size: 0.85rem; margin-top: 0.15rem; }

.section-label { display: block; font-family: 'Plex Mono', monospace; font-size: 0.64rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.35rem; }
.exit-plan { padding: 0 1.2rem 0.9rem; }
.exit-plan p { margin: 0; font-size: 0.85rem; color: var(--text); max-width: 62ch; }

.reasons { padding: 0 1.2rem 0.9rem; border-top: 1px solid var(--border); padding-top: 0.9rem; }
.reasons ul { margin: 0; padding-left: 1.1rem; display: flex; flex-direction: column; gap: 0.3rem; }
.reasons li { font-size: 0.83rem; }
.reason-confirm { color: var(--buy); }
.reason-conflict { color: var(--sell); }

.context-row { display: flex; flex-wrap: wrap; gap: 1.2rem; padding: 0 1.2rem 0.9rem; border-top: 1px solid var(--border); padding-top: 0.9rem; }
.invalidation { padding: 0 1.2rem 1.1rem; }
.invalidation p { margin: 0; font-size: 0.83rem; color: var(--text-muted); max-width: 62ch; }

footer { border-top: 1px solid var(--border); padding-top: 1.25rem; font-size: 0.78rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 0.4rem; }
footer .mono { color: var(--text-muted); }

@media (max-width: 520px) {
  .price-ladder { grid-template-columns: repeat(2, 1fr); }
  body { padding: 1.75rem 1rem 3rem; }
}
"""
