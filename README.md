# Under Armour Product Scraper

Production Finds scraper for [Under Armour](https://www.underarmour.com/en-us/).

- Source: `scraper-underarmour`
- Schedule: `7 18 * * 1,3,5` UTC
- Currency: USD (EN+US). EUR `/en-eu/` redirects / GraphQL requires signed requests.
- Approach: Playwright sitemap (`sitemap_0-product.xml`) + PDP JSON-LD ProductGroup
- Curl gets HTTP 418; no password wall
- Embeddings: local SigLIP `google/siglip-base-patch16-384`
- Secrets: `SUPABASE_URL`, `SUPABASE_KEY`
- Upsert batch size: 5; never sends `embedding_version`
