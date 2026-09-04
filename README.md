# patchright-docker

A container image of [patchright](https://pypi.org/project/patchright/) serving
the same HTTP contract as firecrawl's `playwright-service`, so it can be dropped
in via `PLAYWRIGHT_MICROSERVICE_URL`.

```
ghcr.io/chrisns/patchright-docker:1.62.3
```

Image tags match the upstream patchright version exactly. A scheduled workflow
checks PyPI daily and cuts a matching tag and release here when upstream
publishes, which triggers the build.

## Why not the stock playwright-service

Playwright enables the CDP Runtime domain, which is observable from the page and
is the usual reason a headless browser is spotted. Patchright is a fork that
does not. On top of that this image runs real Google Chrome rather than the
bundled chromium test build, headed under Xvfb, against a persistent profile, so
sessions carry cookies and history rather than starting cold on every request.

Chrome stable is published for linux/amd64 only, so there is no arm64 image.

## Endpoints

### `POST /scrape`

The firecrawl contract.

```json
{ "url": "https://example.com", "wait_after_load": 2000, "timeout": 60000 }
```

```json
{ "content": "<html>…</html>", "pageStatusCode": 200, "pageError": null }
```

Optional: `headers`, `check_selector`.

### `POST /evaluate`

Loads a page, then runs JavaScript inside it. Requests issued from in-page JS
use Chrome's own TLS stack, cookie jar and header ordering, which a server-side
fetch does not.

```json
{ "url": "https://example.com", "script": "document.title" }
```

### `GET /health`

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `3000` | Listen port |
| `USER_DATA_DIR` | `/data/profile` | Chrome profile, worth persisting |
| `MAX_CONCURRENT_PAGES` | `2` | Concurrent pages per container |
| `LOCALE` | `en-GB` | Browser locale |
| `TIMEZONE` | `Europe/London` | Browser timezone |

Mount at least 1GB at `/dev/shm`; Chrome is unhappy with the default 64MB.

## A note on what this is for

This exists to make a self-hosted scraper behave like the ordinary browser it
is. Plenty of sites deploy bot management in front of endpoints that carry real
consequences for other people, and defeating those is not what this is for.
Check what you are pointing it at.
