"""Under Armour parser — Playwright sitemap + PDP JSON-LD (EN+USD)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, Page

from config import cfg

logger = logging.getLogger(__name__)


def _stable_id(product_url: str) -> str:
    digest = hashlib.sha256(f"{cfg.SOURCE}:{product_url}".encode()).hexdigest()[:24]
    return f"underarmour_{digest}"


def _money(amount: Any, currency: str | None = None) -> Optional[str]:
    if amount is None or amount == "":
        return None
    currency = currency or cfg.CURRENCY
    try:
        val = float(amount)
    except (TypeError, ValueError):
        return None
    if val <= 0:
        return None
    return f"{val:.2f}{currency}"


def _infer_gender(title: str, category: str | None = None) -> str:
    blob = f"{title or ''} {category or ''}".lower()
    if re.search(r"\bwomens?\b|\bwoman\b|sports\s*bra", blob):
        return "Women"
    if re.search(r"\bmens?\b|\bman\b", blob):
        return "Men"
    if re.search(r"\bkids?\b|\byouth\b|\bboy|\bgirl", blob):
        return "Kids"
    return cfg.GENDER_DEFAULT


def _detect_back(images: list[str], front: str) -> Optional[str]:
    for src in images:
        if src == front:
            continue
        low = src.lower()
        if any(tok in low for tok in ("_bc", "_back", "-back", "_hb", "rear")):
            return src
    return None


async def _new_page(browser: Browser) -> Page:
    context = await browser.new_context(
        user_agent=cfg.USER_AGENT,
        locale="en-US",
        viewport={"width": 1400, "height": 900},
    )
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return await context.new_page()


async def fetch_product_urls(page: Page) -> list[str]:
    await page.goto(cfg.SITEMAP_PRODUCT, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(1500)
    content = await page.content()
    urls = re.findall(
        r"https://www\.underarmour\.com/en-us/p/[^\s<\"']+", content
    )
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        u = u.rstrip("]")
        if u not in seen:
            seen.add(u)
            out.append(u)
    logger.info("Sitemap product URLs: %d", len(out))
    return out


async def parse_pdp(page: Page, product_url: str) -> Optional[dict[str, Any]]:
    try:
        await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_selector('script[type="application/ld+json"]', state="attached", timeout=20000)
        await page.wait_for_timeout(400)
        data = await page.evaluate(
            """() => {
          const ld = [...document.querySelectorAll('script[type="application/ld+json"]')]
            .map(s => { try { return JSON.parse(s.textContent); } catch(e) { return null; } })
            .filter(Boolean);
          const pg = ld.find(x => x['@type'] === 'ProductGroup');
          if (!pg) return null;
          const offer = pg.offers || {};
          const variants = Array.isArray(pg.hasVariant) ? pg.hasVariant : [];
          const sizes = [...new Set(variants.map(v => v.size).filter(Boolean))];
          const colors = [...new Set(variants.map(v => v.color).filter(Boolean))];
          let sale = null;
          let price = offer.price;
          // If variants have different prices, keep offer price as list
          const imgs = Array.isArray(pg.image) ? pg.image : (pg.image ? [pg.image] : []);
          return {
            title: pg.alternateName || pg.name || document.title,
            name: pg.name || null,
            description: pg.description || null,
            url: pg['@id'] || location.href,
            images: imgs,
            price: price,
            currency: offer.priceCurrency || 'USD',
            availability: offer.availability || null,
            mpn: pg.mpn || null,
            sku: pg.sku || null,
            sizes, colors,
            brand: (pg.brand && pg.brand.name) || 'Under Armour',
            category: (variants[0] && variants[0].category) || null,
          };
        }"""
        )
    except Exception as e:
        logger.warning("PDP fail %s: %s", product_url, e)
        return None

    if not data or not data.get("images"):
        logger.warning("Skip %s: no JSON-LD ProductGroup/image", product_url)
        return None

    images = [i for i in (data.get("images") or []) if i]
    # Prefer pdp-sized front if present
    front = images[0]
    for img in images:
        if "pdp" in img and "_FC" in img:
            front = img
            break
    back = _detect_back(images, front)
    additional = [i for i in images[1:] if i != front]
    if back and back not in additional:
        additional.append(back)

    title = (data.get("title") or "Unknown").strip()
    gender = _infer_gender(title, data.get("category"))
    price = _money(data.get("price"), data.get("currency") or cfg.CURRENCY)
    category = data.get("category")
    # Normalize junk category labels
    if category and ("http" in category or len(category) > 80):
        category = None
    if not category:
        # derive from URL slug keywords
        slug = urlparse(product_url).path
        if "shoe" in slug:
            category = "Shoes"
        elif "bra" in slug:
            category = "Sports Bras"
        elif "legging" in slug:
            category = "Leggings"
        elif "short" in slug:
            category = "Shorts"
        elif "hoodie" in slug or "fleece" in slug:
            category = "Hoodies"
        elif "jogger" in slug or "pant" in slug:
            category = "Pants"
        elif "sock" in slug:
            category = "Socks"
        else:
            category = "Apparel"

    metadata = {
        "mpn": data.get("mpn"),
        "sku": data.get("sku"),
        "colors": data.get("colors"),
        "availability": data.get("availability"),
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "scrape_source": "pdp-jsonld",
        "locale": "en-us",
    }

    return {
        "id": _stable_id(product_url),
        "source": cfg.SOURCE,
        "product_url": product_url.split("?")[0],
        "affiliate_url": None,
        "image_url": front,
        "compressed_image_url": None,
        "back_image_url": back,
        "brand": cfg.BRAND_COLUMN,
        "title": title,
        "description": data.get("description"),
        "category": category,
        "gender": gender,
        "price": price,
        "sale": None,
        "metadata": json.dumps(metadata, ensure_ascii=False),
        "size": ", ".join(data.get("sizes") or []) or None,
        "second_hand": cfg.SECOND_HAND,
        "country": cfg.COUNTRY,
        "tags": None,
        "additional_images": " , ".join(additional) if additional else None,
        "other": None,
    }


async def _worker(browser: Browser, urls: list[str], results: list, sem: asyncio.Semaphore):
    page = await _new_page(browser)
    try:
        for u in urls:
            async with sem:
                parsed = await parse_pdp(page, u)
                if parsed:
                    results.append(parsed)
                await asyncio.sleep(cfg.RATE_LIMIT_DELAY)
    finally:
        await page.context.close()


async def scrape_all_async() -> list[dict[str, Any]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            boot = await _new_page(browser)
            # Warm homepage (helps with cookies / bot score)
            try:
                await boot.goto(cfg.LANDING_PAGE, wait_until="domcontentloaded", timeout=90000)
                await boot.wait_for_timeout(2000)
            except Exception as e:
                logger.warning("Homepage warm failed: %s", e)
            urls = await fetch_product_urls(boot)
            await boot.context.close()

            if cfg.MAX_PRODUCTS and cfg.MAX_PRODUCTS > 0:
                urls = urls[: cfg.MAX_PRODUCTS]

            n = max(1, cfg.PLAYWRIGHT_CONCURRENCY)
            chunks = [urls[i::n] for i in range(n)]
            results: list[dict[str, Any]] = []
            sem = asyncio.Semaphore(n)
            await asyncio.gather(
                *[_worker(browser, chunk, results, sem) for chunk in chunks if chunk]
            )
            # dedupe
            seen: set[str] = set()
            unique: list[dict[str, Any]] = []
            for r in results:
                if r["product_url"] in seen:
                    continue
                seen.add(r["product_url"])
                unique.append(r)
            logger.info("Scraped unique products: %d", len(unique))
            return unique
        finally:
            await browser.close()


def scrape_all_categories() -> list[dict[str, Any]]:
    return asyncio.run(scrape_all_async())
