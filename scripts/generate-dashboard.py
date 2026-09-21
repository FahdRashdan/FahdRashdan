#!/usr/bin/env python3
"""Generate assets/dashboard.svg from public GitHub data. Standard library only."""
import json, os, re, sys, urllib.request
from datetime import date, datetime, timedelta, timezone

USER = os.environ.get("GH_USER", "FahdRashdan")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "dashboard.svg")


def get(url, api=False):
    headers = {"User-Agent": "profile-dashboard"}
    if api and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


# ---------- contributions ----------
def fetch_contributions():
    html = get(f"https://github.com/users/{USER}/contributions")
    tips = {}
    for tid, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>', html):
        m = re.match(r"(\d+) contribution", text.strip())
        tips[tid] = int(m.group(1)) if m else 0
    days = {}
    for tag in re.findall(r"<td[^>]*data-date=[^>]*>", html):
        d = re.search(r'data-date="([\d-]+)"', tag)
        i = re.search(r'id="([^"]+)"', tag)
        lv = re.search(r'data-level="(\d)"', tag)
        if d and i:
            days[date.fromisoformat(d.group(1))] = (tips.get(i.group(1), 0), int(lv.group(1)) if lv else 0)
    return days


# ---------- languages ----------
def fetch_languages():
    """Returns (repo_count, {language: weight}). Uses bytes via API when a token exists."""
    langs, repos = {}, 0
    if TOKEN:
        try:
            data = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner", api=True))
            for r in data:
                if r.get("fork"):
                    continue
                repos += 1
                for k, v in json.loads(get(r["languages_url"], api=True)).items():
                    langs[k] = langs.get(k, 0) + v
            if langs:
                return repos, langs
        except Exception as e:
            print("API fallback:", e, file=sys.stderr)
    html = get(f"https://github.com/{USER}?tab=repositories&type=source")
    repos = len(re.findall(r'itemprop="name codeRepository"', html))
    for k in re.findall(r'itemprop="programmingLanguage">([^<]+)<', html):
        langs[k.strip()] = langs.get(k.strip(), 0) + 1
    return repos, langs


LANG_COLORS = ["#58a6ff", "#a371f7", "#3fb950", "#f0883e", "#f85149", "#8b949e"]
HEAT = ["#161b22", "#0c2d6b", "#1f6feb", "#58a6ff", "#a371f7"]


def build():
    days = fetch_contributions()
    repos, langs = fetch_languages()
    today = max(days)
    first = min(days)
    start = first - timedelta(days=(first.weekday() + 1) % 7)  # align to Sunday
    total = sum(c for c, _ in days.values())

    # streaks
    cur = 0
    d = today if days[today][0] > 0 else today - timedelta(days=1)
    while d in days and days[d][0] > 0:
        cur += 1
        d -= timedelta(days=1)
    longest = run = 0
    for d in sorted(days):
        run = run + 1 if days[d][0] > 0 else 0
        longest = max(longest, run)

    weeks = (today - start).days // 7 + 1
    weekly = [0] * weeks
    for d, (c, _) in days.items():
        weekly[(d - start).days // 7] += c

    W, H = 900, 570
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Activity dashboard">')
    a("""<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#0d1117"/><stop offset="100%" stop-color="#161b22"/></linearGradient>
<linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop offset="0%" stop-color="#1f6feb"/><stop offset="100%" stop-color="#a371f7"/></linearGradient>
<style>
text{font-family:'JetBrains Mono','SFMono-Regular',Consolas,monospace}
.h{fill:#e6edf3;font-size:15px;font-weight:700;letter-spacing:2px}
.s{fill:#8b949e;font-size:11px;letter-spacing:1.5px}
.v{fill:#e6edf3;font-size:30px;font-weight:700}
.l{fill:#8b949e;font-size:12px}
.t{fill:#c9d1d9;font-size:13px}
.cell{opacity:0;animation:pop .5s ease-out forwards}
.wk{transform-box:fill-box;transform-origin:bottom center;transform:scaleY(0);animation:up 1s cubic-bezier(.2,.8,.2,1) forwards}
.pulse{animation:pulse 2.4s ease-in-out infinite}
@keyframes pop{from{opacity:0}to{opacity:1}}
@keyframes up{to{transform:scaleY(1)}}
@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
</style></defs>""")
    a(f'<rect width="{W}" height="{H}" rx="14" fill="url(#bg)" stroke="#30363d"/>')
    a('<circle class="pulse" cx="34" cy="34" r="5" fill="#3fb950"/>')
    a('<text class="h" x="50" y="40">ACTIVITY DASHBOARD</text>')
    a(f'<text class="s" x="870" y="39" text-anchor="end">UPDATED {today.isoformat()}</text>')
    a('<line x1="30" y1="56" x2="870" y2="56" stroke="#30363d"/>')

    tiles = [(f"{total}", "Contributions / year", "#58a6ff"),
             (f"{cur}", "Current streak (days)", "#a371f7"),
             (f"{longest}", "Longest streak (days)", "#3fb950"),
             (f"{repos}", "Public repositories", "#f0883e")]
    for i, (val, lab, col) in enumerate(tiles):
        x = 30 + i * 215
        a(f'<rect x="{x}" y="74" width="195" height="82" rx="10" fill="#161b22" stroke="#30363d"/>')
        a(f'<rect x="{x}" y="74" width="4" height="82" rx="2" fill="{col}"/>')
        a(f'<text class="v" x="{x+22}" y="118">{val}</text>')
        a(f'<text class="l" x="{x+22}" y="142">{lab}</text>')

    a('<text class="s" x="30" y="188">CONTRIBUTION CALENDAR</text>')
    x0, y0, step = 56, 226, 15
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        a(f'<text class="s" x="30" y="{y0 + r*step + 10}" style="font-size:9px">{name}</text>')
    labels, last_month = [], -1
    for d in sorted(days):
        col = (d - start).days // 7
        row = (d.weekday() + 1) % 7
        c, lv = days[d]
        if row == 0 and d.month != last_month:
            labels.append((col, d.strftime("%b").upper()))
            last_month = d.month
        a(f'<rect class="cell" x="{x0 + col*step}" y="{y0 + row*step}" width="12" height="12" rx="3" fill="{HEAT[lv]}" style="animation-delay:{col*0.03:.2f}s"/>')
    for i, (col, name) in enumerate(labels):
        if i + 1 < len(labels) and labels[i + 1][0] - col < 3:
            continue
        a(f'<text class="s" x="{x0 + col*step}" y="{y0-8}" style="font-size:9px">{name}</text>')
    lx = 870 - 5 * 15 - 60
    a(f'<text class="s" x="{lx-8}" y="{y0+7*step+16}" text-anchor="end" style="font-size:9px">LESS</text>')
    for i, c in enumerate(HEAT):
        a(f'<rect x="{lx + i*15}" y="{y0+7*step+7}" width="12" height="12" rx="3" fill="{c}"/>')
    a(f'<text class="s" x="{lx+5*15+4}" y="{y0+7*step+16}" style="font-size:9px">MORE</text>')

    a('<line x1="30" y1="372" x2="870" y2="372" stroke="#30363d"/>')
    a(f'<text class="s" x="30" y="398">LANGUAGES ({"BY CODE SIZE" if TOKEN else "BY REPOSITORY"})</text>')
    a('<text class="s" x="360" y="398">WEEKLY CONTRIBUTIONS</text>')

    # donut
    total_w = sum(langs.values()) or 1
    items = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    cx, cy, r = 100, 480, 48
    C = 2 * 3.14159265 * r
    a(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#21262d" stroke-width="16"/>')
    off, unit = 0.0, "repos" if not TOKEN else "code"
    for i, (name, w) in enumerate(items):
        seg = C * w / total_w
        col = LANG_COLORS[i % len(LANG_COLORS)]
        a(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="16" stroke-dasharray="0 {C:.2f}" stroke-dashoffset="{-off:.2f}" transform="rotate(-90 {cx} {cy})">'
          f'<animate attributeName="stroke-dasharray" from="0 {C:.2f}" to="{max(seg-2,0.5):.2f} {C:.2f}" dur="1s" begin="{i*0.25:.2f}s" fill="freeze"/></circle>')
        off += seg
    a(f'<text x="{cx}" y="{cy+5}" text-anchor="middle" class="t" style="font-weight:700">{len(langs)}</text>')
    a(f'<text x="{cx}" y="{cy+19}" text-anchor="middle" class="s" style="font-size:9px">LANGS</text>')
    for i, (name, w) in enumerate(items):
        y = 440 + i * 24
        col = LANG_COLORS[i % len(LANG_COLORS)]
        a(f'<rect x="185" y="{y-10}" width="12" height="12" rx="3" fill="{col}"/>')
        a(f'<text class="t" x="206" y="{y}">{name}</text>')
        a(f'<text class="l" x="330" y="{y}" text-anchor="end">{round(100*w/total_w)}%</text>')

    # weekly bars
    bx, by, bh = 360, 540, 110
    mx = max(weekly) or 1
    bw = 510 / weeks
    a(f'<line x1="{bx}" y1="{by}" x2="870" y2="{by}" stroke="#30363d"/>')
    for i, v in enumerate(weekly):
        h = max(2, v / mx * bh)
        a(f'<rect class="wk" x="{bx + i*bw:.1f}" y="{by-h:.1f}" width="{bw*0.68:.1f}" height="{h:.1f}" rx="2" fill="url(#bar)" style="animation-delay:{i*0.03:.2f}s"/>')
    a(f'<text class="s" x="{bx}" y="{by+16}" style="font-size:9px">{start.strftime("%b %Y").upper()}</text>')
    a(f'<text class="s" x="870" y="{by+16}" text-anchor="end" style="font-size:9px">{today.strftime("%b %Y").upper()}</text>')
    a(f'<text class="s" x="870" y="{by-bh-6}" text-anchor="end" style="font-size:9px">PEAK WEEK: {mx}</text>')
    a("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    svg = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print("wrote", os.path.abspath(OUT), len(svg), "bytes")
