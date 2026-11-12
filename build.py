"""Builds the articles: one page per articles/<slug>/index.md, the articles index (featured first, then newest),
the carousel and footer on the front page, and sitemap.xml.

    pip install markdown
    python build.py
"""
import datetime
import html
import json
import re
from pathlib import Path

import markdown

SITE = "https://kcvdh.com"
ROOT = Path(__file__).parent
ARTICLES = ROOT / "articles"
EXTERNAL_LINKS = [
    "https://www.linkedin.com/in/kcvdh",
    "https://github.com/kvandeh",
    "https://github.com/sponsors/kvandeh",
    "https://peekseek.net/",
    "https://github.com/PeekSeek/PeekSeek",
    "https://angelo.kcvdh.com/",
    "https://github.com/kvandeh/Angelo",
    "https://github.com/kvandeh/Bouncer",
]


def read_article(md_file):
    header, body = re.match(r"---\n(.*?)\n---\n(.*)", md_file.read_text(encoding="utf-8"), re.S).groups()
    meta = dict(line.split(":", 1) for line in header.splitlines() if line.strip())
    meta = {key.strip(): value.strip() for key, value in meta.items()}
    meta["featured"] = meta.get("featured", "").lower() == "true"
    meta["slug"] = md_file.parent.name
    meta["date"] = datetime.date.fromisoformat(meta["date"])
    meta["body"] = markdown.markdown(body, extensions=["extra"])
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
      <a class="foot-name" href="{root}">Kieran van der Heijde</a>
      <p class="foot-role">Python Engineer @ <span class="asml-mark" role="img" aria-label="ASML"></span></p>
      <div class="foot-icons">
        <a class="iconlink" href="https://www.linkedin.com/in/kcvdh" rel="me" aria-label="LinkedIn"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.36V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.45v6.29zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.22.79 24 1.77 24h20.45c.98 0 1.78-.78 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/></svg></a>
        <a class="iconlink" href="https://github.com/kvandeh" rel="me" aria-label="GitHub"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5C5.37.5 0 5.78 0 12.29c0 5.2 3.44 9.6 8.21 11.16.6.11.82-.25.82-.56 0-.28-.01-1.02-.02-2-3.34.71-4.04-1.59-4.04-1.59-.55-1.37-1.34-1.74-1.34-1.74-1.09-.74.08-.73.08-.73 1.2.08 1.84 1.22 1.84 1.22 1.07 1.8 2.81 1.28 3.5.98.11-.76.42-1.28.76-1.57-2.67-.3-5.47-1.31-5.47-5.83 0-1.29.47-2.34 1.23-3.17-.12-.3-.53-1.52.12-3.17 0 0 1.01-.32 3.3 1.21a11.6 11.6 0 0 1 6 0c2.29-1.53 3.3-1.21 3.3-1.21.65 1.65.24 2.87.12 3.17.77.83 1.23 1.88 1.23 3.17 0 4.53-2.81 5.53-5.49 5.82.43.36.82 1.09.82 2.2 0 1.59-.01 2.87-.01 3.26 0 .31.22.68.83.56C20.56 21.88 24 17.49 24 12.29 24 5.78 18.63.5 12 .5z"/></svg></a>
        <a class="iconlink" href="mailto:kieran@kcvdh.com" aria-label="Email"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2zm0 2v.4l8 5 8-5V6H4zm16 2.3-7.47 4.67a1 1 0 0 1-1.06 0L4 8.3V18h16V8.3z"/></svg></a>
        <a href="{root}resume.pdf">Resume</a>
      </div>
    </div>
    <nav aria-label="Projects">
      <h2>Projects</h2>
      <ul>
        <li><a href="https://peekseek.net">PeekSeek</a></li>
        <li>AlgoStudio</li>
        <li><a href="https://angelo.kcvdh.com">Angelo</a></li>
        <li><a href="https://github.com/kvandeh/Bouncer">Bouncer</a></li>
      </ul>
    </nav>
    <nav aria-label="Articles">
      <h2>Articles</h2>
      <ul>{latest}<li><a href="{root}articles/">All articles</a></li></ul>
    </nav>
  </div>
  <p class="foot-legal">© {datetime.date.today().year} Kieran van der Heijde</p>
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
        f'<a class="now-chip" href="{root}" aria-label="Kieran van der Heijde, home page">',
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


def head(title, description, url, image, root, extra=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}" />
<meta name="author" content="Kieran van der Heijde" />
<link rel="canonical" href="{url}" />
<meta property="og:type" content="article" />
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
    return head(f"{article['title']} | Kieran van der Heijde", article["summary"], url, image, root, extra) + f"""<main id="content">
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


def replace_block(text, name, block):
    return re.sub(rf"<!-- build:{name} -->.*?<!-- /build:{name} -->", lambda _: block, text, flags=re.S)


def sitemap(articles):
    today = datetime.date.today().isoformat()
    pages = [(f"{SITE}/", today), (f"{SITE}/articles/", today), (f"{SITE}/resume.pdf", None)]
    pages += [(f"{SITE}/articles/{a['slug']}/", a["date"].isoformat()) for a in articles]
    pages += [(link, None) for link in EXTERNAL_LINKS]
    rows = "".join(
        f"  <url><loc>{loc}</loc>{f'<lastmod>{mod}</lastmod>' if mod else ''}</url>\n" for loc, mod in pages
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}</urlset>\n'


def main():
    articles = sorted((read_article(f) for f in ARTICLES.glob("*/index.md")), key=lambda a: (a["featured"], a["date"]), reverse=True)
    for article in articles:
        (ARTICLES / article["slug"] / "index.html").write_text(article_page(article, articles), encoding="utf-8")
    (ARTICLES / "index.html").write_text(index_page(articles), encoding="utf-8")

    front = ROOT / "index.html"
    text = replace_block(front.read_text(encoding="utf-8"), "articles", carousel(articles))
    text = replace_block(text, "footer", footer(articles, ""))
    front.write_text(text, encoding="utf-8")

    (ROOT / "sitemap.xml").write_text(sitemap(articles), encoding="utf-8")
    print(f"Built {len(articles)} article(s).")


if __name__ == "__main__":
    main()
