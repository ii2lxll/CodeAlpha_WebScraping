"""
CodeAlpha Data Analytics Internship - Task 1: Web Scraping
E-commerce Market & Competitor Analysis Dataset
Author: Abdullah Khaled Hasan Barabaa

Collects every product (laptops, tablets, phones) from an e-commerce test store
and saves a clean dataset to data/products.csv.
"""

import csv
import os
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
BASE_URL = "https://webscraper.io/test-sites/e-commerce/static/"

# (category, subcategory, page path on the site)
CATEGORIES = [
    ("Computers", "Laptops", "computers/laptops"),
    ("Computers", "Tablets", "computers/tablets"),
    ("Phones", "Touch Phones", "phones/touch"),
]

OUTPUT_FILE = "data/products.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (CodeAlpha internship scraper; educational use)"}
DELAY_SECONDS = 1  # wait between requests so we don't overload the website

# Some product names start with a model line instead of the brand
BRAND_ALIASES = {
    "hewlett": "HP", "hp": "HP", "packard": "HP", "pavilion": "HP", "probook": "HP",
    "aspire": "Acer", "iconia": "Acer",
    "inspiron": "Dell",
    "thinkpad": "Lenovo", "ideatab": "Lenovo",
    "vivobook": "Asus", "memo": "Asus",
    "galaxy": "Samsung",
    "iphone": "Apple", "ipad": "Apple", "macbook": "Apple",
    "kindle": "Amazon",
}

# Words that mean a memory size belongs to the graphics card, not RAM/storage
GPU_WORDS = re.compile(r"GeForce|Radeon|GTX|Quadro|Intel HD|Graphics", re.I)


# ---------------------------------------------------------------------------
# Step 1-2: download a page
# ---------------------------------------------------------------------------
def get_page(url):
    """Download a page and return it as a BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()  # stop with an error if status is not 200
    time.sleep(DELAY_SECONDS)
    return BeautifulSoup(response.text, "html.parser")


# ---------------------------------------------------------------------------
# Step 5: cleaning helpers
# ---------------------------------------------------------------------------
def clean_price(text):
    """'$1,399.00' -> 1399.0"""
    return float(text.replace("$", "").replace(",", "").strip())


def clean_reviews(text):
    """'14 reviews' -> 14"""
    return int(text.split()[0])


# ---------------------------------------------------------------------------
# Step 9: feature engineering (brand + specs)
# ---------------------------------------------------------------------------
def detect_brand(name):
    """'Aspire E1-510' -> 'Acer', 'Lenovo ThinkPad' -> 'Lenovo'"""
    first_word = name.split()[0].strip(",")
    return BRAND_ALIASES.get(first_word.lower(), first_word)


def detect_os(text):
    """Group operating-system spellings: 'Win7 Pro 64bit' -> 'Windows 7'"""
    windows = re.search(r"Win(?:dows)?\s?(10|8\.1|8|7)", text, re.I)
    if windows:
        return "Windows " + windows.group(1)
    os_patterns = [
        (r"No OS", "No OS"), (r"Endless", "Endless OS"), (r"FreeDOS|\bDOS\b", "FreeDOS"),
        (r"Linux", "Linux"), (r"Andr?oid", "Android"), (r"\biOS\b", "iOS"),
        (r"Chrome OS", "Chrome OS"), (r"Windows", "Windows"),
    ]
    for pattern, os_name in os_patterns:
        if re.search(pattern, text, re.I):
            return os_name
    return None


def parse_specs(description):
    """Turn a free-text description into structured columns, e.g.
    '15.6", Core i5-7200U, 8GB, 256GB SSD, Windows 10 Home'
    -> screen 15.6, cpu Core i5, ram 8, storage 256, type SSD, os Windows 10"""
    screen = re.search(r'(\d{1,2}(?:\.\d)?)\s*(?:"|”|inch)', description)
    cpu = re.search(r"(Core\s?i\d|Core\s?m\d|Celeron|Pentium|Atom|Ryzen\s?\d|AMD\s?[AE]\d+"
                    r"|A\d{1,2}-\d+|Snapdragon|Exynos|MediaTek)", description, re.I)

    # Collect every memory size in order, e.g. "8GB" and "256GB SSD",
    # skipping graphics-card memory and small SSD caches
    sizes = []
    for part in description.split(","):
        if GPU_WORDS.search(part):
            continue
        part = re.sub(r"\+\s*\d+\s*GB\s*SSD\s*Cache", "", part, flags=re.I)
        for number, unit, kind in re.findall(r"(\d+)\s*(GB|TB)\s*(SSD|HDD|SSHD|eMMC|Flash)?", part, re.I):
            size_gb = int(number) * (1024 if unit.upper() == "TB" else 1)
            sizes.append((size_gb, kind.upper() or None))

    # First small size without a type = RAM, the next size = storage
    ram_gb = storage_gb = storage_type = None
    for size_gb, kind in sizes:
        if ram_gb is None and kind is None and size_gb <= 64 and len(sizes) > 1:
            ram_gb = size_gb
        elif storage_gb is None:
            storage_gb, storage_type = size_gb, kind

    return {
        "screen_inch": float(screen.group(1)) if screen else None,
        "cpu": re.sub(r"\s+", " ", cpu.group(1)) if cpu else None,
        "ram_gb": ram_gb,
        "storage_gb": storage_gb,
        "storage_type": storage_type,
        "os": detect_os(description),
    }


# ---------------------------------------------------------------------------
# Step 3-4: extract every product card on one page
# ---------------------------------------------------------------------------
def parse_products(soup, page_url, category, subcategory):
    products = []
    for card in soup.select("div.thumbnail"):
        name = card.select_one("a.title")["title"].strip()
        description = card.select_one(".description").get_text(" ", strip=True)

        product = {
            "product_name": name,
            "brand": detect_brand(name),
            "category": category,
            "subcategory": subcategory,
            "price_usd": clean_price(card.select_one(".price").get_text()),
            "rating": int(card.select_one("[data-rating]")["data-rating"]),
            "review_count": clean_reviews(card.select_one(".review-count").get_text()),
        }
        product.update(parse_specs(description))  # add the spec columns
        product["description"] = description
        product["product_url"] = urljoin(page_url, card.select_one("a.title")["href"])
        products.append(product)
    return products


# ---------------------------------------------------------------------------
# Step 6: go through every page of a category
# ---------------------------------------------------------------------------
def scrape_category(category, subcategory, path):
    all_products = []
    seen_urls = set()
    page = 1

    while True:
        url = urljoin(BASE_URL, f"{path}?page={page}")
        products = parse_products(get_page(url), url, category, subcategory)

        # Stop when a page has no products we haven't already collected
        new_products = [p for p in products if p["product_url"] not in seen_urls]
        if not new_products:
            break

        for p in new_products:
            seen_urls.add(p["product_url"])
        all_products.extend(new_products)
        page += 1

    return all_products


# ---------------------------------------------------------------------------
# Step 8: save to CSV
# ---------------------------------------------------------------------------
def save_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Step 7: run everything
# ---------------------------------------------------------------------------
def main():
    start = time.time()
    all_products = []

    for category, subcategory, path in CATEGORIES:
        products = scrape_category(category, subcategory, path)
        all_products.extend(products)
        print(f"{category} > {subcategory}: {len(products)} products")

    save_csv(all_products, OUTPUT_FILE)
    brands = sorted({p["brand"] for p in all_products})
    print(f"\nSaved {len(all_products)} products to {OUTPUT_FILE}")
    print(f"Brands ({len(brands)}): {', '.join(brands)}")
    print(f"Done in {time.time() - start:.0f} seconds")


if __name__ == "__main__":
    main()
