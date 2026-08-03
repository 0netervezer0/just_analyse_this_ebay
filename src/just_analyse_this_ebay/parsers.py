import time
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlparse

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - exercised in environments without Playwright
    sync_playwright = None

def is_expected_search_page( url: str, keywords: str, page_title: str | None = None ) -> bool:
    parsed_url = urlparse( url )

    if parsed_url.netloc not in { "www.ebay.com", "ebay.com" }:
        return False

    if parsed_url.path not in { "/sch/i.html", "/sch/i.html/" }:
        return False

    params = parse_qs( parsed_url.query )
    expected_keywords = params.get( "_nkw", [] )

    if not bool( expected_keywords ) or expected_keywords[ 0 ] != keywords:
        return False

    if page_title is not None:
        title = page_title.lower()
        blocked_markers = (
            "browser check",
            "verify you are human",
            "verify you're a human",
            "security check",
            "request blocked",
        )

        if any( marker in title for marker in blocked_markers ):
            return False

    return True


def wait_for_expected_page(
    probe: Callable[[], tuple[str, str]],
    reload_page: Callable[[str], None],
    expected_url: str,
    keywords: str,
    *,
    max_attempts: int = 3,
    retry_delay_seconds: float = 3.0,
) -> None:
    last_error: RuntimeError | None = None

    for attempt in range( max_attempts ):
        current_url, page_title = probe()

        if is_expected_search_page( current_url, keywords, page_title ):
            return

        last_error = RuntimeError(
            "Failed to open ebay search page for "
            f"'{ keywords }', but got '{ current_url }'"
            f" (title: { page_title })"
        )

        if attempt < max_attempts - 1:
            if retry_delay_seconds > 0:
                time.sleep( retry_delay_seconds )
            reload_page( expected_url )

    if last_error is not None:
        raise last_error


def parse_urls_from_cards( cards: list[ object ] ) -> list[ str ]:
    urls: list[ str ] = []

    for card in cards:
        title_element = card.query_selector( ".s-card__title" )
        price_element = card.query_selector( ".s-card__price" )

        if title_element is None or price_element is None:
            continue

        title_text = title_element.inner_text().strip()
        suffix = "Opens in a new window or tab"

        if title_text.endswith( suffix ):
            title_text = title_text[: title_text.rfind( suffix ) ].rstrip()

        if title_text in { "Shop on eBay", "to" }:
            continue

        link_element = card.query_selector( ".s-card__link" )
        if link_element is None:
            continue

        href = link_element.get_attribute( "href" )
        if href:
            urls.append( href )

    return urls


def parse_result_rows( 
        cards: list[ object ], blocked_markers: tuple[str, ...]
    ) -> list[ tuple[str, str] ]:
    rows: list[ tuple[str, str] ] = []

    for card in cards:
        title_element = card.query_selector( ".s-card__title" )
        price_element = card.query_selector( ".s-card__price" )

        if title_element is None or price_element is None:
            continue

        title_text = title_element.inner_text().strip()
        suffix = "Opens in a new window or tab"

        if title_text.endswith( suffix ):
            title_text = title_text[: title_text.rfind( suffix ) ].rstrip()

        if title_text in blocked_markers:
            continue

        price_text = price_element.inner_text().strip()
        if price_text in blocked_markers:
            continue

        rows.append( ( title_text, price_text ) )

    return rows


class SearchParser:
    def __init__( self, keywords: str ):
        if sync_playwright is None:
            raise RuntimeError( 
                "Playwright is not installed. Please install dependencies before running SearchParser." 
            )

        self.keywords = keywords
        self._result_rows: list[ tuple[str, str] ] | None = None

        self.blocked_markers = (
            "Shop on eBay",
            "to"
        )

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch( headless = False )
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

        expected_url = f"https://www.ebay.com/sch/i.html?{ urlencode( { '_nkw': self.keywords } ) }"

        self.page.goto(
            expected_url,
            wait_until = "domcontentloaded",
            timeout = 30000
        )

        self._ensure_expected_page( expected_url )

    def _ensure_expected_page( self, expected_url: str ) -> None:
        wait_for_expected_page(
            probe = lambda: ( self.page.url, self.page.title() or "" ),
            reload_page = lambda url: self.page.goto(
                url,
                wait_until = "domcontentloaded",
                timeout = 30000
            ),
            expected_url = expected_url,
            keywords = self.keywords,
            max_attempts = 3,
            retry_delay_seconds = 3.0,
        )

    def _get_result_rows( self ) -> list[ tuple[str, str] ]:
        if self._result_rows is None:
            self._result_rows = parse_result_rows( 
                self.page.query_selector_all( ".s-card" ), self.blocked_markers 
            )

        return self._result_rows

    def parse_urls( self ):
        self.url_list = parse_urls_from_cards( self.page.query_selector_all( ".s-card" ) )
        return self.url_list

    def parse_titles( self ):
        rows = self._get_result_rows()
        self.title_list = [ title for title, _ in rows ]
        return self.title_list

    def parse_prices( self ):
        rows = self._get_result_rows()
        self.price_list = [ price for _, price in rows ]
        return self.price_list

    def stop( self ):
        self.context.close()
        self.browser.close()
        self.playwright.stop()


class ProductParser:
    def __init__( self, product_url: str ):
        if sync_playwright is None:
            raise RuntimeError( 
                "Playwright is not installed. Please install dependencies before running ProductParser." 
            )

        self.product_url = product_url
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch( headless = False )
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

        self.page.goto(
            self.product_url,
            wait_until = "domcontentloaded",
            timeout = 30000
        )

    def stop( self ):
        self.context.close()
        self.browser.close()
        self.playwright.stop()
        