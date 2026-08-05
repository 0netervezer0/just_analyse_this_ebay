from just_analyse_this_ebay.parsers import SearchParser, ProductParser
import pandas as pd

def main():
    # keywords = "laptop" # Example keyword for searching on eBay
    # s_parser = SearchParser( keywords )

    # titles = s_parser.parse_titles()
    # prices = s_parser.parse_prices()
    # urls   = s_parser.parse_urls()
    # s_parser.stop()

    # df = pd.DataFrame( {
    #         "Title": titles,
    #         "Price": prices,
    #         "URL": urls
    #     } )
    
    # df.to_csv( "output/results.csv", index = False )

    df_in = pd.read_csv( 'output/results.csv', encoding = 'utf-8' )
    url = df_in.iat[ 0, 2 ]

    p_parser = ProductParser( url )

    description = p_parser.parse_description()
    p_parser.stop()

    print( f"Description: { description }" )

if __name__ == "__main__":
    main()