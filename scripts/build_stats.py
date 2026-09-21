#!/usr/bin/env python3
"""build_stats.py — génère assets/stats.svg depuis l'API GitHub.

Aucune dépendance externe : uniquement la bibliothèque standard. Le jeton est
lu dans GITHUB_TOKEN / GH_TOKEN (injecté par GitHub Actions) ou, en local, via
`gh auth token`.

Usage :
  GITHUB_TOKEN=... python3 scripts/build_stats.py
  python3 scripts/build_stats.py            # essaie `gh auth token`
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "stats.svg"
LOGIN = "yirvisom"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, privacy: PUBLIC, ownerAffiliations: OWNER) {
      totalCount
      nodes { stargazerCount primaryLanguage { name } }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def token() -> str:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(key):
            return os.environ[key].strip()
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        sys.stderr.write("error: no GitHub token (set GITHUB_TOKEN or run `gh auth login`)\n")
        sys.exit(1)


def fetch() -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token()}",
            "Content-Type": "application/json",
            "User-Agent": "yirvisom-profile-stats",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        sys.stderr.write(f"error: GitHub API {exc.code}: {exc.read().decode(errors='replace')}\n")
        sys.exit(1)
    if "errors" in payload:
        sys.stderr.write(f"error: {payload['errors']}\n")
        sys.exit(1)
    return payload["data"]["user"]


def current_streak(days: list[dict]) -> int:
    counts = [(d["date"], d["contributionCount"]) for d in sorted(days, key=lambda x: x["date"])]
    if not counts:
        return 0
    streak = 0
    i = len(counts) - 1
    if counts[i][1] == 0:
        i -= 1
    while i >= 0 and counts[i][1] > 0:
        streak += 1
        i -= 1
    return streak


def fmt(n: int) -> str:
    return f"{n:,}"


def bars(days: list[dict], x: float, y: float, width: float, height: float, n: int = 182) -> str:
    tail = sorted(days, key=lambda d: d["date"])[-n:]
    if not tail:
        return ""
    peak = max((d["contributionCount"] for d in tail), default=1) or 1
    step = width / len(tail)
    bw = max(step - 1.6, 1.2)
    out = []
    for i, d in enumerate(tail):
        c = d["contributionCount"]
        h = 1.2 if c == 0 else max(1.2, (c / peak) * height)
        op = 0.16 if c == 0 else 0.42 + 0.58 * (c / peak)
        out.append(
            f'<rect x="{x + i * step:.2f}" y="{y + height - h:.2f}" width="{bw:.2f}" '
            f'height="{h:.2f}" rx="{bw / 2:.2f}" fill="#34D399" opacity="{op:.2f}"/>'
        )
    return "".join(out)


def metric(x: float, value: str, label: str, accent: str) -> str:
    return (
        f'<text x="{x}" y="108" class="sans" fill="#E6EDF3" font-size="38" font-weight="800">{value}</text>'
        f'<text x="{x}" y="132" class="mono" fill="{accent}" font-size="11.5" letter-spacing="1.6">{label}</text>'
    )


def render(u: dict) -> str:
    repos = u["repositories"]
    stars = sum(n.get("stargazerCount") or 0 for n in repos["nodes"])
    followers = u["followers"]["totalCount"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    contribs = cal["totalContributions"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    streak = current_streak(days)

    langs: dict[str, int] = {}
    for n in repos["nodes"]:
        lang = (n.get("primaryLanguage") or {}).get("name")
        if lang:
            langs[lang] = langs.get(lang, 0) + 1
    top = max(langs.items(), key=lambda kv: kv[1])[0] if langs else "—"

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cols = [
        (28, fmt(repos["totalCount"]), "PUBLIC REPOS", "#E0B252"),
        (218, fmt(followers), "FOLLOWERS", "#38BDF8"),
        (408, fmt(stars), "STARS EARNED", "#34D399"),
        (598, fmt(contribs), "CONTRIBUTIONS / YR", "#A78BFA"),
        (788, fmt(streak), "DAY STREAK", "#F87171"),
    ]
    metrics = "".join(metric(*c) for c in cols)
    strip = bars(days, 28, 150, 944, 24)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="190" viewBox="0 0 1000 190" role="img" aria-label="GitHub activity for {LOGIN}">
  <defs>
    <linearGradient id="sbg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#101B2E"/>
      <stop offset="1" stop-color="#0A101D"/>
    </linearGradient>
    <linearGradient id="srule" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#E0B252"/>
      <stop offset="0.4" stop-color="#E0B252" stop-opacity="0.15"/>
      <stop offset="1" stop-color="#E0B252" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <style>
    .sans{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;}}
    .mono{{font-family:ui-monospace,'SFMono-Regular',Menlo,Consolas,'Liberation Mono',monospace;}}
  </style>

  <rect x="6" y="6" width="988" height="178" rx="16" fill="url(#sbg)" stroke="#1E293B" stroke-width="1.5"/>
  <rect x="28" y="28" width="120" height="2.5" rx="1.25" fill="url(#srule)"/>

  <text x="28" y="52" class="mono" fill="#94A3B8" font-size="11.5" letter-spacing="2.2">GITHUB SIGNAL</text>
  <text x="972" y="52" text-anchor="end" class="mono" fill="#64748B" font-size="11">top language: {top} · updated {updated}</text>

  {metrics}
  {strip}
</svg>
"""


def main() -> int:
    svg = render(fetch())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"✓ {OUT.relative_to(ROOT)} written ({len(svg)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
