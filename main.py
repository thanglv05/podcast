from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Optional
import re
import asyncio
import os

app = FastAPI(
    title="LinkGrabber API",
    description="Extract and filter links from any URL",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Keep-alive (chống Render sleep) ───────────────────────────────────────────

async def _keep_alive_loop():
    await asyncio.sleep(60)
    self_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not self_url:
        return
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get(f"{self_url}/ping", timeout=10)
            except Exception:
                pass
            await asyncio.sleep(600)  # Ping mỗi 10 phút

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_keep_alive_loop())

# ─── Models ────────────────────────────────────────────────────────────────────

class LinkItem(BaseModel):
    href: str
    text: str
    title: Optional[str] = None
    rel: Optional[str] = None

class GrabResponse(BaseModel):
    url: str
    total: int
    filtered: int
    links: list[LinkItem]

# ─── Helper ────────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def extract_links(html: str, base_url: str) -> list[LinkItem]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()

    for tag in soup.find_all("a", href=True):
        raw = tag["href"].strip()
        if not raw or raw.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue

        # Resolve relative URLs
        full = urljoin(base_url, raw)

        # Deduplicate
        if full in seen:
            continue
        seen.add(full)

        links.append(LinkItem(
            href=full,
            text=" ".join(tag.get_text().split()) or "",
            title=tag.get("title") or None,
            rel=tag.get("rel", [None])[0] if tag.get("rel") else None,
        ))

    return links

def apply_filters(
    links: list[LinkItem],
    contains: Optional[str],
    starts_with: Optional[str],
    ends_with: Optional[str],
    domain: Optional[str],
    regex: Optional[str],
    link_type: Optional[str],
    exclude: Optional[str],
) -> list[LinkItem]:
    result = links

    if contains:
        result = [l for l in result if contains.lower() in l.href.lower()]
    if starts_with:
        result = [l for l in result if l.href.lower().startswith(starts_with.lower())]
    if ends_with:
        result = [l for l in result if l.href.lower().endswith(ends_with.lower())]
    if domain:
        result = [l for l in result if urlparse(l.href).netloc == domain.lower()]
    if regex:
        try:
            pat = re.compile(regex, re.IGNORECASE)
            result = [l for l in result if pat.search(l.href)]
        except re.error:
            raise HTTPException(status_code=400, detail=f"Invalid regex: {regex}")
    if link_type:
        lt = link_type.lower()
        if lt == "image":
            result = [l for l in result if re.search(r"\.(jpe?g|png|gif|webp|svg|bmp)(\?|$)", l.href, re.I)]
        elif lt == "document":
            result = [l for l in result if re.search(r"\.(pdf|docx?|xlsx?|pptx?|txt|csv)(\?|$)", l.href, re.I)]
        elif lt == "video":
            result = [l for l in result if re.search(r"\.(mp4|webm|mov|avi|mkv)(\?|$)", l.href, re.I)]
        elif lt == "audio":
            result = [l for l in result if re.search(r"\.(mp3|wav|ogg|flac|m4a)(\?|$)", l.href, re.I)]
        elif lt == "internal":
            base_domain = urlparse(links[0].href).netloc if links else ""
            result = [l for l in result if urlparse(l.href).netloc == base_domain]
        elif lt == "external":
            base_domain = urlparse(links[0].href).netloc if links else ""
            result = [l for l in result if urlparse(l.href).netloc != base_domain]
    if exclude:
        result = [l for l in result if exclude.lower() not in l.href.lower()]

    return result

# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "LinkGrabber API is running 🚀"}

@app.get("/ping", tags=["Health"])
def ping():
    return {"ping": "pong"}

@app.get("/grab", response_model=GrabResponse, tags=["Links"])
async def grab_links(
    url: str = Query(..., description="Target URL to extract links from"),
    contains: Optional[str] = Query(None, description="Only links containing this string"),
    starts_with: Optional[str] = Query(None, description="Only links starting with this string"),
    ends_with: Optional[str] = Query(None, description="Only links ending with this string"),
    domain: Optional[str] = Query(None, description="Only links from this exact domain (e.g. example.com)"),
    regex: Optional[str] = Query(None, description="Filter by regex pattern"),
    link_type: Optional[str] = Query(None, description="Filter by type: image | document | video | audio | internal | external"),
    exclude: Optional[str] = Query(None, description="Exclude links containing this string"),
    timeout: int = Query(15, ge=3, le=60, description="Request timeout in seconds"),
):
    """
    Fetch a URL and return all links found on the page.
    Apply one or more filters to narrow down results.
    """
    # Validate URL
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    # Fetch page
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url, headers=HEADERS)
            resp.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Request timed out after {timeout}s")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Extract
    all_links = extract_links(resp.text, str(resp.url))

    # Filter
    filtered = apply_filters(
        all_links, contains, starts_with, ends_with,
        domain, regex, link_type, exclude
    )

    return GrabResponse(
        url=url,
        total=len(all_links),
        filtered=len(filtered),
        links=filtered,
    )
