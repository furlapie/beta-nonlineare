import pandas as pd
from pathlib import Path

# --- Paths ---
base_path = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare")
wk_file = base_path / "wk_by_date.csv"
shares_folder = base_path / "shares"
output_file = base_path / "mos.csv"

# --- Load wk_by_date.csv ---
wk = pd.read_csv(wk_file)
wk["Date"] = pd.to_datetime(wk["Date"])
wk["Tickers"] = wk["Tickers"].apply(lambda x: x.replace('"', '').split(','))

# --- Collect all dates and tickers ---
all_dates = wk["Date"].unique()
all_tickers = sorted(set(t for lst in wk["Tickers"] for t in lst))

# --- Create master dataframe ---
master = pd.DataFrame({"Date": all_dates})
master = master.sort_values("Date").reset_index(drop=True)

# --- Precompute date→tickers map ---
date_ticker_map = {row["Date"]: set(row["Tickers"]) for _, row in wk.iterrows()}

print(f"Found {len(all_tickers)} tickers and {len(all_dates)} dates.")

# --- Process each ticker ---
for ticker in all_tickers:
    ticker_file = shares_folder / f"{ticker}.csv"
    if not ticker_file.exists():
        print(f"Missing file for {ticker}")
        master[ticker] = pd.NA
        continue

    df_ticker = pd.read_csv(ticker_file)
    df_ticker["Date"] = pd.to_datetime(df_ticker["Date"])
    df_ticker = df_ticker.rename(columns={"Shares": ticker})

    # Merge with master
    merged = pd.merge(master[["Date"]], df_ticker, on="Date", how="left")

    # Keep only if ticker exists that day
    merged[ticker] = merged.apply(
        lambda r: r[ticker] if ticker in date_ticker_map.get(r["Date"], set()) else pd.NA,
        axis=1
    )

    master[ticker] = merged[ticker]

# --- Save result ---
master.to_csv(output_file, index=False)
print(f"Saved master file: {output_file}")