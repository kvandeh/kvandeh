---
card: "My stack as a diagram: plain JavaScript, FastAPI, PostgreSQL and Rust."
title: Uses
ai_summary: Kieran van der Heijde's tech stack. The browser runs plain JavaScript with no framework. Requests go through Traefik, which handles HTTPS and routing, to a FastAPI backend written in Python with Pydantic. FastAPI stores data in PostgreSQL through SQLAlchemy and hands performance-critical work to compiled Rust executables. Everything runs in Docker on Linux. He also uses pandas, NumPy and Metabase for data, pytest and mutation testing, Git, CI/CD, SQL and C#.
summary: "The stack Kieran van der Heijde builds with: plain JavaScript in the browser, FastAPI and PostgreSQL on the server, and Rust executables for the fast parts."
---

The stack behind PeekSeek, AlgoStudio and my day job. I keep it small on purpose.

<figure class="stack" aria-labelledby="stack-caption">
<figcaption id="stack-caption">How a request moves through my stack. Open any box for details.</figcaption>
<ol class="stack-flow">
<li class="node"><details><summary><b>Browser</b><span>Plain JavaScript</span></summary><p>No frontend framework and no build step: plain JavaScript in the browser.</p></details></li>
<li class="zone"><span class="arrow" aria-hidden="true">&rarr;</span><div class="zone-box"><span class="zone-label">Docker on Linux</span><ol class="zone-flow">
<li class="node"><details><summary><b>Traefik</b><span>Routing, TLS</span></summary><p>Receives every request, handles HTTPS and routes it to the right container.</p></details></li>
<li class="node"><span class="arrow" aria-hidden="true">&rarr;</span><details><summary><b>FastAPI</b><span>Python, Pydantic</span></summary><p>The backend. Pydantic validates the data going in and out.</p></details></li>
<li class="branch"><ul>
<li class="node"><span class="arrow arrow-up" aria-hidden="true">&nearr;</span><details><summary><b>PostgreSQL</b><span>via SQLAlchemy</span></summary><p>The database. Python talks to it through SQLAlchemy.</p></details></li>
<li class="node"><span class="arrow arrow-down" aria-hidden="true">&searr;</span><details><summary><b>Rust .exe</b><span>The fast parts</span></summary><p>Compiled Rust executables for the performance-critical work. Rust is never the web server, but it is often part of the backend.</p></details></li>
</ul></li>
</ol></div></li>
</ol>
</figure>

## Also in the toolbox

- **Data:** pandas, NumPy and Metabase
- **Testing:** pytest, unit tests and mutation testing
- **Everything else:** Git, CI/CD, SQL and C#

<!-- TODO(Kieran): editor, terminal, hardware -->
