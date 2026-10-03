"""Regenerate dark_mode.svg / light_mode.svg with live GitHub stats.

Runs daily via GitHub Actions. Stdlib only, no dependencies.
"""
import calendar
import html
import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone

USER = "jarbasgoncal"
BIRTHDAY = date(1989, 3, 7)
JOINED_YEAR = 2023  # account creation year, never changes
W = 56  # info column width in characters
TOP_LANGS = 4  # how many languages to show

# Markup/template/build languages excluded from "Programming" ranking.
MARKUP_EXCLUDE = {
    "HTML", "CSS", "SCSS", "Less", "Sass", "Stylus", "Twig", "Blade", "Smarty",
    "Jinja", "Handlebars", "Mustache", "Makefile", "Dockerfile", "Shell",
    "Batchfile", "PowerShell", "Nix", "CMake", "Starlark",
}
# SQL dialect names reported by Linguist, normalized to "SQL".
SQL_DIALECTS = {"PLSQL", "PLpgSQL", "TSQL"}
FALLBACK_LANGS = "Python, JavaScript, SQL, PHP"

ART = r"""
::::::::::::::::::::::::::::::-::.:::::::::::::::::::---------------------------
:::::::::::::::::::::::::::::::::.:::::::::::::::::::---------------------------
:::::::::::::::::::::::::::::::=::::-+++=--::::::::::::-------------------------
::::::::::::::::::::::::::::::+=.:*%%+*#**#%#%##*+--::::------------------------
:::::::::::::::::::::+-:-:--=*#*+%##%%%%%%%%%%%%%%####+=-::---------------------
::::::::::::::::::::--::::=+*#*%###%%%%##%%%@%%%%%%%@*##%%++--------------------
::::::::::::::::::::=::::-++*#*%%**#%#%%#%%%%%%#%##%@%%%#%%%#-:-----------------
::::::::::::::::::::::-=***##*###%%%%%@%%%%%%%%%%%%*%%%%%%%%%#=-----------------
::::::::::::::::::::+##%%%%#%%%%%%%%%%%@%@@%%%@@@%%%@%%###%%#%#=----------------
:::::::::::::::::::#%#%###%%%%%@@@@@@@@@%@@%%@%%%%%%%%%%%%%%%%*-----------------
:::::::::::::::::-*#+%%%%%%%%%%@@@@@%%%####*####*###*#%%%%%%@%%#=:--------------
:::::::::::::::::-*#%%%%%%%@%%%%%#*++===---:-------====+#%%%%%%%%:--------------
:::::::::::::::---*%%%%%%@@%%%*++==-----::::::::::----:--+##%%%%#:--------------
:::::::::::::::::*%%%%%%%###+==---------::::::::::::--:::-=+##%###=-------------
::::::::::::::::#%%%%%%%%#*==------------::::::::::---------+*#%%%%*------------
:::::::::::::::#%%%%%%%%#*+===-------:::::::::::::::---------=*%%%%#=-----------
::::::::::::::#%%%%%%%%%*+===------::::::::::::::::::::------=+#%%%%=-----------
:::::::::::::-*%%%%%%%#+======+====---:::::::::::::::::::-----+##%%#:-----------
::::::::::::::=%%%%%#+====+++++***#**+=-----::::--------------=*%%%=::----------
:::::::::::::.:%%%%#+====+*++++=-==****++===-----===****++====-+#%%=:-----------
:::::::::::::.:%%%%#+====++++=+==-:===++**+=--=++**++=----====-=#%%-:::---------
:::::::::::::.:%%%%#======++*###%@%#+#+++=--:-==+++++-:-======--*%+::::---------
:::::::::::...:#%%%*===----==+++++========-::---+***%%%*#+===---##:::::---------
::::::::::...=*++*#+====-----==++++=======-::---=======++===---=#:::::::--------
:::::::::::.:=+++++====----::---------===-::::---===+===----:--+-::::::--:------
::::::::::::::-=+**====------:::::::--==---:::---:------::::-----::::::-:::-----
::::::::::::::--+*+====-----:::::::::--=---.:::--::::::::::---=+=:::::::::::::--
:::::::::::..::--*+====-----:-::::::=++#*=----=--:::::::------:-:::::::::::::---
:::::::::::..:::-=+=====-----::::::-+**#**+++%*=::::::::------:::::::::::::::::-
::::::::::::...---======-------:------===+*=---::::::::::----::::::::::::::::::-
::::::::::::..::========---------+==**++=--===+==--:::-------::::::::::::::::::-
:::::::::::..::...:+++====-----=+#**=====-:----=++=-::--:----:::::::::::::::----
::::::::::.::.::...++++====-----==+#****++++++*+=++==--------::::::::::::-:::---
::::::::::.:::::::.:++++====----------===----------==------::::::::::::::::::---
:::::::::::::::....:+++++====---------===-=---------------::::::::::::::::::----
::::::::::::::.:-*%%+++++++===---------:-----------------::::::::::::::::::--::-
:::::::::::::.-#%%@%++*****++==-----:-::::::::::::----=::::::::::::::::::::::---
::::::::::::::#%#%%*********##+++==-==-:---:---:----===+:::::::::::::::::-::--:-
:::::::::::::=%%%%%%*+****#####%##**##*+=+=++**+++**+=#%-:::::::::::::::----::--
:::::::::::::%%%%%%%%*+*#######%%%%%%*%%####%##%%#**==%%%-:::::::::::::---------
:::::::::::+%%%%%%%%%%%%*########%%#%%%%%%%%%%%***+=-+%%%#%#=-:::::::::---------
::::::::-#%%%%%%%%%%%%%%%%%%##################**===-=%%%%#%###%##---::::::------
:::::-#%%%%%%%%%%%%%%%%%%%%@%%##############*+===--=%%%%%#%%#%%#%%%#%%#*=---:---
::-#%%%%%%%%%%%%%%%%%%%%%%%%#%%%%###########***=-==#%%%%%%%%%%%%%%%%%%%#%%%%#=-:
#%%%%%%%%%%%%%#%@%%%%%%%%%%%%%%%%%*#*###*++++=---*%%%%#%%%%%#%%%%%%%%%%%%%%%%%##
%%%%%%%%%%%%%%%%%@%%%%%%%%%%%%%%%%%%#====------=%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%@%%%%%#%%%%%%%##%%%%%%==--=*%@@%%%%%%%%%%%%%%%%%#%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%##%%%%%%%%%%%%%%@%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%#%%%%%%%#%%%%%@@%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%@%#%%%%%%%%%%#%#%@%%%%%%=::%%%%%%%%%%%%%%%%%%%%%%%%%#%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%#%%%%##%###%@%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%#%%%%%%%%%%%%%%%%%%%%%%%%@%%%%%%%%%%%%%%%%%%%%%%%%#%%#%%%%%%%%%%%#%%%%%%%%%%
"""

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("ACCESS_TOKEN") or ""
PRIV_TOKEN = os.environ.get("ACCESS_TOKEN") or TOKEN


def gh(url, payload=None, token=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload else None,
        headers={"Authorization": f"Bearer {token or TOKEN}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read() or "{}")


def graphql(query, variables=None, token=None):
    _, resp = gh("https://api.github.com/graphql", {"query": query, "variables": variables or {}}, token)
    if resp.get("errors"):
        raise RuntimeError(resp["errors"])
    return resp["data"]


def age(b, t):
    years = t.year - b.year - ((t.month, t.day) < (b.month, b.day))
    months = (t.month - b.month - (t.day < b.day)) % 12
    if t.day >= b.day:
        days = t.day - b.day
    else:
        pm_year, pm = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
        days = calendar.monthrange(pm_year, pm)[1] - b.day + t.day
    return years, months, days


def gh_rest(path, token=None):
    """GET on the REST API, returns parsed JSON."""
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Authorization": f"Bearer {token or TOKEN}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or "{}")


def search_total(payload):
    try:
        return int((payload or {}).get("total_count", 0))
    except (TypeError, ValueError):
        return 0


def collab_stats():
    """PRs authored / PRs reviewed / issues authored via Search API.

    contributionsCollection silently drops private-org contributions
    (e.g. clarus-comercial/sonic), while search sees them with the
    same token. Returns (prs, reviews, issues).
    """
    try:
        prs = search_total(gh_rest(f"/search/issues?q=author:{USER}+type:pr&per_page=1", PRIV_TOKEN))
        reviews = search_total(gh_rest(f"/search/issues?q=reviewed-by:{USER}+type:pr&per_page=1", PRIV_TOKEN))
        issues = search_total(gh_rest(f"/search/issues?q=author:{USER}+type:issue&per_page=1", PRIV_TOKEN))
        return prs, reviews, issues
    except Exception as e:
        print(f"warning: search prs/reviews/issues falhou ({e}) — usando zeros")
        return 0, 0, 0


def fetch_stats():
    yr_aliases = "\n".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y + 1}-01-01T00:00:00Z")'
        " { totalCommitContributions restrictedContributionsCount }"
        for y in range(JOINED_YEAR, datetime.now(timezone.utc).year + 1)
    )
    try:
        contrib = graphql(f'query {{ user(login: "{USER}") {{ {yr_aliases} }} }}')["user"]
        commits = 0
        for v in contrib.values():
            v = v or {}
            commits += v.get("totalCommitContributions", 0) + v.get("restrictedContributionsCount", 0)
    except Exception as e:
        print(f"warning: contributions falhou ({e}) — usando zeros")
        commits = 0
    prs, reviews, issues = collab_stats()
    try:
        u = graphql(f"""
        query {{
          user(login: "{USER}") {{
            id
            followers {{ totalCount }}
            following {{ totalCount }}
            repositories(first: 100, ownerAffiliations: OWNER) {{
              totalCount
              nodes {{ name stargazerCount forkCount isFork
                languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
                  edges {{ size node {{ name }} }}
                }}
              }}
            }}
            repositoriesContributedTo(first: 100, contributionTypes: [COMMIT, PULL_REQUEST]) {{
              totalCount
              nodes {{ nameWithOwner isFork
                languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
                  edges {{ size node {{ name }} }}
                }}
              }}
            }}
          }}
        }}""", token=PRIV_TOKEN)["user"]
    except Exception as e:
        print(f"warning: user/repos falhou ({e}) — usando zeros")
        return {"followers": 0, "following": 0, "repos": 0, "contributed": 0,
                "stars": 0, "forks": 0, "commits": commits, "prs": prs,
                "reviews": reviews, "issues": issues, "languages": FALLBACK_LANGS,
                "streak": "—", "loc_add": 0, "loc_del": 0, "loc": 0}
    owned = [n for n in u["repositories"]["nodes"] if not n["isFork"]]
    contributed = [n for n in u["repositoriesContributedTo"]["nodes"] if not n["isFork"]]
    stats = {
        "followers": u["followers"]["totalCount"],
        "following": u["following"]["totalCount"],
        "repos": u["repositories"]["totalCount"],
        "contributed": u["repositoriesContributedTo"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "forks": sum(n["forkCount"] for n in u["repositories"]["nodes"]),
        "commits": commits,
        "prs": prs,
        "reviews": reviews,
        "issues": issues,
        "languages": top_languages(owned, contributed),
        "streak": streak(),
    }
    repos = [(USER, n["name"]) for n in owned]
    repos += [tuple(n["nameWithOwner"].split("/", 1)) for n in contributed
              if "/" in n["nameWithOwner"] and n["nameWithOwner"].split("/", 1)[0] != USER]
    stats.update(loc(repos, u["id"]))
    return stats


def top_languages(owned, contributed):
    """Aggregate Linguist bytes across owned + contributed repos.

    Returns e.g. "PHP 73%, JavaScript 20%, SQL 5%, Python 1%".
    """
    try:
        totals = {}
        seen = set()
        for n in list(owned) + list(contributed):
            key = n.get("nameWithOwner") or n.get("name", "")
            if key in seen:
                continue
            seen.add(key)
            for e in (n.get("languages") or {}).get("edges", []):
                name = (e.get("node") or {}).get("name", "")
                if not name or name in MARKUP_EXCLUDE:
                    continue
                if name in SQL_DIALECTS:
                    name = "SQL"
                totals[name] = totals.get(name, 0) + (e.get("size") or 0)
        ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:TOP_LANGS]
        if not ranked:
            return FALLBACK_LANGS
        total = sum(totals.values()) or 1
        return ", ".join(f"{name} {size * 100 // total}%" for name, size in ranked)
    except Exception as e:
        print(f"warning: languages falhou ({e}) — usando fallback")
        return FALLBACK_LANGS


def streak(days=370):
    """Current + longest contribution streak from the contribution calendar."""
    try:
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00Z")
        end = now.strftime("%Y-%m-%dT00:00:00Z")
        cal = graphql(f"""
        query {{
          user(login: "{USER}") {{
            contributionsCollection(from: "{start}", to: "{end}") {{
              contributionCalendar {{
                weeks {{ contributionDays {{ date contributionCount }} }}
              }}
            }}
          }}
        }}""")["user"]["contributionsCollection"]["contributionCalendar"]
        seq = [d for w in cal["weeks"] for d in w["contributionDays"]]
        best = cur = 0
        for d in seq:
            cur = cur + 1 if d["contributionCount"] > 0 else 0
            best = max(best, cur)
        if seq and seq[-1]["contributionCount"] == 0:
            cur = 0
            for d in reversed(seq[:-1]):
                if d["contributionCount"] > 0:
                    cur += 1
                else:
                    break
        day = lambda n: "day" if n == 1 else "days"
        return f"{cur} {day(cur)} (max {best})"
    except Exception as e:
        print(f"warning: streak falhou ({e})")
        return "—"


LOC_QUERY = """
query($owner: String!, $name: String!, $id: ID!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef { target { ... on Commit {
      history(first: 100, author: {id: $id}, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { additions deletions }
      }
    } } }
  }
}"""


def loc(repos, user_id):
    """Sum additions/deletions of the user's own commits.

    repos: list of (owner, name). Only the user's commits count
    (author filter), including contributed repos like other orgs.
    """
    add = rem = 0
    for owner, name in repos:
        cursor = None
        try:
            while True:
                ref = graphql(LOC_QUERY, {"owner": owner, "name": name, "id": user_id, "cursor": cursor}, token=PRIV_TOKEN)["repository"]["defaultBranchRef"]
                if ref is None:
                    break  # empty repo
                h = ref["target"]["history"]
                add += sum(n["additions"] for n in h["nodes"])
                rem += sum(n["deletions"] for n in h["nodes"])
                if not h["pageInfo"]["hasNextPage"]:
                    break
                cursor = h["pageInfo"]["endCursor"]
        except Exception as e:
            print(f"loc {owner}/{name}: {e}")
    return {"loc_add": add, "loc_del": rem, "loc": add - rem}


PALETTES = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "art": "#8b949e", "h": "#58a6ff",
             "k": "#ffa657", "v": "#c9d1d9", "d": "#484f58", "g": "#3fb950", "r": "#f85149"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "art": "#57606a", "h": "#0969da",
              "k": "#953800", "v": "#24292f", "d": "#afb8c1", "g": "#1a7f37", "r": "#cf222e"},
}


def kv(key, val, width=W):
    dots = "." * max(width - len(key) - len(str(val)) - 3, 1)
    return [(f"{key}: ", "k"), (dots + " ", "d"), (str(val), "v")]


def kv2(k1, v1, k2, v2):
    left = kv(k1, v1, 30)
    return left + [(" | ", "d")] + kv(k2, v2, 23)


def rule(title=""):
    label = f"─ {title} " if title else ""
    return [(label, "h"), ("─" * (W - len(label)), "d")]


def info_lines(s):
    y, m, d = age(BIRTHDAY, date.today())
    n = lambda x: f"{x:,}"
    return [
        [(f"{USER.lower()}@github ", "h"), ("─" * (W - len(USER) - 8), "d")],
        [],
        kv("OS", "Linux Zorin OS, Windows"),
        kv("Uptime", f"{y} years, {m} months, {d} days"),
        kv("Kernel", "Software Analyst & Developer"),
        kv("IDE", "VS Code"),
        [],
        kv("Languages.Programming", s["languages"]),
        kv("Hobbies", "Gaming, Tech"),
        [],
        rule("Contact"),
        kv("Email", "jarbasgoncal@gmail.com"),
        kv("LinkedIn", "in/jarbasgoncal"),
        [],
        rule("GitHub Stats"),
        kv2("Repos", f"{s['repos']} {{Contributed: {s['contributed']}}}", "Stars", n(s["stars"])),
        kv2("Commits", n(s["commits"]), "Followers", n(s["followers"])),
        kv2("PRs", n(s["prs"]), "Reviews", n(s["reviews"])),
        kv2("Issues", n(s["issues"]), "Forks", n(s["forks"])),
        kv2("Following", n(s["following"]), "Streak", s["streak"]),
        [("Lines of Code: ", "k"), (n(s["loc"]), "v"), (" ( ", "d"),
         (n(s["loc_add"]) + "++", "g"), (", ", "d"), (n(s["loc_del"]) + "--", "r"), (" )", "d")],
    ]


ART_FONT_SIZE = 9
ART_LINE_H = 11
ART_X = 20
ART_Y0 = 35
INFO_FONT_SIZE = 13
INFO_LINE_H = 21
INFO_X = 485
INFO_Y0 = 45
SVG_W = 1040
SVG_H = 650


def render(mode, stats):
    p = PALETTES[mode]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}" '
        f'font-family="Consolas, Menlo, monospace" font-size="{INFO_FONT_SIZE}px">',
        f'<rect x="0.5" y="0.5" width="{SVG_W - 1}" height="{SVG_H - 1}" rx="10" fill="{p["bg"]}" stroke="{p["border"]}"/>',
    ]
    for i, line in enumerate(ART.strip("\n").split("\n")):
        out.append(f'<text x="{ART_X}" y="{ART_Y0 + i * ART_LINE_H}" fill="{p["art"]}" font-size="{ART_FONT_SIZE}px" xml:space="preserve">{html.escape(line)}</text>')
    for i, segs in enumerate(info_lines(stats)):
        if not segs:
            continue
        spans = "".join(f'<tspan fill="{p[c]}">{html.escape(t)}</tspan>' for t, c in segs)
        out.append(f'<text x="{INFO_X}" y="{INFO_Y0 + i * INFO_LINE_H}" xml:space="preserve">{spans}</text>')
    out.append("</svg>")
    return "\n".join(out)


def selfcheck():
    assert age(date(1989, 1, 15), date(2026, 7, 10)) == (37, 5, 25)
    assert age(date(2000, 3, 31), date(2026, 4, 1)) == (26, 0, 1)
    assert age(date(2000, 1, 1), date(2026, 1, 1)) == (26, 0, 0)
    assert len("".join(t for t, _ in kv("OS", "Windows, macOS"))) == W
    sample = {"repos": 4, "contributed": 1, "stars": 0, "forks": 0,
              "commits": 43, "followers": 1, "following": 5, "prs": 10,
              "reviews": 7, "issues": 3, "streak": "12 days (max 45)",
              "languages": "PHP 73%, JavaScript 20%, SQL 5%, Python 1%",
              "loc": 27120, "loc_add": 28117, "loc_del": 997}
    lines = info_lines(sample)
    art = ART.strip("\n").split("\n")
    assert ART_Y0 + (len(art) - 1) * ART_LINE_H + 20 <= SVG_H, "arte corta embaixo"
    # largura estimada: monospace ~0.6 * font-size por coluna
    assert ART_X + max(len(l) for l in art) * ART_FONT_SIZE * 0.6 + 20 <= INFO_X, "arte sobrepoe info"
    assert INFO_Y0 + (len(lines) - 1) * INFO_LINE_H + 25 <= SVG_H, "info corta embaixo"
    widest = max(len("".join(t for t, _ in segs)) for segs in lines if segs)
    assert INFO_X + widest * INFO_FONT_SIZE * 0.6 + 20 <= SVG_W, "info corta à direita"
    # agregação de linguagens: filtro markup + PLSQL->SQL (fixture sopro Sonic)
    fx_owned = [{"name": "pavaflow",
                 "languages": {"edges": [{"size": 334158, "node": {"name": "PHP"}},
                                         {"size": 69421, "node": {"name": "Twig"}},
                                         {"size": 7159, "node": {"name": "JavaScript"}}]}}]
    fx_contrib = [{"nameWithOwner": "clarus-comercial/sonic",
                   "languages": {"edges": [{"size": 1448362, "node": {"name": "PHP"}},
                                           {"size": 477819, "node": {"name": "JavaScript"}},
                                           {"size": 126402, "node": {"name": "PLSQL"}},
                                           {"size": 42381, "node": {"name": "CSS"}}]}}]
    got = top_languages(fx_owned, fx_contrib)
    assert got.startswith("PHP") and "JavaScript" in got and "SQL" in got, got
    assert "Twig" not in got and "CSS" not in got and "PLSQL" not in got, got
    assert search_total({"total_count": 150, "incomplete_results": False}) == 150
    assert search_total({}) == 0 and search_total(None) == 0


if __name__ == "__main__":
    selfcheck()
    stats = fetch_stats()
    print("stats:", stats)
    for mode in PALETTES:
        with open(f"{mode}_mode.svg", "w", encoding="utf-8") as f:
            f.write(render(mode, stats))
    print("wrote dark_mode.svg, light_mode.svg")
