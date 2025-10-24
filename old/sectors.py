import pandas as pd

# --- INPUT FILES ---
wk_file = r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\wk_by_date.csv"
current_wiki_file = r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\wikipedia_current.csv"
historic_wiki_file = r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\wiki_yf_chat_historic_sectors.csv"
output_file = r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\sectors.csv"

# --- TICKER NORMALIZATION (reverse mapping for Wikipedia lookup) ---
reverse_ticker_map = {
    "BRK-B": "BRK.B",
    "BF-B": "BF.B",
    "FBIN": "FBHS",
    "WBD": ["DISCA", "DISCK"],
    "BFH": "ADS",
    "HWM": "ARNC",
    "FRCB": "FRC",
    "GAP": "GPS"
}

# --- LOAD WK_BY_DATE AND GET ALL UNIQUE TICKERS ---
wk_df = pd.read_csv(wk_file)
all_tickers = set()
for tickers_str in wk_df['Tickers']:
    tickers = [t.strip() for t in str(tickers_str).split(',') if t.strip()]
    all_tickers.update(tickers)

print(f"Total unique tickers in wk_by_date.csv: {len(all_tickers)}")

# --- LOAD CURRENT WIKI SECTORS ---
current_df = pd.read_csv(current_wiki_file)
current_df = current_df[['Symbol', 'GICS Sector']].rename(columns={'Symbol': 'Ticker', 'GICS Sector': 'Sector'})

# Map tickers to their Wikipedia equivalent if missing
mapped_tickers = {}
for t in all_tickers:
    if t in current_df['Ticker'].values:
        mapped_tickers[t] = t
    elif t in reverse_ticker_map:
        mapped_tickers[t] = reverse_ticker_map[t]
    else:
        mapped_tickers[t] = t  # keep as is, maybe historic will have it

# Apply mapping to current_df
current_df['Original_Ticker'] = current_df['Ticker']  # keep original Wiki ticker
current_df['Ticker'] = current_df['Ticker'].map({v:k for k,v in mapped_tickers.items() if v in current_df['Ticker'].values})

# Filter only tickers we need
current_filtered = current_df[current_df['Ticker'].isin(all_tickers)][['Ticker','Sector']]

# --- FIND MISSING TICKERS ---
found_tickers = set(current_filtered['Ticker'])
missing_tickers = all_tickers - found_tickers
print(f"Tickers missing in current Wikipedia: {len(missing_tickers)} -> {missing_tickers}")

# --- LOAD HISTORIC WIKI SECTORS FOR MISSING ---
historic_df = pd.read_csv(historic_wiki_file)
historic_df = historic_df[['Ticker', 'Sector']]

# Apply reverse mapping for missing tickers
historic_mapped = []
for t in missing_tickers:
    wiki_t = reverse_ticker_map.get(t, t)
    if isinstance(wiki_t, list):
        # pick first match found in historic
        for w in wiki_t:
            row = historic_df[historic_df['Ticker'] == w]
            if not row.empty:
                row = row.copy()
                row['Ticker'] = t
                historic_mapped.append(row)
                break
    else:
        row = historic_df[historic_df['Ticker'] == wiki_t]
        if not row.empty:
            row = row.copy()
            row['Ticker'] = t
            historic_mapped.append(row)

historic_filtered = pd.concat(historic_mapped, axis=0) if historic_mapped else pd.DataFrame(columns=['Ticker','Sector'])

# --- COMBINE RESULTS ---
combined_df = pd.concat([current_filtered, historic_filtered], axis=0)
combined_df = combined_df.drop_duplicates(subset='Ticker', keep='first')

# --- CHECK IF SOME TICKERS STILL MISSING ---
still_missing = all_tickers - set(combined_df['Ticker'])
if still_missing:
    print(f"⚠ Warning: {len(still_missing)} tickers still missing sectors: {still_missing}")

# --- SAVE OUTPUT ---
combined_df.to_csv(output_file, index=False)
print(f"✅ Combined ticker-sector file saved to {output_file} ({len(combined_df):,} tickers)")