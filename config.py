"""Under Armour scraper configuration — EN+USD via Playwright sitemap + PDP JSON-LD."""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    BRAND_NAME: str = "Under Armour"
    SOURCE: str = "scraper-underarmour"
    BRAND_COLUMN: str = "Under Armour"
    SECOND_HAND: bool = False
    LANDING_PAGE: str = "https://www.underarmour.com/en-us/"
    BASE_URL: str = "https://www.underarmour.com"
    LOCALE_PATH: str = "/en-us"
    CURRENCY: str = "USD"
    COUNTRY: str = "US"
    SITEMAP_PRODUCT: str = "https://www.underarmour.com/en-us/sitemap_0-product.xml"

    CATEGORY_URLS: list[str] = field(default_factory=lambda: [
        "https://www.underarmour.com/en-us/c/mens-tops/",
        "https://www.underarmour.com/en-us/c/mens-shorts/",
        "https://www.underarmour.com/en-us/c/mens-pants/",
        "https://www.underarmour.com/en-us/c/mens-hoodies-and-sweatshirts/",
        "https://www.underarmour.com/en-us/c/womens-tops/",
        "https://www.underarmour.com/en-us/c/womens-leggings/",
        "https://www.underarmour.com/en-us/c/womens-shorts/",
        "https://www.underarmour.com/en-us/c/womens-sports-bras/",
        "https://www.underarmour.com/en-us/c/shoes/",
        "https://www.underarmour.com/en-us/c/accessories/",
    ])

    SUPABASE_URL: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    SUPABASE_KEY: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))

    EMBEDDING_MODEL: str = "google/siglip-base-patch16-384"
    EMBEDDING_DIM: int = 768
    EMBEDDING_VERSION: int = 2
    RATE_LIMIT_DELAY: float = 0.4
    BATCH_SIZE: int = 5
    STALE_MISS_THRESHOLD: int = 2
    REQUEST_TIMEOUT: int = 45
    PLAYWRIGHT_CONCURRENCY: int = 4
    MAX_PRODUCTS: int = 0  # 0 = all
    USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    GENDER_DEFAULT: str = "Unisex"


cfg = Config()
