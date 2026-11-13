"""Builds the site: one page per articles/<slug>/index.md, the articles index (featured first, then newest),
one page per pages/<slug>.md, /contributions from the GitHub API, the carousel and footer on the front page,
and sitemap.xml. Every page gets the front page's header and the one footer below.

    pip install markdown
    GH_TOKEN=$(gh auth token) python build.py   # without GH_TOKEN, /contributions is skipped
"""
import datetime
import html
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

import markdown

SITE = "https://kcvdh.com"
ROOT = Path(__file__).parent
ARTICLES = ROOT / "articles"
PAGES = ROOT / "pages"
GITHUB_LOGIN = "kvandeh"


def read_markdown(md_file):
    header, body = re.match(r"---\n(.*?)\n---\n(.*)", md_file.read_text(encoding="utf-8"), re.S).groups()
    meta = dict(line.split(":", 1) for line in header.splitlines() if line.strip())
    meta = {key.strip(): value.strip() for key, value in meta.items()}
    meta["body"] = markdown.markdown(body, extensions=["extra"])
    return meta, body


def read_article(md_file):
    meta, body = read_markdown(md_file)
    meta["featured"] = meta.get("featured", "").lower() == "true"
    meta["slug"] = md_file.parent.name
    meta["date"] = datetime.date.fromisoformat(meta["date"])
    meta["minutes"] = max(1, round(len(body.split()) / 220))
    return meta


def featured_label(article):
    # Every card gets the label row, hidden when not featured, so all titles line up.
    if article["featured"]:
        return '<span class="featured">Featured</span>'
    return '<span class="featured" aria-hidden="true" style="visibility: hidden">Featured</span>'


# Syntax highlighting for ```language fenced blocks; the autoloader fetches each grammar on demand.
PRISM = """<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" />
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"></script>
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>"""


def relative_date(date):
    """Exact date in the tooltip; the script on the page rewrites the text as "3 days ago"."""
    exact = date.strftime("%d %B %Y").lstrip("0")
    return f'<time class="relative" datetime="{date.isoformat()}" title="{exact}">{exact}</time>'


RELATIVE_DATE_SCRIPT = """<script>
  document.querySelectorAll('time.relative').forEach(function (t) {
    var days = Math.round((Date.now() - new Date(t.dateTime)) / 864e5);
    var units = [[365, 'year'], [30, 'month'], [7, 'week'], [1, 'day']];
    if (days < 1) { t.textContent = 'Today'; return; }
    if (days === 1) { t.textContent = 'Yesterday'; return; }
    for (var i = 0; i < units.length; i++) {
      var n = Math.floor(days / units[i][0]);
      if (n >= 1) { t.textContent = n + ' ' + units[i][1] + (n > 1 ? 's' : '') + ' ago'; return; }
    }
  });
</script>"""


def nice_date(date):
    return f'<time datetime="{date.isoformat()}">{date.strftime("%d %B %Y").lstrip("0")}</time>'


def footer(articles, root):
    latest = "".join(
        f'<li><a href="{root}articles/{a["slug"]}/">{html.escape(a["title"])}</a></li>' for a in articles[:5]
    )
    return f"""<!-- build:footer -->
<footer class="foot">
  <div class="foot-cols">
    <div class="foot-about">
      <a class="foot-id" href="{root}">
        <span class="foot-name">Kieran van der Heijde</span>
        <span class="foot-role">Python Engineer @ <span class="asml-mark" role="img" aria-label="ASML"></span></span>
      </a>
      <div class="foot-icons">
        <a class="iconlink" href="https://www.linkedin.com/in/kcvdh" rel="me" aria-label="LinkedIn"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.36V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.45v6.29zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.22.79 24 1.77 24h20.45c.98 0 1.78-.78 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/></svg></a>
        <a class="iconlink" href="https://github.com/kvandeh" rel="me" aria-label="GitHub"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5C5.37.5 0 5.78 0 12.29c0 5.2 3.44 9.6 8.21 11.16.6.11.82-.25.82-.56 0-.28-.01-1.02-.02-2-3.34.71-4.04-1.59-4.04-1.59-.55-1.37-1.34-1.74-1.34-1.74-1.09-.74.08-.73.08-.73 1.2.08 1.84 1.22 1.84 1.22 1.07 1.8 2.81 1.28 3.5.98.11-.76.42-1.28.76-1.57-2.67-.3-5.47-1.31-5.47-5.83 0-1.29.47-2.34 1.23-3.17-.12-.3-.53-1.52.12-3.17 0 0 1.01-.32 3.3 1.21a11.6 11.6 0 0 1 6 0c2.29-1.53 3.3-1.21 3.3-1.21.65 1.65.24 2.87.12 3.17.77.83 1.23 1.88 1.23 3.17 0 4.53-2.81 5.53-5.49 5.82.43.36.82 1.09.82 2.2 0 1.59-.01 2.87-.01 3.26 0 .31.22.68.83.56C20.56 21.88 24 17.49 24 12.29 24 5.78 18.63.5 12 .5z"/></svg></a>
        <a class="iconlink" href="mailto:kieran@kcvdh.com" aria-label="Email"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 2v.4l8 5 8-5V6H4zm16 2.3-7.47 4.67a1 1 0 0 1-1.06 0L4 8.3V18h16V8.3z"/></svg></a>
        <a href="{root}resume.pdf">Resume</a>
      </div>
      <p class="foot-legal">© {datetime.date.today().year} Kieran van der Heijde</p>
    </div>
    <nav aria-label="Projects">
      <h2><a href="{root}#projects">Projects</a></h2>
      <ul>
        <li><a href="https://peekseek.net">PeekSeek</a></li>
        <li>AlgoStudio</li>
        <li><a href="https://angelo.kcvdh.com">Angelo</a></li>
        <li><a href="https://github.com/kvandeh/Bouncer">Bouncer</a></li>
      </ul>
    </nav>
    <nav aria-label="Site">
      <h2><a href="{root}site/">Site</a></h2>
      <ul>
        <li><a href="{root}contributions/">Contributions</a></li>
        <li><a href="{root}uses/">Uses</a></li>
        <li><a href="{root}now/">Now</a></li>
      </ul>
    </nav>
    <nav aria-label="Articles">
      <h2><a href="{root}articles/">Articles</a></h2>
      <ul>{latest}<li><a href="{root}articles/">All articles</a></li></ul>
    </nav>
  </div>
</footer>
<!-- /build:footer -->"""


def card(article, root):
    return f"""<li class="acard">
        <a href="{root}articles/{article['slug']}/">
          <div class="acard-body">
            {featured_label(article)}
            <h3>{html.escape(article['title'])}</h3>
            <p>{html.escape(article['summary'])}</p>
            <span class="acard-meta">{nice_date(article['date'])} · {article['minutes']} min read</span>
          </div>
        </a>
      </li>"""


def carousel(articles):
    cards = "\n      ".join(card(a, "") for a in articles)
    return f"""<!-- build:articles -->
  <section class="articles reveal" id="articles" aria-labelledby="articles-title">
    <div class="articles-head">
      <h2 id="articles-title" class="sr-only">Articles</h2>
      <a class="articles-all" href="articles/">All articles &rarr;</a>
    </div>
    <ul class="carousel" role="list">
      {cards}
    </ul>
  </section>
  <script>
    (function () {{
      var track = document.querySelector('.carousel');
      function step() {{ return track.firstElementChild.offsetWidth + parseFloat(getComputedStyle(track).columnGap); }}
      function glideTo(left) {{ track.scrollTo({{ left: left, behavior: 'smooth' }}); }}

      // Mouse wheel: one card per gesture, gliding to it. At either end the page scrolls.
      var busy = false;
      track.addEventListener('wheel', function (e) {{
        var delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
        var max = track.scrollWidth - track.clientWidth;
        if ((delta < 0 && track.scrollLeft <= 0) || (delta > 0 && track.scrollLeft >= max - 1)) return;
        e.preventDefault();
        if (busy) return;
        busy = true;
        var index = Math.round(track.scrollLeft / step()) + (delta > 0 ? 1 : -1);
        glideTo(index * step());
        setTimeout(function () {{ busy = false; }}, 450);
      }}, {{ passive: false }});

      // Mouse drag: follow the pointer, then glide to the nearest card. Touch uses native swipe.
      var startX = 0, startLeft = 0, dragging = false, moved = false;
      track.addEventListener('pointerdown', function (e) {{
        if (e.pointerType !== 'mouse' || e.button !== 0) return;
        dragging = true; moved = false; startX = e.clientX; startLeft = track.scrollLeft;
      }});
      window.addEventListener('pointermove', function (e) {{
        if (!dragging) return;
        var dx = e.clientX - startX;
        if (!moved && Math.abs(dx) < 5) return;
        moved = true;
        track.style.scrollSnapType = 'none';
        track.style.cursor = 'grabbing';
        track.scrollLeft = startLeft - dx;
      }});
      window.addEventListener('pointerup', function () {{
        if (!dragging) return;
        dragging = false;
        track.style.cursor = '';
        if (!moved) return;
        glideTo(Math.round(track.scrollLeft / step()) * step());
        setTimeout(function () {{ track.style.scrollSnapType = ''; }}, 450);
      }});
      // A drag must not open the card it ended on, or start a native link/image drag.
      track.addEventListener('click', function (e) {{ if (moved) {{ e.preventDefault(); moved = false; }} }}, true);
      track.addEventListener('dragstart', function (e) {{ e.preventDefault(); }});
    }})();
  </script>
  <!-- /build:articles -->"""


def site_header(root):
    """The front page's header, reused on every page so there is one to maintain."""
    front = (ROOT / "index.html").read_text(encoding="utf-8")
    header = re.search(r'<header class="topbar">.*?</header>', front, re.S).group(0)
    header = header.replace('="./', f'="{root}')
    # On the front page the chip opens LinkedIn; everywhere else it leads home.
    return header.replace(
        '<a class="now-chip" href="https://www.linkedin.com/in/kcvdh" target="_blank" aria-label="Kieran, Python Engineer at ASML, Veldhoven">',
        f'<a class="now-chip" href="{root}">',
    )


def contact_section(root):
    """The front page's "Let's talk" block, reused at the end of every article."""
    front = (ROOT / "index.html").read_text(encoding="utf-8")
    section = re.search(r'<section class="contact reveal" id="contact">.*?</section>', front, re.S).group(0)
    return section.replace(' reveal"', '"').replace('="./', f'="{root}')


def read_next(article, articles, root):
    others = [a for a in articles if a["slug"] != article["slug"]][:3]
    if not others:
        return ""
    cards = "\n".join(card(a, root) for a in others)
    return f"""<section class="articles" aria-labelledby="read-next">
    <h2 id="read-next" class="read-next-title">Read next</h2>
    <ul class="article-grid" role="list">
{cards}
    </ul>
  </section>"""


def ai_summary(text):
    """A plain-language summary for AI crawlers and assistants. `hidden` keeps it off screen and out of the
    accessibility tree, so screen-reader users do not hear it twice. It must only restate what the page says."""
    return f'<section class="ai-summary" hidden data-nosnippet>\n  <h2>Page summary</h2>\n  <p>{html.escape(text)}</p>\n</section>'


def head(title, description, url, image, root, extra="", og_type="website", summary=None):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}" />
<meta name="author" content="Kieran van der Heijde" />
<link rel="canonical" href="{url}" />
<meta property="og:type" content="{og_type}" />
<meta property="og:url" content="{url}" />
<meta property="og:title" content="{html.escape(title)}" />
<meta property="og:description" content="{html.escape(description)}" />
<meta property="og:image" content="{image}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="theme-color" content="#0b0b0d" />
<link rel="icon" href="{root}assets/kieran.jpg" />
<link rel="stylesheet" href="{root}styles.css" />
{extra}
</head>
<body>
<a class="skip" href="#content">Skip to the content</a>
{ai_summary(summary or description)}
{site_header(root)}
"""


def article_page(article, articles):
    url = f"{SITE}/articles/{article['slug']}/"
    image = url + article["cover"] if "cover" in article else f"{SITE}/assets/og.png"
    schema = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": article["title"],
        "description": article["summary"],
        "datePublished": article["date"].isoformat(),
        "image": image,
        "url": url,
        "author": {"@type": "Person", "name": article["author"], "url": SITE},
    }
    extra = f'<script type="application/ld+json">{json.dumps(schema)}</script>\n{PRISM}'
    root = "../../"
    return head(f"{article['title']} | Kieran van der Heijde", article["summary"], url, image, root, extra, "article") + f"""<main id="content">
  <article class="post">
    <header class="post-head">
      <div class="byline">
        <img src="{root}{article['avatar']}" alt="" width="28" height="28" />
        <b>{html.escape(article['author'])}</b>
        <span class="byline-date">{relative_date(article['date'])}</span>
      </div>
      <h1>{html.escape(article['title'])}</h1>
    </header>
    <div class="post-body">
{article['body']}
    </div>
  </article>
  {read_next(article, articles, root)}
  {contact_section(root)}
</main>
{footer(articles, root)}
{RELATIVE_DATE_SCRIPT}
</body>
</html>
"""


def index_page(articles):
    cards = "\n".join(card(a, "../") for a in articles)
    return head("Articles | Kieran van der Heijde", "Articles by Kieran van der Heijde about software, infrastructure and careers.",
                f"{SITE}/articles/", f"{SITE}/assets/og.png", "../") + f"""<main id="content">
  <section class="articles">
    <h1 class="sr-only">Articles</h1>
    <ul class="article-grid" role="list">
{cards}
    </ul>
  </section>
</main>
{footer(articles, "../")}
</body>
</html>
"""


def simple_page(slug, page):
    """A pages/<slug>.md file: same layout as an article, without byline or read-next."""
    root = "../"
    return head(f"{page['title']} | Kieran van der Heijde", page["summary"], f"{SITE}/{slug}/", f"{SITE}/assets/og.png", root, summary=page.get("ai_summary")) + f"""<main id="content">
  <article class="post">
    <h1 class="page-title">{html.escape(page['title'])}</h1>
    <div class="post-body">
{page['body']}
    </div>
  </article>
</main>
{footer(ARTICLES_FOR_FOOTER, root)}
</body>
</html>
"""


def alias_page(target):
    """A redirect that search engines fold into its target, e.g. /techstack -> /uses."""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><title>Redirecting</title>
<link rel="canonical" href="{SITE}{target}" />
<meta name="robots" content="noindex" />
<meta http-equiv="refresh" content="0; url={target}" /></head>
<body><a href="{target}">Continue to {target}</a></body></html>
"""


ALIASES = {"techstack": "/uses/", "about": "/now/"}

# ---------- /contributions, from the GitHub GraphQL API ----------

PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    id
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
    pullRequests(first: 4, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes { title url createdAt repository { nameWithOwner } commits(last: 1) { nodes { commit { statusCheckRollup { state } } } } }
    }
    repositories(first: 100, privacy: PUBLIC, ownerAffiliations: [OWNER, ORGANIZATION_MEMBER, COLLABORATOR], isFork: false) {
      nodes { ...repo }
    }
    repositoriesContributedTo(first: 100, privacy: PUBLIC, contributionTypes: [COMMIT, PULL_REQUEST]) {
      nodes { ...repo }
    }
  }
}
fragment repo on Repository {
  nameWithOwner name url description stargazerCount forkCount pushedAt
  owner { login __typename }
  primaryLanguage { name }
}
"""

COMMITS_QUERY = """
query($owner: String!, $name: String!, $author: ID!) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef { target { ... on Commit { history(author: {id: $author}) { totalCount } } } }
  }
}
"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def github(query, **variables):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}"},
    )
    for attempt in range(3):  # GitHub returns the odd 502; try again before giving up
        try:
            body = json.load(urllib.request.urlopen(request, timeout=30))
            break
        except urllib.error.URLError:
            if attempt == 2:
                raise
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def commits_by(repo, author_id):
    owner, name = repo["nameWithOwner"].split("/")
    branch = github(COMMITS_QUERY, owner=owner, name=name, author=author_id)["repository"]["defaultBranchRef"]
    return branch["target"]["history"]["totalCount"] if branch else 0


def role(repo):
    if repo["owner"]["login"].lower() == GITHUB_LOGIN:
        return "Owner"
    if repo["owner"]["__typename"] == "Organization":
        return "Member"
    return "Contributor"


def activity_grid(calendar):
    weeks = calendar["weeks"][-26:]
    cells = []
    for week in weeks:
        for day in week["contributionDays"]:
            count = day["contributionCount"]
            cells.append(f'<i class="l{LEVELS[day["contributionLevel"]]}" title="{count} on {day["date"]}"></i>')
    padding = '<i class="pad"></i>' * (7 - len(weeks[0]["contributionDays"]))
    total = sum(day["contributionCount"] for week in weeks for day in week["contributionDays"])
    return f'<div class="grid" role="img" aria-label="{total:,} contributions in the last six months">{padding}{"".join(cells)}</div>'


CI_ICONS = {
    "SUCCESS": ("passed", '<path d="M5 12.5l4.5 4.5L19 7.5"/>'),
    "FAILURE": ("failed", '<path d="M6 6l12 12M18 6L6 18"/>'),
    "ERROR": ("failed", '<path d="M6 6l12 12M18 6L6 18"/>'),
    "PENDING": ("running", '<circle cx="12" cy="12" r="4"/>'),
    "EXPECTED": ("running", '<circle cx="12" cy="12" r="4"/>'),
}


def ci_icon(pr):
    """A small check, cross or dot for the PR's last CI run; nothing when the repo has no CI."""
    commits = pr["commits"]["nodes"]
    rollup = commits[0]["commit"]["statusCheckRollup"] if commits else None
    if not rollup:
        return ""
    label, shape = CI_ICONS[rollup["state"]]
    return f'<svg class="ci ci-{label}" viewBox="0 0 24 24" role="img" aria-label="CI {label}"><title>CI {label}</title>{shape}</svg>'


def pull_request_row(pr):
    e = html.escape
    return (
        f'<li><a href="{e(pr["url"])}">{ci_icon(pr)}<span class="pr-title">{e(pr["title"])}</span>'
        f'<span class="pr-meta">{e(pr["repository"]["nameWithOwner"])}</span></a></li>'
    )


def repo_card(repo):
    e = html.escape
    language = f' · {e(repo["primaryLanguage"]["name"])}' if repo["primaryLanguage"] else ""
    description = f'<p>{e(repo["description"])}</p>' if repo["description"] else ""
    return f"""<li class="acard repo" data-name="{e(repo['name'].lower())}" data-stars="{repo['stargazerCount']}" data-forks="{repo['forkCount']}" data-commits="{repo['commits']}" data-pushed="{repo['pushedAt']}">
        <a href="{e(repo['url'])}">
          <div class="acard-body">
            <span class="repo-top"><h2>{e(repo['name'])}</h2><span class="repo-commits"><b>{repo['commits']}</b> commits by me</span></span>
            {description}
            <span class="acard-meta repo-meta"><span>{repo['stargazerCount']} stars · {repo['forkCount']} forks{language}</span><span>{e(repo['owner']['login'])} · {role(repo)}</span></span>
          </div>
        </a>
      </li>"""


SORT_SCRIPT = """<script>
  document.getElementById('sort').addEventListener('change', function () {
    var key = this.value, list = document.getElementById('repos');
    var compare = {
      name: function (a, b) { return a.dataset.name.localeCompare(b.dataset.name); },
      pushed: function (a, b) { return b.dataset.pushed.localeCompare(a.dataset.pushed); }
    }[key] || function (a, b) { return b.dataset[key] - a.dataset[key]; };
    Array.from(list.children).sort(compare).forEach(function (li) { list.appendChild(li); });
  });
</script>"""


def contributions_summary(ranked, total):
    top = ", ".join(f"{r['name']} ({r['commits']} commits, {role(r).lower()})" for r in ranked[:5])
    return (f"Kieran van der Heijde made {total} public GitHub contributions in the last year across {len(ranked)} repositories. "
            f"The repositories with the most commits by him are {top}. The page also lists his four most recent pull requests "
            f"with their CI status, and a grid of daily activity for the last six months.")


def contributions_page():
    user = github(PROFILE_QUERY, login=GITHUB_LOGIN)["user"]
    repos = {r["nameWithOwner"]: r for r in user["repositories"]["nodes"] + user["repositoriesContributedTo"]["nodes"]}
    for repo in repos.values():
        repo["commits"] = commits_by(repo, user["id"])
    ranked = sorted((r for r in repos.values() if r["commits"]), key=lambda r: r["commits"], reverse=True)
    calendar = user["contributionsCollection"]["contributionCalendar"]
    total = f'{calendar["totalContributions"]:,}'
    root = "../"
    description = f"Kieran van der Heijde's open source work: {total} GitHub contributions in the last year across {len(ranked)} repositories."
    schema = {
        "@context": "https://schema.org",
        "@type": "ProfilePage",
        "url": f"{SITE}/contributions/",
        "mainEntity": {"@type": "Person", "name": "Kieran van der Heijde", "url": SITE, "sameAs": [f"https://github.com/{GITHUB_LOGIN}"]},
    }
    extra = f'<script type="application/ld+json">{json.dumps(schema)}</script>'
    return head("Open Source Contributions | Kieran van der Heijde", description, f"{SITE}/contributions/", f"{SITE}/assets/og.png", root, extra, "profile", contributions_summary(ranked, total)) + f"""<main id="content">
  <section class="contrib">
    <h1 class="sr-only">Open source contributions</h1>
    <div class="contrib-top">
      <ul class="prs" aria-label="Recent pull requests">{"".join(pull_request_row(pr) for pr in user["pullRequests"]["nodes"])}</ul>
      {activity_grid(calendar)}
    </div>
    <div class="repos-bar">
      <p class="contrib-total"><b>{total}</b> contributions across <b>{len(ranked)}</b> repositories this year</p>
      <label>Sort by
        <select id="sort">
          <option value="commits">Commits by me</option>
          <option value="stars">Stars</option>
          <option value="forks">Forks</option>
          <option value="pushed">Recently updated</option>
          <option value="name">Name</option>
        </select>
      </label>
    </div>
    <ul class="repo-grid" id="repos" aria-label="Repositories">
      {"".join(repo_card(r) for r in ranked)}
    </ul>
  </section>
</main>
{footer(ARTICLES_FOR_FOOTER, root)}
{SORT_SCRIPT}
</body>
</html>
"""


def replace_block(text, name, block):
    return re.sub(rf"<!-- build:{name} -->.*?<!-- /build:{name} -->", lambda _: block, text, flags=re.S)


def sitemap(articles, extra_paths):
    today = datetime.date.today().isoformat()
    pages = [(f"{SITE}/", today), (f"{SITE}/articles/", today), (f"{SITE}/resume.pdf", None)]
    pages += [(f"{SITE}/articles/{a['slug']}/", a["date"].isoformat()) for a in articles]
    pages += [(f"{SITE}/{path}/", today) for path in extra_paths]
    pages.append(("https://angelo.kcvdh.com/", None))
    rows = "".join(
        f"  <url><loc>{loc}</loc>{f'<lastmod>{mod}</lastmod>' if mod else ''}</url>\n" for loc, mod in pages
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}</urlset>\n'


ARTICLES_FOR_FOOTER = []


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def page_card(href, title, summary):
    return f"""<li class="acard">
        <a href="{href}">
          <div class="acard-body">
            <h3>{html.escape(title)}</h3>
            <p>{html.escape(summary)}</p>
          </div>
        </a>
      </li>"""


def site_page(articles, extra_paths):
    """/site/: every page on the site as cards, built from the same lists as sitemap.xml and llms.txt."""
    root = "../"
    # Each pages/*.md gives its own first-person `card:` line (falling back to its SEO summary).
    summaries = {md.stem: (lambda meta: meta.get("card", meta["summary"]))(read_markdown(md)[0]) for md in PAGES.glob("*.md")}
    summaries["contributions"] = "My public GitHub activity, recent pull requests and every repository."
    pages = [page_card(root, "Home", "Who I am, PeekSeek, AlgoStudio and how to reach me."),
             page_card(f"{root}#projects", "Projects", "PeekSeek, AlgoStudio, Angelo and Bouncer.")]
    pages += [page_card(f"{root}{path}/", path.title(), summaries[path]) for path in extra_paths if path in summaries]
    pages.append(page_card(f"{root}resume.pdf", "Resume", "My resume as a PDF."))
    cards = "\n".join(pages)
    posts = "\n".join(card(a, root) for a in articles)
    description = "Every page on kcvdh.com: Kieran van der Heijde's projects, articles, open source contributions, tech stack and resume."
    return head("Site map | Kieran van der Heijde", description, f"{SITE}/site/", f"{SITE}/assets/og.png", root) + f"""<main id="content">
  <section class="articles">
    <h1 class="sr-only">Site map</h1>
    <h2 class="read-next-title">Pages</h2>
    <ul class="article-grid" role="list">
{cards}
    </ul>
    <h2 class="read-next-title site-articles-title">Articles</h2>
    <ul class="article-grid" role="list">
{posts}
    </ul>
  </section>
</main>
{footer(articles, root)}
</body>
</html>
"""


def llms_txt(articles, extra_paths):
    """A plain-text map of the site for AI crawlers (llmstxt.org), built from the same lists as the sitemap."""
    article_lines = "".join(f"- [{a['title']}]({SITE}/articles/{a['slug']}/): {a['summary']}\n" for a in articles)
    page_lines = "".join(f"- [{path.title()}]({SITE}/{path}/)\n" for path in extra_paths)
    return f"""# Kieran van der Heijde

> Python Engineer at ASML in Veldhoven, Netherlands. Builds PeekSeek and AlgoStudio with Python, FastAPI and Flask.

- [Home]({SITE}/)
- [Resume]({SITE}/resume.pdf)
{page_lines}
## Articles

{article_lines}"""


def main():
    articles = sorted((read_article(f) for f in ARTICLES.glob("*/index.md")), key=lambda a: (a["featured"], a["date"]), reverse=True)
    ARTICLES_FOR_FOOTER.extend(articles)
    extra_paths = []
    for md_file in sorted(PAGES.glob("*.md")):
        write(ROOT / md_file.stem / "index.html", simple_page(md_file.stem, read_markdown(md_file)[0]))
        extra_paths.append(md_file.stem)
    for alias, target in ALIASES.items():
        write(ROOT / alias / "index.html", alias_page(target))
    if os.environ.get("GH_TOKEN"):
        try:
            write(ROOT / "contributions" / "index.html", contributions_page())
        except (urllib.error.URLError, RuntimeError) as error:  # GitHub down must not stop the deploy
            print(f"Skipped /contributions, GitHub API failed: {error}")
    if (ROOT / "contributions" / "index.html").exists():
        extra_paths.append("contributions")
    for article in articles:
        (ARTICLES / article["slug"] / "index.html").write_text(article_page(article, articles), encoding="utf-8")
    (ARTICLES / "index.html").write_text(index_page(articles), encoding="utf-8")

    front = ROOT / "index.html"
    text = replace_block(front.read_text(encoding="utf-8"), "articles", carousel(articles))
    text = replace_block(text, "footer", footer(articles, ""))
    front.write_text(text, encoding="utf-8")

    write(ROOT / "site" / "index.html", site_page(articles, extra_paths))
    extra_paths.append("site")
    (ROOT / "sitemap.xml").write_text(sitemap(articles, extra_paths), encoding="utf-8")
    (ROOT / "llms.txt").write_text(llms_txt(articles, extra_paths), encoding="utf-8")
    print(f"Built {len(articles)} article(s).")


if __name__ == "__main__":
    main()
