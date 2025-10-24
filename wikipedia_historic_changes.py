import requests
import pandas as pd
from bs4 import BeautifulSoup
import yfinance as yf
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_historic_sectors():
    """Load previously found sectors from CSV."""
    try:
        historic_df = pd.read_csv("wiki_yf_chat_historic_sectors.csv")
        return dict(zip(historic_df['Ticker'], historic_df['Sector']))
    except Exception as e:
        logger.warning(f"Could not load historic sectors: {e}")
        return {}

def get_sector(ticker, historic_sectors):
    """Get sector information from historic data first, then YFinance."""
    # Check historic sectors first
    if ticker in historic_sectors and historic_sectors[ticker]:
        return historic_sectors[ticker]
    
    # If not found, try YFinance
    try:
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "")
        if sector:
            return sector
    except Exception as e:
        logger.debug(f"YFinance error for {ticker}: {str(e)}")
    
    logger.warning(f"No sector found for {ticker}")
    return ""

def scrape_sp500_current():
    """Scrape la prima tabella con i 500 attuali, per mappare ticker→settore."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, "html.parser")
    tables = soup.find_all("table", {"class": "wikitable"})
    if not tables:
        raise RuntimeError("Non trovo la tabella principale degli S&P 500")
    
    table = tables[0]  # prima tabella
    rows = table.find_all("tr")
    
    sector_map = {}
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        ticker = cells[0].get_text(strip=True)
        sector = cells[2].get_text(strip=True)
        ticker = re.sub(r"[^\w.]", "", ticker)  # pulizia simbolo
        sector_map[ticker] = sector
    
    return sector_map

def scrape_sp500_changes(historic_sectors):
    """Scrape la seconda tabella (storico cambi) e aggiungi i settori."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, "html.parser")
    tables = soup.find_all("table", {"class": "wikitable"})
    if len(tables) < 2:
        raise RuntimeError("Non trovo la seconda tabella (storico cambi)")
    
    table = tables[1]
    rows = table.find_all("tr")
    
    data = []
    missing_sectors = set()  # Track tickers with missing sectors
    
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 6:
            continue
        
        date = cells[0].get_text(strip=True)
        added_ticker = cells[1].get_text(strip=True)
        added_company = cells[2].get_text(strip=True)
        removed_ticker = cells[3].get_text(strip=True)
        removed_company = cells[4].get_text(strip=True)
        reason = cells[5].get_text(" ", strip=True)

        # Clean reason row from citations
        reason = re.sub(r"\[ \d+\ ]", "", reason).strip()
        
        # Try to get sectors from historic data first
        added_sector = historic_sectors.get(added_ticker, "") if added_ticker else ""
        removed_sector = historic_sectors.get(removed_ticker, "") if removed_ticker else ""
        
        # Track missing sectors only if ticker exists
        if added_ticker and not added_sector:
            missing_sectors.add(added_ticker)
        if removed_ticker and not removed_sector:
            missing_sectors.add(removed_ticker)
        
        data.append({
            "Date": date,
            "Added Ticker": added_ticker,
            "Added Company": added_company,
            "Added Sector": added_sector,
            "Removed Ticker": removed_ticker,
            "Removed Company": removed_company,
            "Removed Sector": removed_sector,
            "Reason": reason
        })
    
    df = pd.DataFrame(data)
    
    # Only if we have missing sectors, try Wikipedia table 1
    if missing_sectors:
        print(f"Cercando {len(missing_sectors)} settori mancanti nella tabella 1 di Wikipedia...")
        sector_map = scrape_sp500_current()
        
        # Update missing sectors
        for ticker in missing_sectors:
            sector = sector_map.get(ticker, "")
            if sector:
                mask_added = df['Added Ticker'] == ticker
                mask_removed = df['Removed Ticker'] == ticker
                df.loc[mask_added, 'Added Sector'] = sector
                df.loc[mask_removed, 'Removed Sector'] = sector
    
    # Convert dates to dd/mm/yyyy
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")
    
    return df

def main():
    # Setup display Pandas
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    
    # Load historic sectors
    historic_sectors = load_historic_sectors()
    print(f"Settori storici caricati: {len(historic_sectors)}")
    
    # Scraping storico cambi (now only uses historic sectors first)
    df = scrape_sp500_changes(historic_sectors)
    
    # Update historic sectors with new findings
    new_sectors = {}
    for _, row in df.iterrows():
        if row['Added Ticker'] and row['Added Sector']:
            new_sectors[row['Added Ticker']] = row['Added Sector']
        if row['Removed Ticker'] and row['Removed Sector']:
            new_sectors[row['Removed Ticker']] = row['Removed Sector']
    
    # Combine with existing historic sectors and save
    historic_sectors.update(new_sectors)
    pd.DataFrame({
        'Ticker': list(historic_sectors.keys()),
        'Sector': list(historic_sectors.values())
    }).to_csv("wiki_yf_chat_historic_sectors.csv", index=False)
    
    # Save changes data
    df.to_csv("wikipedia_historic_changes.csv", index=False)
    print("Dati salvati in wikipedia_historic_changes.csv")
    print(df.head(20))

    # Modifica il conteggio per escludere le celle vuote legittime
    added_missing = df[
        (df['Added Ticker'].notna()) &  # c'è un ticker
        (df['Added Ticker'] != '') &    # il ticker non è vuoto
        (df['Added Sector'].str.len().eq(0))  # settore mancante
    ].shape[0]

    removed_missing = df[
        (df['Removed Ticker'].notna()) &  # c'è un ticker
        (df['Removed Ticker'] != '') &    # il ticker non è vuoto
        (df['Removed Sector'].str.len().eq(0))  # settore mancante
    ].shape[0]
    
    print(f"\nTotale cambi registrati: {len(df)}")
    print(f"Added tickers senza settore: {added_missing}")
    print(f"Removed tickers senza settore: {removed_missing}")
    print(f"Totale tickers senza settore: {added_missing + removed_missing}")
    
    # Calcola ticker unici usando pandas concat e drop_duplicates
    unique_tickers = pd.concat([
        df['Added Ticker'],
        df['Removed Ticker']
    ]).dropna().unique()
    
    # Rimuovi stringhe vuote e conta
    unique_tickers = [t for t in unique_tickers if t]
    print(f"\nTickers unici: {len(unique_tickers)}")

if __name__ == "__main__":
    main()