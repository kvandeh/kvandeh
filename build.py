"""Builds the site from templates/: one page per articles/<slug>/index.md, the articles index (featured first,
then newest), one page per pages/<slug>.md, /contributions from the GitHub API, /site/, sitemap.xml, llms.txt,
and the carousel and footer on the front page. Every page shares templates/base.html.j2 and footer.html.j2.

    pip install markdown jinja2
    GH_TOKEN=$(gh auth token) python build.py   # without GH_TOKEN, /contributions is skipped
"""
import datetime
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

SITE = "https://kcvdh.com"
ROOT = Path(__file__).parent
ARTICLES = ROOT / "articles"
PAGES = ROOT / "pages"
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


def read_page(md_file):
    page = read_markdown(md_file)[0]
    page["slug"] = md_file.stem
    page.setdefault("card", page["summary"])  # first-person line on /site/
    return page


# ---------- parts of the front page, reused on every page ----------

def front_page_part(pattern):
    return re.search(pattern, (ROOT / "index.html").read_text(encoding="utf-8"), re.S).group(0)


def site_header(root):
    """The front page's header. There the chip opens LinkedIn; everywhere else it leads home."""
    header = front_page_part(r'<header class="topbar">.*?</header>').replace('="./', f'="{root}')
    header = re.sub(r'<a class="now-chip" href="https://www.linkedin.com/in/kcvdh"[^>]*>', f'<a class="now-chip" href="{root}">', header)
    return Markup(header)


def contact_section(root):
    """The front page's "Let's talk" block, reused at the end of every article."""
    section = front_page_part(r'<section class="contact reveal" id="contact">.*?</section>')
    return Markup(section.replace(' reveal"', '"').replace('="./', f'="{root}'))


env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["j2"]),
                  trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
env.filters["nice"] = lambda date: date.strftime("%d %B %Y").lstrip("0")
env.globals.update(site=SITE, year=datetime.date.today().year, header=site_header, contact=contact_section)


def render(template, **context):
    return env.get_template(template).render(**context)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def replace_block(text, name, block):
    return re.sub(rf"<!-- build:{name} -->.*?<!-- /build:{name} -->", lambda _: block.strip(), text, flags=re.S)


def main():
    articles = sorted((read_article(f) for f in ARTICLES.glob("*/index.md")), key=lambda a: (a["featured"], a["date"]), reverse=True)
    pages = [read_page(md) for md in sorted(PAGES.glob("*.md"))]

    for page in pages:
        write(ROOT / page["slug"] / "index.html", render(
            "page.html.j2", root="../", articles=articles, page=page, title=f"{page['title']} | Kieran van der Heijde",
            description=page["summary"], summary=page.get("ai_summary"), url=f"{SITE}/{page['slug']}/"))
    for alias, target in ALIASES.items():
        write(ROOT / alias / "index.html", render("alias.html.j2", target=target))

    if os.environ.get("GH_TOKEN"):
        try:
            write(ROOT / "contributions" / "index.html", contributions_page(articles))
        except (urllib.error.URLError, RuntimeError) as error:  # GitHub down must not stop the deploy
            print(f"Skipped /contributions, GitHub API failed: {error}")
    if (ROOT / "contributions" / "index.html").exists():
        pages.append({"slug": "contributions", "title": "Contributions",
                      "card": "My public GitHub activity, recent pull requests and every repository.",
                      "summary": "Public GitHub activity, recent pull requests and every repository Kieran contributed to, rebuilt daily."})

    for article in articles:
        write(ARTICLES / article["slug"] / "index.html", article_page(article, articles))
    write(ARTICLES / "index.html", render(
        "articles.html.j2", root="../", articles=articles, title="Articles | Kieran van der Heijde",
        description="Articles by Kieran van der Heijde about software, infrastructure and careers.", url=f"{SITE}/articles/"))

    front = ROOT / "index.html"
    text = replace_block(front.read_text(encoding="utf-8"), "articles", render("carousel.html.j2", articles=articles))
    text = replace_block(text, "footer", render("footer.html.j2", root="", articles=articles))
    front.write_text(text, encoding="utf-8")

    write(ROOT / "site" / "index.html", render(
        "site.html.j2", root="../", articles=articles, pages=pages, title="Site map | Kieran van der Heijde",
        description="Every page on kcvdh.com: Kieran van der Heijde's projects, articles, open source contributions, tech stack and resume.",
        url=f"{SITE}/site/"))
    pages.append({"slug": "site", "title": "Site", "summary": "Every page and article on kcvdh.com."})
    write(ROOT / "sitemap.xml", render("sitemap.xml.j2", articles=articles, pages=pages, aliases=ALIASES, today=datetime.date.today().isoformat()))
    write(ROOT / "llms.txt", render("llms.txt.j2", articles=articles, pages=pages))
    print(f"Built {len(articles)} article(s).")


if __name__ == "__main__":
    main()
