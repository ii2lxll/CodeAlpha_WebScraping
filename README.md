# CodeAlpha – Task 1: Web Scraping 🛒
### E-commerce Market & Competitor Analysis Dataset

**Data Analytics Internship @ CodeAlpha** · 

A Python web scraper that collects the full product catalogue of an online electronics store and turns it into a **competitor-analysis dataset**: every brand is treated as a competitor and compared on price, customer rating, review volume and product specs.

The source is the [Web Scraper e-commerce test store](https://webscraper.io/test-sites/e-commerce/static), a realistic shop built for scraping practice. Major marketplaces such as Amazon prohibit automated scraping in their terms of service, so a scraping-permitted store keeps this project legal and reproducible while using the same techniques.

## Result
**147 products** from **15 competing brands** across 3 categories: Laptops (117), Tablets (21) and Touch Phones (9).

## What the scraper does
- Crawls 3 categories and handles pagination automatically, stopping when a page adds no new products
- Extracts name, price, star rating, review count and product link
- Cleans values during extraction (`$1,399.00` → `1399.0`, `14 reviews` → `14`)
- **Feature engineering:** detects each product's brand (e.g. "Aspire" → Acer) and uses regex to turn free-text descriptions into screen size, CPU, RAM, storage and operating system
- Polite crawling: 1 s delay between requests, a clear User-Agent, timeouts and status-code checks

## Business questions this dataset answers
- Which brands dominate each category?
- How is each competitor positioned on price: budget, mid-range or premium?
- Which specs drive price differences?
- Do more expensive products earn better ratings?

## Tech stack
Python · Requests · BeautifulSoup4 · Regex · CSV

## How to run
```bash
pip install -r requirements.txt
python scraper.py
```
Output: `data/products.csv`

## How the code works
| Step | Function | What it does |
|---|---|---|
| Download | `get_page` | Requests a page and parses it with BeautifulSoup |
| Extract | `parse_products` | Reads every product card on a page |
| Clean | `clean_price`, `clean_reviews` | Turns text into numbers |
| Paginate | `scrape_category` | Visits page 1, 2, 3… until no new products appear |
| Enrich | `detect_brand`, `parse_specs` | Derives brand and specs from text |
| Save | `save_csv` | Writes the dataset to CSV |