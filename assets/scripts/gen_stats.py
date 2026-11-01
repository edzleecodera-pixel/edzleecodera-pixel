"""Generate self-hosted GitHub stat cards (assets/stats.svg, assets/languages.svg).

Runs inside GitHub Actions using the built-in GITHUB_TOKEN. Set MOCK=1 to test offline.
"""
import html
import json
import os
import urllib.request

USER = os.environ.get("GH_USER", "edzleecodera-pixel")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT_DIR", "assets")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


def fetch():
    if os.environ.get("MOCK"):
        return {
            "followers": {"totalCount": 4},
            "pullRequests": {"totalCount": 3},
            "issues": {"totalCount": 1},
            "contributionsCollection": {
                "totalCommitContributions": 20,
                "contributionCalendar": {"totalContributions": 23},
            },
            "repositories": {
                "totalCount": 5,
                "nodes": [
                    {"stargazerCount": 2, "languages": {"edges": [
                        {"size": 6000, "node": {"name": "Python"}},
                        {"size": 3000, "node": {"name": "HTML"}},
                        {"size": 1000, "node": {"name": "CSS"}}]}},
                    {"stargazerCount": 1, "languages": {"edges": [
                        {"size": 2500, "node": {"name": "JavaScript"}},
                        {"size": 500, "node": {"name": "Shell"}}]}},
                ],
            },
        }
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def stats_card(u):
    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    rows = [
        ("Public Repositories", u["repositories"]["totalCount"]),
        ("Total Stars Earned", stars),
        ("Commits (this year)", u["contributionsCollection"]["totalCommitContributions"]),
        ("Pull Requests", u["pullRequests"]["totalCount"]),
        ("Issues Opened", u["issues"]["totalCount"]),
        ("Followers", u["followers"]["totalCount"]),
    ]
    y = 78
    body = ""
    for label, val in rows:
        body += (
            f'<text x="28" y="{y}" class="lbl">&gt; {html.escape(label)}</text>'
            f'<text x="440" y="{y}" class="val" text-anchor="end">{val}</text>'
        )
        y += 28
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="470" height="{y + 6}" viewBox="0 0 470 {y + 6}">
<style>
text{{font-family:'Courier New',monospace}}
.t{{font-size:18px;font-weight:bold;fill:#00ff41}}
.lbl{{font-size:14px;fill:#39ff14}}
.val{{font-size:14px;font-weight:bold;fill:#00ff41}}
@keyframes b{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
.cur{{animation:b 1s steps(1) infinite}}
</style>
<rect x="1" y="1" width="468" height="{y + 4}" rx="10" fill="#0d1117" stroke="#008f11" stroke-width="2"/>
<text x="28" y="40" class="t">{html.escape(USER)} :: GitHub Stats<tspan class="cur"> _</tspan></text>
<line x1="28" y1="52" x2="442" y2="52" stroke="#0d3b13" stroke-width="2"/>
{body}
</svg>'''


def languages_card(u):
    totals = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            totals[e["node"]["name"]] = totals.get(e["node"]["name"], 0) + e["size"]
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]
    whole = sum(v for _, v in top) or 1
    shades = ["#00ff41", "#39ff14", "#00cc33", "#00a82a", "#008f11", "#006b0d"]
    y = 78
    body = ""
    if not top:
        body = '<text x="28" y="82" class="lbl">&gt; No language data yet</text>'
        y = 110
    for i, (name, size) in enumerate(top):
        pct = size / whole * 100
        w = max(4, round(pct / 100 * 414))
        body += (
            f'<text x="28" y="{y}" class="lbl">{html.escape(name)}</text>'
            f'<text x="442" y="{y}" class="val" text-anchor="end">{pct:.1f}%</text>'
            f'<rect x="28" y="{y + 7}" width="414" height="6" rx="3" fill="#0d3b13"/>'
            f'<rect x="28" y="{y + 7}" width="{w}" height="6" rx="3" fill="{shades[i]}"/>'
        )
        y += 34
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="470" height="{y + 6}" viewBox="0 0 470 {y + 6}">
<style>
text{{font-family:'Courier New',monospace}}
.t{{font-size:18px;font-weight:bold;fill:#00ff41}}
.lbl{{font-size:14px;fill:#39ff14}}
.val{{font-size:14px;font-weight:bold;fill:#00ff41}}
</style>
<rect x="1" y="1" width="468" height="{y + 4}" rx="10" fill="#0d1117" stroke="#008f11" stroke-width="2"/>
<text x="28" y="40" class="t">Most Used Languages</text>
<line x1="28" y1="52" x2="442" y2="52" stroke="#0d3b13" stroke-width="2"/>
{body}
</svg>'''


def main():
    u = fetch()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(stats_card(u))
    with open(os.path.join(OUT, "languages.svg"), "w", encoding="utf-8") as f:
        f.write(languages_card(u))
    print("stats cards written to", OUT)


if __name__ == "__main__":
    main()
