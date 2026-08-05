import pytest

from just_analyse_this_ebay.parsers import (
    is_expected_product_page,
    is_expected_search_page,
    parse_result_rows,
    wait_for_expected_page,
)


def test_accepts_matching_ebay_search_url():
    assert is_expected_search_page(
        "https://www.ebay.com/sch/i.html?_nkw=iphone",
        "iphone",
    )


def test_rejects_non_search_or_wrong_page():
    assert not is_expected_search_page(
        "https://www.ebay.com/help/buying/" ,
        "iphone",
    )
    assert not is_expected_search_page(
        "https://www.ebay.com/sch/i.html?_nkw=ipad",
        "iphone",
    )


def test_rejects_browser_check_page():
    assert not is_expected_search_page(
        "https://www.ebay.com/sch/i.html?_nkw=iphone",
        "iphone",
        "Browser Check",
    )


def test_accepts_matching_ebay_product_page():
    assert is_expected_product_page(
        "https://www.ebay.com/itm/iphone-case/123456789",
        "iPhone Case",
    )


def test_rejects_browser_check_page_for_product_pages():
    assert not is_expected_product_page(
        "https://www.ebay.com/itm/iphone-case/123456789",
        "Browser Check",
    )


def test_result_rows_are_paired_by_card():
    class FakeElement:
        def __init__( self, text: str ):
            self.text = text

        def inner_text( self ) -> str:
            return self.text

    class FakeCard:
        def __init__( self, title: str, price: str ):
            self.title_element = FakeElement( title )
            self.price_element = FakeElement( price )

        def query_selector( self, selector: str ):
            if selector == ".s-card__title":
                return self.title_element
            if selector == ".s-card__price":
                return self.price_element
            return None

    cards = [
        FakeCard( "Alpha", "$10" ),
        FakeCard( "Beta Opens in a new window or tab", "$20" ),
        FakeCard( "Gamma", "$30" ),
    ]

    rows = parse_result_rows( cards, ( "Shop on eBay", "to" ) )

    assert rows == [ ( "Alpha", "$10" ), ( "Beta", "$20" ), ( "Gamma", "$30" ) ]


def test_parse_urls_collects_product_links():
    class FakeLinkElement:
        def __init__( self, href: str ):
            self.href = href

        def get_attribute( self, name: str ):
            if name == "href":
                return self.href
            return None

    class FakeCard:
        def __init__( self, href: str ):
            self.link_element = FakeLinkElement( href )
            self.title_element = type( "FakeTitle", (), { "inner_text": lambda self: "Example title" } )()
            self.price_element = type( "FakePrice", (), { "inner_text": lambda self: "$10" } )()

        def query_selector( self, selector: str ):
            if selector == ".s-card__title":
                return self.title_element
            if selector == ".s-card__price":
                return self.price_element
            if selector == ".s-card__link":
                return self.link_element
            return None

    cards = [
        FakeCard( "https://www.ebay.com/itm/1" ),
        FakeCard( "https://www.ebay.com/itm/2" ),
    ]

    from just_analyse_this_ebay.parsers import parse_urls_from_cards

    assert parse_urls_from_cards( cards ) == [
        "https://www.ebay.com/itm/1",
        "https://www.ebay.com/itm/2",
    ]


def test_wait_for_expected_page_retries_and_succeeds():
    attempts = { "count": 0 }

    def probe():
        attempts["count"] += 1
        if attempts["count"] < 3:
            return "https://www.ebay.com/help/buying/", "Help"
        return "https://www.ebay.com/sch/i.html?_nkw=iphone", "iPhone"

    reloaded = { "count": 0 }

    def reload_page( url ):
        reloaded["count"] += 1

    wait_for_expected_page(
        probe = probe,
        reload_page = reload_page,
        expected_url = "https://www.ebay.com/sch/i.html?_nkw=iphone",
        keywords = "iphone",
        max_attempts = 3,
        retry_delay_seconds = 0.0,
    )

    assert attempts["count"] == 3
    assert reloaded["count"] == 2


def test_wait_for_expected_page_reports_page_type_in_error_message():
    def probe():
        return "https://www.ebay.com/itm/iphone-case/123456789", "Browser Check"

    def reload_page( url ):
        return None

    with pytest.raises( RuntimeError ) as exc_info:
        wait_for_expected_page(
            probe = probe,
            reload_page = reload_page,
            expected_url = "https://www.ebay.com/itm/iphone-case/123456789",
            keywords = "",
            page_validator = lambda url, page_title: is_expected_product_page( url, page_title ),
            page_description = "product page",
            max_attempts = 1,
            retry_delay_seconds = 0.0,
        )

    message = str( exc_info.value )
    assert "product page" in message
    assert "search page" not in message
