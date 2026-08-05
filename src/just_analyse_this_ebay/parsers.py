import time
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlparse

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - exercised in environments without Playwright
    sync_playwright = None

BLOCKED_PAGE_MARKERS = (
    "browser check",
    "verify you are human",
    "verify you're a human",
    "security check",
    "request blocked",
)


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

        if any( marker in title for marker in BLOCKED_PAGE_MARKERS ):
            return False

    return True


def is_expected_product_page( url: str, page_title: str | None = None ) -> bool:
    parsed_url = urlparse( url )

    if parsed_url.netloc not in { "www.ebay.com", "ebay.com" }:
        return False

    if not parsed_url.path.startswith( "/itm/" ):
        return False

    if page_title is not None:
        title = page_title.lower()

        if any( marker in title for marker in BLOCKED_PAGE_MARKERS ):
            return False

    return True


def wait_for_expected_page(
    probe: Callable[[], tuple[str, str]],
    reload_page: Callable[[str], None],
    expected_url: str,
    keywords: str,
    *,
    page_validator: Callable[[str, str | None], bool] | None = None,
    page_description: str = "search page",
    max_attempts: int = 3,
    retry_delay_seconds: float = 3.0,
) -> None:
    last_error: RuntimeError | None = None
    validator = page_validator or ( lambda url, page_title: is_expected_search_page( url, keywords, page_title ) )

    for attempt in range( max_attempts ):
        current_url, page_title = probe()

        if validator( current_url, page_title ):
            return

        last_error = RuntimeError(
            f"Failed to open ebay { page_description } for "
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

    def stop( self ) -> None:
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

        self._ensure_expected_page( self.product_url )

        self.specifics_area   = self.page.locator( ".ux-layout-section-evo__item--description-list" )
        self.seller_area      = self.page.locator( ".x-store-information__header" )
        self.description_area = self.page.locator( ".d-item-description" )

    def _ensure_expected_page( self, expected_url: str ) -> None:
        wait_for_expected_page(
            probe = lambda: ( self.page.url, self.page.title() or "" ),
            reload_page = lambda url: self.page.goto(
                url,
                wait_until = "domcontentloaded",
                timeout = 30000
            ),
            expected_url = expected_url,
            keywords = "",
            page_validator = lambda url, page_title: is_expected_product_page( url, page_title ),
            page_description = "product page",
            max_attempts = 3,
            retry_delay_seconds = 3.0,
        )

    def parse_specifics_labels( self ):
        specifics_labels = []
        for label_element in self.specifics_area.locator( ".ux-labels-values__labels" ).all():
            label_text = label_element.inner_text()
            specifics_labels.append( label_text )

        return specifics_labels

    def parse_specifics_values( self ):
        specifics_values = []
        for value_element in self.specifics_area.locator( ".ux-labels-values__values" ).all():
            value_text = value_element.inner_text()
            specifics_values.append( value_text )

        return specifics_values

    def parse_description( self ):
        iframe = self.page.locator( "#desc_ifr" )
        iframe.wait_for( timeout = 10000 )

        frame = iframe.content_frame
        frame.locator( "body" ).wait_for( timeout = 10000 )

        return frame.locator( "body" ).inner_text()

    def parse_seller_name( self ):
        seller_name = self.seller_area.locator( ".ux-textspans--BOLD" )

        return seller_name.inner_text() if seller_name else ""

    def stop( self ) -> None:
        self.context.close()
        self.browser.close()
        self.playwright.stop()
        
