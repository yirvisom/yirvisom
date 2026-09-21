#!/usr/bin/env python3
"""render_banner.py — régénère assets/banner.svg avec de vraies données MASI.

Source : scanner public TradingView (région CSEMA, Bourse de Casablanca) —
la même source que le snapshot marché de deyirviel.com. Données indicatives,
possiblement différées : la bannière affiche l'horodatage « as of ».

En cas d'échec réseau/parse, le fichier existant n'est PAS touché (le profil
garde la dernière bannière connue).

Usage :
  python3 scripts/render_banner.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "banner.svg"

SCAN_URL = "https://scanner.tradingview.com/global/scan"
TZ = ZoneInfo("Africa/Casablanca")
TIMEOUT = 30

# Blue chips affichées dans le bandeau (dans l'ordre, on garde celles présentes).
TAPE = ["ATW", "IAM", "BCP", "TMA", "BOA", "CIH", "MSA", "ADH", "AKT", "SID", "LHM", "TQM", "CMG"]

UP, DOWN, FLAT = "#34D399", "#F87171", "#94A3B8"

# Motif de chandeliers (13 bougies, tendance haussière de référence).
CANDLES = [
    (150, 232, 168, 216, True), (140, 220, 158, 196, True), (148, 210, 156, 188, True),
    (130, 200, 150, 186, True), (128, 198, 138, 182, False), (120, 190, 132, 176, True),
    (118, 186, 128, 170, True), (108, 180, 122, 166, False), (100, 172, 116, 158, True),
    (96, 166, 108, 152, True), (92, 160, 104, 146, True), (84, 152, 98, 140, False),
    (76, 148, 88, 134, True),
]
TREND_Y = [192, 177, 172, 168, 160, 154, 149, 144, 139, 133, 127, 121, 114]


def fetch(tickers: list[str] | None, filt: list[dict] | None, columns: list[str]) -> list[dict]:
    payload = {
        "symbols": {"tickers": tickers or [], "query": {"types": []}},
        "columns": columns,
        "sort": {"sortBy": "name", "sortOrder": "asc"},
        "range": [0, 300],
    }
    if filt:
        payload["filter"] = filt
    req = urllib.request.Request(
        SCAN_URL, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (profile banner)"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace")).get("data") or []


def color(pct: float) -> str:
    return UP if pct > 0.0001 else (DOWN if pct < -0.0001 else FLAT)


def arrow(pct: float) -> str:
    return "▲" if pct > 0.0001 else ("▼" if pct < -0.0001 else "■")


def fmt_price(v: float) -> str:
    return f"{v:,.2f}"


def fmt_change(pct: float) -> str:
    return f"{'+' if pct >= 0 else ''}{pct:.2f}%"


def chart(up: bool) -> tuple[str, str, str, float, float]:
    xs = [492 + i * 36 for i in range(13)] if up else [924 - i * 36 for i in range(13)]
    trend = list(zip(xs, TREND_Y)) if up else list(zip(xs, TREND_Y))
    poly_trend = " ".join(f"{x},{y}" for x, y in trend)
    poly_area = poly_trend + f" {trend[-1][0]},238 {trend[0][0]},238"

    candles = []
    for (wt, wb, bt, bb, green), x in zip(CANDLES, xs):
        c = UP if green else DOWN
        candles.append(
            f'<line x1="{x}" y1="{wt}" x2="{x}" y2="{wb}" stroke="{c}"/>'
            f'<rect x="{x - 5}" y="{bt}" width="10" height="{bb - bt}" fill="{c}" stroke="none"/>'
        )
    return poly_trend, poly_area, "".join(candles), trend[-1][0], trend[-1][1]


def tape_text(stocks: list[dict]) -> str:
    parts = []
    for s in stocks:
        c = color(s["pct"])
        parts.append(
            f'<tspan fill="{c}">{s["symbol"]}</tspan>'
            f'<tspan fill="#94A3B8"> {s["price"]} </tspan>'
            f'<tspan fill="{c}">{s["change"]}</tspan>'
            f'<tspan fill="#64748B">  ·  </tspan>'
        )
    return "".join(parts)


def render(masi: dict, stocks: list[dict], as_of: str, marker: str) -> str:
    up = masi["pct"] >= 0
    dc = color(masi["pct"])
    poly_trend, poly_area, candles, end_x, end_y = chart(up)
    tape = tape_text(stocks)

    return f'''<!-- data: {marker} -->
<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="300" viewBox="0 0 1000 300" role="img" aria-label="Yirviel Somé — Financial Markets Analyst, Casablanca">
  <defs>
    <linearGradient id="panel" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0B1220"/><stop offset="1" stop-color="#070B14"/>
    </linearGradient>
    <linearGradient id="glow" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0F172A"/><stop offset="1" stop-color="#0B1220"/>
    </linearGradient>
    <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{dc}" stop-opacity="0.30"/><stop offset="1" stop-color="{dc}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#E0B252"/><stop offset="0.55" stop-color="#E0B252" stop-opacity="0.25"/><stop offset="1" stop-color="#E0B252" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="cardClip"><rect x="0" y="0" width="1000" height="300" rx="18"/></clipPath>
    <clipPath id="chartClip"><rect x="470" y="70" width="500" height="168"/></clipPath>
    <clipPath id="tapeClip"><rect x="0" y="252" width="1000" height="48"/></clipPath>
  </defs>

  <style>
    .mono{{font-family:ui-monospace,'SFMono-Regular',Menlo,Consolas,'Liberation Mono',monospace;}}
    .sans{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;}}
    .ink{{fill:#E6EDF3}}.muted{{fill:#94A3B8}}.dim{{fill:#64748B}}
    .mint{{fill:#34D399}}.gold{{fill:#E0B252}}.cyan{{fill:#38BDF8}}.red{{fill:#F87171}}
    @keyframes tickerScroll{{from{{transform:translateX(0)}}to{{transform:translateX(-1000px)}}}}
    .tape{{animation:tickerScroll 34s linear infinite}}
    @keyframes livePulse{{0%,100%{{opacity:1}}50%{{opacity:.15}}}}
    .live{{animation:livePulse 1.7s ease-in-out infinite}}
    @keyframes drawLine{{from{{stroke-dashoffset:1}}to{{stroke-dashoffset:0}}}}
    .trend{{stroke-dasharray:1;stroke-dashoffset:1;animation:drawLine 2.6s .35s ease-out forwards}}
    @media (prefers-reduced-motion: reduce){{.tape,.live,.trend{{animation:none}}.trend{{stroke-dashoffset:0}}}}
  </style>

  <g clip-path="url(#cardClip)">
    <rect width="1000" height="300" fill="url(#panel)"/>
    <rect x="0.75" y="0.75" width="998.5" height="298.5" rx="18" fill="none" stroke="#1E293B" stroke-width="1.5"/>

    <g opacity="0.35">
      <line x1="0" y1="90" x2="1000" y2="90" stroke="#0F172A"/>
      <line x1="0" y1="140" x2="1000" y2="140" stroke="#0F172A"/>
      <line x1="0" y1="190" x2="1000" y2="190" stroke="#0F172A"/>
    </g>

    <circle cx="26" cy="21" r="5.5" fill="#F87171"/>
    <circle cx="46" cy="21" r="5.5" fill="#E0B252"/>
    <circle cx="66" cy="21" r="5.5" fill="#34D399"/>
    <text x="500" y="26" text-anchor="middle" class="mono dim" font-size="13">yirvisom@casablanca — ~/markets</text>
    <text x="974" y="26" text-anchor="end" class="mono dim" font-size="12">{as_of}</text>
    <line x1="0" y1="42" x2="1000" y2="42" stroke="#1E293B"/>

    <text x="42" y="94" class="mono mint" font-size="13" letter-spacing="3.4">FINANCIAL MARKETS ANALYST</text>
    <text x="40" y="142" class="sans ink" font-size="44" font-weight="800" letter-spacing="-0.5">Yirviel Somé</text>
    <rect x="42" y="158" width="150" height="3" rx="1.5" fill="url(#rule)"/>
    <text x="42" y="188" class="mono muted" font-size="13.5">FMVA® · BIDA® · Casablanca · TZ=Africa/Casablanca</text>

    <g class="mono" font-size="12">
      <rect x="42" y="206" width="86" height="26" rx="13" fill="#0F172A" stroke="#334155"/>
      <text x="85" y="223" text-anchor="middle" class="muted">Equity</text>
      <rect x="136" y="206" width="118" height="26" rx="13" fill="#0F172A" stroke="#334155"/>
      <text x="195" y="223" text-anchor="middle" class="muted">Market Risk</text>
      <rect x="262" y="206" width="112" height="26" rx="13" fill="#0F172A" stroke="#334155"/>
      <text x="318" y="223" text-anchor="middle" class="muted">Data Eng.</text>
    </g>

    <g clip-path="url(#chartClip)">
      <g opacity="0.55">
        <line x1="470" y1="90" x2="970" y2="90" stroke="#16233A" stroke-width="0.8"/>
        <line x1="470" y1="132" x2="970" y2="132" stroke="#16233A" stroke-width="0.8"/>
        <line x1="470" y1="174" x2="970" y2="174" stroke="#16233A" stroke-width="0.8"/>
        <line x1="470" y1="216" x2="970" y2="216" stroke="#16233A" stroke-width="0.8"/>
      </g>
      <polygon fill="url(#area)" points="{poly_area}"/>
      <polyline class="trend" pathLength="1" fill="none" stroke="{dc}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" points="{poly_trend}"/>
      <g stroke-width="1.4">{candles}</g>
      <circle cx="{end_x}" cy="{end_y}" r="3.6" fill="{dc}"/>
      <line x1="{end_x}" y1="{end_y - 35}" x2="{end_x}" y2="238" stroke="{dc}" stroke-width="1" stroke-dasharray="3 4" opacity="0.6"/>
    </g>

    <text x="470" y="64" class="mono muted" font-size="12">MASI · Bourse de Casablanca</text>
    <text x="947" y="64" text-anchor="end" class="mono" fill="{dc}" font-size="12" font-weight="bold">{masi["price"]}  {arrow(masi["pct"])} {masi["change"]}</text>
    <circle class="live" cx="963" cy="60" r="3.6" fill="{dc}"/>

    <line x1="0" y1="252" x2="1000" y2="252" stroke="#1E293B"/>
    <rect x="0" y="252" width="1000" height="48" fill="url(#glow)"/>
    <g clip-path="url(#tapeClip)">
      <g class="tape mono" font-size="13.5">
        <text x="24" y="282">{tape}</text>
        <text x="1024" y="282">{tape}</text>
      </g>
    </g>
  </g>
</svg>
'''


def main() -> int:
    try:
        columns = ["name", "description", "close", "change", "change_abs", "sector", "market_cap_basic"]
        rows = fetch(None, [{"left": "exchange", "operation": "equal", "right": "CSEMA"}], columns)
        by_symbol = {r["s"].split(":", 1)[-1]: r for r in rows}
        masi_raw = next((r for r in fetch(["CSEMA:MASI"], None, columns) if r["s"] == "CSEMA:MASI"), None)
        if masi_raw is None:
            raise RuntimeError("MASI introuvable dans la réponse TradingView")
        d = masi_raw["d"]
        masi = {"price": fmt_price(float(d[2])), "change": fmt_change(float(d[3])), "pct": float(d[3])}
        stocks = []
        for sym in TAPE:
            r = by_symbol.get(sym)
            if not r:
                continue
            sd = r["d"]
            stocks.append({
                "symbol": sym,
                "price": fmt_price(float(sd[2])),
                "change": fmt_change(float(sd[3])),
                "pct": float(sd[3]),
            })
            if len(stocks) == 8:
                break
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, RuntimeError) as exc:
        sys.stderr.write(f"! banner non régénérée ({exc}) — le fichier existant est conservé\n")
        return 0

    as_of = datetime.now(TZ).strftime("%d %b · %H:%M")
    marker = "MASI=" + masi["price"] + "," + masi["change"] + ";" + ";".join(
        f'{s["symbol"]}={s["price"]},{s["change"]}' for s in stocks
    )
    if OUT.exists() and f"<!-- data: {marker} -->" in OUT.read_text(encoding="utf-8"):
        print("✓ marché inchangé — bannière conservée")
        return 0

    OUT.write_text(render(masi, stocks, as_of, marker), encoding="utf-8")
    print(f"✓ {OUT.relative_to(ROOT)} — MASI {masi['price']} {masi['change']} · {len(stocks)} valeurs · as of {as_of}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
