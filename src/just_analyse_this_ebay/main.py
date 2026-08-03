from just_analyse_this_ebay.parsers import SearchParser
import pandas as pd

def main():
    keywords = "laptop" # Example keyword for searching on eBay
    parser = SearchParser( keywords )

    titles = parser.parse_titles()
    prices = parser.parse_prices()
    urls   = parser.parse_urls()
    parser.stop()

    df = pd.DataFrame( {
            "Title": titles,
            "Price": prices,
            "URL": urls
        } )
    
    df.to_csv( "output/results.csv", index = False )

if __name__ == "__main__":
    main()