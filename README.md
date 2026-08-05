# just-analyse-this-ebay

just-analyse-this-ebay is a lightweight Python library for automating browser-based extraction from eBay search and product pages. It combines Playwright for browser control with a small set of parser classes that expose a simple, explicit API for collecting structured data.

The library is designed for clarity and maintainability rather than for building a general-purpose scraping platform. Its primary purpose is to make it easy to:

- open an eBay search page and extract result cards;
- collect titles, prices, and links from search results;
- open an individual product page and extract description, seller, and item-specific details.

The code is organized around two main parser classes:

- SearchParser for search result pages;
- ProductParser for individual product listing pages.

Each class manages its own Playwright browser session, exposes a focused API, and includes safeguards for common eBay verification pages.

---

## Installation

### Requirements

- Python 3.12 or newer
- Playwright
- Chromium browser binaries

### Install the package

From the repository root:

```bash
python -m pip install -e .
```

### Install Playwright browser binaries

```bash
python -m playwright install chromium
```

If you prefer uv, use:

```bash
uv sync
uv run python -m playwright install chromium
```

---

## Quick start

### Search results

```python
from just_analyse_this_ebay.parsers import SearchParser

parser = SearchParser("laptop")

try:
    titles = parser.parse_titles()
    prices = parser.parse_prices()
    urls = parser.parse_urls()
finally:
    parser.stop()
```

### Product page

```python
from just_analyse_this_ebay.parsers import ProductParser

parser = ProductParser("https://www.ebay.com/itm/123456789")

try:
    description = parser.parse_description()
    seller_name = parser.parse_seller_name()
    specifics_labels = parser.parse_specifics_labels()
    specifics_values = parser.parse_specifics_values()
finally:
    parser.stop()
```

The lifecycle is consistent across both parsers:

1. instantiate the parser;
2. call the desired parsing method or methods;
3. call stop() to release browser resources.

---

## API reference

The public API is intentionally compact and centered in the parsers module.

### Functional helpers

| Name | Description |
| --- | --- |
| [is_expected_search_page](#is_expected_search_pageurl-keywords-page_titlenone) | Validates that the current page is an eBay search results page for the expected keyword. |
| [is_expected_product_page](#is_expected_product_pageurl-page_titlenone) | Validates that the current page is an eBay product page. |
| [wait_for_expected_page](#wait_for_expected_page) | Retries page loading until the expected page appears or the allowed attempts are exhausted. |
| [parse_result_rows](#parse_result_rowscards-blocked_markers) | Converts parsed card-like objects into `(title, price)` rows. |
| [parse_urls_from_cards](#parse_urls_from_cardscards) | Extracts product URLs from card-like objects. |

#### is_expected_search_page(url, keywords, page_title=None)

Validates that the given URL is an eBay search results page and that the query keyword matches the expected term.

```python
from just_analyse_this_ebay.parsers import is_expected_search_page

is_expected_search_page(
    "https://www.ebay.com/sch/i.html?_nkw=laptop",
    "laptop",
    "laptop | eBay",
)
```

Returns `True` when all of the following hold:

- the URL belongs to eBay;
- the path is an eBay search results view;
- the `_nkw` query parameter matches the requested keyword;
- the page title is not a blocked verification page.

#### is_expected_product_page(url, page_title=None)

Validates that the given URL looks like a normal eBay product page.

```python
from just_analyse_this_ebay.parsers import is_expected_product_page

is_expected_product_page(
    "https://www.ebay.com/itm/123456789",
    "iPhone case | eBay",
)
```

Returns `True` when:

- the URL belongs to eBay;
- the URL path is a product page path starting with `/itm/`;
- the page title is not one of the known blocked verification pages.

#### wait_for_expected_page(...)

Retries the page-opening flow until the expected page is reached or the maximum number of attempts is exhausted.

```python
from just_analyse_this_ebay.parsers import wait_for_expected_page

wait_for_expected_page(
    probe=lambda: ("https://www.ebay.com/sch/i.html?_nkw=laptop", "Laptop"),
    reload_page=lambda url: None,
    expected_url="https://www.ebay.com/sch/i.html?_nkw=laptop",
    keywords="laptop",
    max_attempts=3,
    retry_delay_seconds=0.0,
)
```

This helper is used internally by both parser classes to recover from temporary verification pages and redirects.

#### parse_result_rows(cards, blocked_markers)

Parses a list of card-like objects into `(title, price)` rows.

```python
from just_analyse_this_ebay.parsers import parse_result_rows

rows = parse_result_rows(cards, ("Shop on eBay", "to"))
```

Each card is expected to expose `.query_selector()` plus title and price elements.

#### parse_urls_from_cards(cards)

Extracts product URLs from a list of card-like objects.

```python
from just_analyse_this_ebay.parsers import parse_urls_from_cards

urls = parse_urls_from_cards(cards)
```

Returns a list of product links discovered in the cards.

---

## SearchParser

SearchParser opens an eBay search results page, waits for the expected search view, and extracts data from the visible result cards.

### Constructor

```python
SearchParser(keywords: str)
```

Parameters:

- keywords: the search term used to build the eBay search URL.

Behavior:

- starts a Playwright browser session;
- opens a browser page;
- navigates to the generated eBay search URL;
- verifies that the page is the expected search results page;
- retries if the page appears to be a verification or anti-bot page.

### Methods

| Method | Description |
| --- | --- |
| [SearchParser.parse_titles](#searchparserparse_titles) | Returns the titles from the parsed result cards. |
| [SearchParser.parse_prices](#searchparserparse_prices) | Returns the prices from the parsed result cards. |
| [SearchParser.parse_urls](#searchparserparse_urls) | Returns the product URLs from the parsed result cards. |
| [SearchParser.stop](#searchparserstop) | Closes the browser session and releases resources. |

#### SearchParser.parse_titles()

```python
from just_analyse_this_ebay.parsers import SearchParser

parser = SearchParser("camera")
try:
    titles = parser.parse_titles()
    print(titles)
finally:
    parser.stop()
```

Returns a list of titles extracted from the parsed result cards.

#### SearchParser.parse_prices()

```python
from just_analyse_this_ebay.parsers import SearchParser

parser = SearchParser("camera")
try:
    prices = parser.parse_prices()
    print(prices)
finally:
    parser.stop()
```

Returns a list of prices extracted from the parsed result cards.

#### SearchParser.parse_urls()

```python
from just_analyse_this_ebay.parsers import SearchParser

parser = SearchParser("camera")
try:
    urls = parser.parse_urls()
    print(urls)
finally:
    parser.stop()
```

Returns a list of product URLs extracted from the parsed result cards.

#### SearchParser.stop()

```python
from just_analyse_this_ebay.parsers import SearchParser

parser = SearchParser("camera")
try:
    parser.parse_titles()
finally:
    parser.stop()
```

Closes the browser context, browser instance, and Playwright session.

---

## ProductParser

ProductParser opens an individual eBay product page and extracts structured information from the page.

### Constructor

```python
ProductParser(product_url: str)
```

Parameters:

- product_url: the full URL of the eBay listing to inspect.

Behavior:

- starts a Playwright browser session;
- opens a new page;
- navigates to the target product URL;
- verifies that the page is a real product page rather than a verification or blocked page;
- prepares locators for the product details and description areas.

### Methods

| Method | Description |
| --- | --- |
| [ProductParser.parse_specifics_labels](#productparserparse_specifics_labels) | Returns the labels from the item-specifics section. |
| [ProductParser.parse_specifics_values](#productparserparse_specifics_values) | Returns the values from the item-specifics section. |
| [ProductParser.parse_description](#productparserparse_description) | Returns the visible text of the item description. |
| [ProductParser.parse_seller_name](#productparserparse_seller_name) | Returns the seller name shown on the listing page. |
| [ProductParser.stop](#productparserstop) | Closes the browser session and releases resources. |

#### ProductParser.parse_specifics_labels()

```python
from just_analyse_this_ebay.parsers import ProductParser

parser = ProductParser("https://www.ebay.com/itm/123456789")
try:
    labels = parser.parse_specifics_labels()
    print(labels)
finally:
    parser.stop()
```

Returns a list of labels from the item-specifics section of the product page.

#### ProductParser.parse_specifics_values()

```python
from just_analyse_this_ebay.parsers import ProductParser

parser = ProductParser("https://www.ebay.com/itm/123456789")
try:
    values = parser.parse_specifics_values()
    print(values)
finally:
    parser.stop()
```

Returns a list of values from the item-specifics section of the product page.

#### ProductParser.parse_description()

```python
from just_analyse_this_ebay.parsers import ProductParser

parser = ProductParser("https://www.ebay.com/itm/123456789")
try:
    description = parser.parse_description()
    print(description)
finally:
    parser.stop()
```

Returns the visible text of the item description. The method waits for the product description iframe and reads the body content once the frame is ready.

#### ProductParser.parse_seller_name()

```python
from just_analyse_this_ebay.parsers import ProductParser

parser = ProductParser("https://www.ebay.com/itm/123456789")
try:
    seller_name = parser.parse_seller_name()
    print(seller_name)
finally:
    parser.stop()
```

Returns the seller name shown on the listing page if it is available.

#### ProductParser.stop()

```python
from just_analyse_this_ebay.parsers import ProductParser

parser = ProductParser("https://www.ebay.com/itm/123456789")
try:
    parser.parse_description()
finally:
    parser.stop()
```

Closes the browser context, browser instance, and Playwright session.

---

## Verification and retries

Both parser classes include a small retry mechanism designed to handle eBay verification pages and transient redirects.

When the target page is opened, the parser checks whether it is the expected page. If the page title matches one of the known blocked markers, for example:

- Browser Check
- Verify you are human
- Security check
- Request blocked

then the parser retries the navigation after a short delay. This behavior is implemented by the helper function wait_for_expected_page(...).

---

## Testing

The project includes a focused test suite covering the core behavior of the parser helpers.

Run the tests with:

```bash
pytest -q src/tests/test_parsers.py
```

The tests cover:

- search-page validation;
- product-page validation;
- result-row parsing;
- URL extraction from cards;
- retry behavior for page waiting.

---

## Notes and limitations

This library is intentionally small and is best suited for lightweight, educational, and personal use cases.

Important limitations:

- eBay page layouts can change over time;
- selectors may become outdated when the site changes its markup;
- anti-bot protections may still interrupt automation;
- the parser relies on the current DOM structure and may need updating when eBay changes the page HTML.

The library is not intended to be a full-scale scraping framework. Its goal is to provide a clear, readable, and maintainable way to extract common eBay data points with Playwright.

### Example: parse description

```python
from just_analyse_this_ebay.parsers import ProductParser

parser = ProductParser("https://www.ebay.com/itm/123456789")
try:
    description = parser.parse_description()
    print(description)
finally:
    parser.stop()
```

### Example: parse seller name

```python
from just_analyse_this_ebay.parsers import ProductParser

parser = ProductParser("https://www.ebay.com/itm/123456789")
try:
    seller_name = parser.parse_seller_name()
    print(seller_name)
finally:
    parser.stop()
```

### Method reference

#### parse_specifics_labels()

Returns a list of labels from the item-specifics section of the product page.

#### parse_specifics_values()

Returns a list of values from the item-specifics section of the product page.

#### parse_description()

Returns the visible text of the item description. The method waits for the product description iframe and reads the body content once the frame is ready.

#### parse_seller_name()

Returns the seller name shown on the listing page if it is available.

#### stop()

Closes the browser context and Playwright session.

---

## How verification handling works

Both parser classes include a small retry mechanism designed to handle eBay verification pages and transient redirects.

When the target page is opened, the parser checks whether it is the expected page. If the page title matches one of the known blocked markers, for example:

- Browser Check
- Verify you are human
- Security check
- Request blocked

then the parser retries the navigation after a short delay. This behavior is implemented by the helper function wait_for_expected_page(...).

---

## Testing

The project includes a small test suite covering the core behavior of the parser helpers.

Run the tests with:

```bash
pytest -q src/tests/test_parsers.py
```

The tests cover:

- search-page validation;
- product-page validation;
- result-row parsing;
- URL extraction from cards;
- retry behavior for page waiting.

---

## Notes and limitations

This library is intentionally small and is best suited for lightweight, educational, and personal use cases.

Important limitations:

- eBay page layouts can change over time;
- selectors may become outdated when the site changes its markup;
- anti-bot protections may still interrupt automation;
- the parser relies on the current DOM structure and may need updating when eBay changes the page HTML.

The library is not intended to be a full-scale scraping framework. Its goal is to provide a clear, readable, and maintainable way to extract common eBay data points with Playwright.
