import pandas as pd
from pathlib import Path

# --- CONFIG ---
wk_file = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\wk_by_date.csv")
shares_folder = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\shares")

# --- CREATE OUTPUT FOLDER ---
shares_folder.mkdir(exist_ok=True)

# --- READ UNIQUE TICKERS ---
wk_df = pd.read_csv(wk_file)
all_tickers = set()
for tickers_str in wk_df['Tickers']:
    tickers = [t.strip() for t in str(tickers_str).split(",") if t.strip()]
    all_tickers.update(tickers)
tickers = sorted(all_tickers)
print(f"Found {len(tickers)} unique tickers")

# --- CHECK IF FILES ARE EMPTY (A2 empty) ---
empty_files = []
non_empty_files = []

for ticker in tickers:
    output_path = shares_folder / f"{ticker}.xlsx"
    if not output_path.exists():
        empty_files.append(ticker)
        # optionally create empty template
        df = pd.DataFrame(columns=["Date", "Shares"])
        df.to_excel(output_path, index=False)
    else:
        try:
            df = pd.read_excel(output_path)
            # check if A2 is empty
            if df.shape[0] < 1 or pd.isna(df.iloc[0, 0]):
                empty_files.append(ticker)
            else:
                non_empty_files.append(ticker)
        except Exception as e:
            print(f"⚠ Could not read {output_path.name} -> {e}")
            empty_files.append(ticker)

# --- PRINT RESULTS ---
print("\n⏩ Excel files with no data in A2 (empty):")
print(empty_files)
print(f"Total empty: {len(empty_files)}")

print("\n⏩ Excel files with data in A2 (non-empty):")
print(non_empty_files)
print(f"Total filled: {len(non_empty_files)}")
