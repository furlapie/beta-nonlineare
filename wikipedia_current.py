import requests
import pandas as pd
from io import StringIO

def scrape_sp500_wikipedia():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/129.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Wrap the HTML string in a StringIO object
        tables = pd.read_html(StringIO(response.text))
        df = tables[0]
        return df

    except Exception as e:
        print(f"Error scraping Wikipedia: {e}")
        return None

def main():
    print("Scraping full S&P 500 table from Wikipedia...")

    df = scrape_sp500_wikipedia()

    if df is not None:
        print(f"Successfully scraped {len(df)} rows with {len(df.columns)} columns")
        print("\nFirst 10 rows:")
        print(df.head(10))

        # Save the full table as-is
        df.to_csv("wikipedia_current.csv", index=False)
        print("\nData saved to 'wikipedia_current.csv'")

        return df
    else:
        print("Failed to scrape S&P 500 data")
        return None


if __name__ == "__main__":
    main()