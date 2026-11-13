"""Builds the site into _site/, which is what gets deployed: the homepage, one page per articles/<slug>/index.md,
the articles index (featured first, then newest), one page per pages/<slug>.md, /contributions from the GitHub API,
/site/, the aliases, sitemap.xml and llms.txt. Every page extends templates/base.html.j2. Fails on a broken internal link.

    pip install markdown jinja2 pyyaml
    GH_TOKEN=$(gh auth token) python build.py   # without GH_TOKEN, /contributions is skipped
    python -m http.server -d _site              # preview
"""
import datetime
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

SITE = "https://kcvdh.com"
ROOT = Path(__file__).parent
ARTICLES = ROOT / "articles"
PAGES = ROOT / "pages"
OUT = ROOT / "_site"
# Copied into _site/ as they are. Everything else in the repo is source and is not published.
STATIC = ["assets", "resume.pdf", "robots.txt", "CNAME", ".nojekyll", "12b6164e53b149f6b7ea5543f1d5cc12.txt"]
GITHUB_LOGIN = "kvandeh"
# Short, guessable URLs. Each is a small indexable page that redirects to its target, and is listed in the sitemap.
ALIASES = {
    "about": "/now/", "techstack": "/uses/", "stack": "/uses/", "setup": "/uses/",
    "blog": "/articles/", "posts": "/articles/", "writing": "/articles/",
    "github": "/contributions/", "opensource": "/contributions/", "oss": "/contributions/",
    "cv": "/resume.pdf", "resume": "/resume.pdf",
    "projects": "/#projects", "contact": "/#contact", "sitemap": "/site/",
}


def read_markdown(md_file):
    header, body = re.match(r"---\n(.*?)\n---\n(.*)", md_file.read_text(encoding="utf-8"), re.S).groups()
    meta = yaml.safe_load(header)
    meta["body"] = markdown.markdown(body, extensions=["extra"])
    return meta, body


def read_article(md_file):
    meta, body = read_markdown(md_file)
    meta["featured"] = meta.get("featured", False)
    meta["slug"] = md_file.parent.name
    meta["minutes"] = max(1, round(len(body.split()) / 220))
    return meta


def read_page(md_file):
    page = read_markdown(md_file)[0]
    page["slug"] = md_file.stem
    page.setdefault("card", page["summary"])  # first-person line on /site/
    return page


env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["j2"]),
                  trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
env.filters["nice"] = lambda date: date.strftime("%d %B %Y").lstrip("0")
env.globals.update(site=SITE, year=datetime.date.today().year)


def render(template, **context):
    return env.get_template(template).render(**context)


def write(path, text):
    """Write a file under _site/, e.g. write("uses/index.html", ...)."""
    path = OUT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def minify_css(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    return re.sub(r"\s*([{};,>])\s*", r"\1", css).replace(";}", "}").strip()


def broken_links():
    """Every href/src in _site/ that points at a file which does not exist."""
    broken = []
    for page in OUT.rglob("*.html"):
        for link in re.findall(r'<(?:a|link|img)[^>]*?\s(?:href|src)="([^"#?]+)', page.read_text(encoding="utf-8")):
            if re.match(r"[a-z]+:", link):  # https:, mailto:
                continue
            target = (OUT / link.lstrip("/")) if link.startswith("/") else (page.parent / link)
            if not (target.is_file() or (target / "index.html").is_file()):
                broken.append(f"{page.relative_to(OUT)} -> {link}")
    return broken


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
    days = [{"date": d["date"], "count": d["contributionCount"], "level": LEVELS[d["contributionLevel"]]}
            for week in weeks for d in week["contributionDays"]]
    return {"days": days, "padding": 7 - len(weeks[0]["contributionDays"]), "total": sum(d["count"] for d in days)}


def pull_request(pr):
    commits = pr["commits"]["nodes"]
    rollup = commits[0]["commit"]["statusCheckRollup"] if commits else None
    return {"title": pr["title"], "url": pr["url"], "repo": pr["repository"]["nameWithOwner"], "ci": rollup and rollup["state"]}


def contributions_page(articles):
    user = github(PROFILE_QUERY, login=GITHUB_LOGIN)["user"]
    repos = {r["nameWithOwner"]: r for r in user["repositories"]["nodes"] + user["repositoriesContributedTo"]["nodes"]}
    for repo in repos.values():
        repo["commits"] = commits_by(repo, user["id"])
        repo["role"] = role(repo)
    ranked = sorted((r for r in repos.values() if r["commits"]), key=lambda r: r["commits"], reverse=True)
    calendar = user["contributionsCollection"]["contributionCalendar"]
    total = f'{calendar["totalContributions"]:,}'
    top = ", ".join(f"{r['name']} ({r['commits']} commits, {r['role'].lower()})" for r in ranked[:5])
    return render(
        "contributions.html.j2", root="../", articles=articles, og_type="profile",
        title="Open Source Contributions | Kieran van der Heijde",
        description=f"Kieran van der Heijde's open source work: {total} GitHub contributions in the last year across {len(ranked)} repositories.",
        summary=(f"Kieran van der Heijde made {total} public GitHub contributions in the last year across {len(ranked)} repositories. "
                 f"The repositories with the most commits by him are {top}. The page also lists his four most recent pull requests "
                 f"with their CI status, and a grid of daily activity for the last six months."),
        url=f"{SITE}/contributions/",
        schema={"@context": "https://schema.org", "@type": "ProfilePage", "url": f"{SITE}/contributions/",
                "mainEntity": {"@type": "Person", "name": "Kieran van der Heijde", "url": SITE, "sameAs": [f"https://github.com/{GITHUB_LOGIN}"]}},
        pull_requests=[pull_request(pr) for pr in user["pullRequests"]["nodes"]],
        grid=activity_grid(calendar), total=total, repos=ranked,
    )


# ---------- pages ----------

def article_page(article, articles):
    url = f"{SITE}/articles/{article['slug']}/"
    image = url + article["cover"] if "cover" in article else f"{SITE}/assets/og.png"
    return render(
        "article.html.j2", root="../../", articles=articles, article=article, og_type="article",
        title=f"{article['title']} | Kieran van der Heijde", description=article["summary"], url=url, image=image,
        schema={"@context": "https://schema.org", "@type": "BlogPosting", "headline": article["title"],
                "description": article["summary"], "datePublished": article["date"].isoformat(), "image": image, "url": url,
                "author": {"@type": "Person", "name": article["author"], "url": SITE}},
        read_next=[a for a in articles if a["slug"] != article["slug"]][:3],
    )


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    for name in STATIC:
        source = ROOT / name
        shutil.copytree(source, OUT / name) if source.is_dir() else shutil.copy2(source, OUT / name)
    for image in ARTICLES.glob("*/*.*"):
        if image.suffix not in {".md", ".html"}:  # article images
            (OUT / image.relative_to(ROOT)).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image, OUT / image.relative_to(ROOT))
    write("styles.css", minify_css((ROOT / "styles.css").read_text(encoding="utf-8")))

    articles = sorted((read_article(f) for f in ARTICLES.glob("*/index.md")), key=lambda a: (a["featured"], a["date"]), reverse=True)
    pages = [read_page(md) for md in sorted(PAGES.glob("*.md"))]

    for page in pages:
        write(f"{page['slug']}/index.html", render(
            "page.html.j2", root="../", articles=articles, page=page, title=f"{page['title']} | Kieran van der Heijde",
            description=page["summary"], summary=page.get("ai_summary"), url=f"{SITE}/{page['slug']}/"))
    for alias, target in ALIASES.items():
        write(f"{alias}/index.html", render("alias.html.j2", target=target))

    if os.environ.get("GH_TOKEN"):
        try:
            write("contributions/index.html", contributions_page(articles))
        except (urllib.error.URLError, RuntimeError) as error:  # GitHub down must not stop the deploy
            print(f"Skipped /contributions, GitHub API failed: {error}")
    if (OUT / "contributions" / "index.html").exists():
        pages.append({"slug": "contributions", "title": "Contributions",
                      "card": "My public GitHub activity, recent pull requests and every repository.",
                      "summary": "Public GitHub activity, recent pull requests and every repository Kieran contributed to, rebuilt daily."})

    for article in articles:
        write(f"articles/{article['slug']}/index.html", article_page(article, articles))
    write("articles/index.html", render(
        "articles.html.j2", root="../", articles=articles, title="Articles | Kieran van der Heijde",
        description="Articles by Kieran van der Heijde about software, infrastructure and careers.", url=f"{SITE}/articles/"))

    write("index.html", render(
        "home.html.j2", root="", home=True, articles=articles, url=f"{SITE}/",
        title="Kieran van der Heijde | Python Engineer",
        description="Kieran van der Heijde, Python Engineer at ASML in Veldhoven, Netherlands. Python, Flask, and FastAPI. Creator of PeekSeek and AlgoStudio.",
        og_description="Software by profession, engineer by obsession. The builder behind PeekSeek and AlgoStudio.",
        summary=("Personal site of Kieran van der Heijde, a Python Engineer at ASML in Veldhoven, the Netherlands. He works mostly in Python "
                 "with Flask and FastAPI. He built and runs PeekSeek, a competitive matchmaking platform for the game Unturned with more than "
                 "2,000 users and 10,000 matches, officially partnered with Smartly Dressed Games, and AlgoStudio, a platform for teaching "
                 "programming with sandboxed Python and C#. The site also has articles, his open source contributions, his tech stack and "
                 "his resume. He is open to Python and software roles across the Netherlands.")))

    write("site/index.html", render(
        "site.html.j2", root="../", articles=articles, pages=pages, title="Site map | Kieran van der Heijde",
        description="Every page on kcvdh.com: Kieran van der Heijde's projects, articles, open source contributions, tech stack and resume.",
        url=f"{SITE}/site/"))
    pages.append({"slug": "site", "title": "Site", "summary": "Every page and article on kcvdh.com."})
    write("sitemap.xml", render("sitemap.xml.j2", articles=articles, pages=pages, aliases=ALIASES, today=datetime.date.today().isoformat()))
    write("llms.txt", render("llms.txt.j2", articles=articles, pages=pages))
    if broken := broken_links():
        raise SystemExit("Broken internal links:\n  " + "\n  ".join(broken))
    print(f"Built {len(articles)} article(s) into _site/.")


if __name__ == "__main__":
    main()
