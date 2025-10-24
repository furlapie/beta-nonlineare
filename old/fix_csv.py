import pandas as pd
from pathlib import Path

# Paths
folder = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\tCP")
wk_by_date_path = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\wk_by_date.csv")

# Load wk_by_date
wk_df = pd.read_csv(wk_by_date_path, parse_dates=["Date"])
wk_df["Date"] = pd.to_datetime(wk_df["Date"])
ticker_dates = {}

for _, row in wk_df.iterrows():
    tickers = [t.strip() for t in str(row["Tickers"]).split(",") if t.strip()]
    for t in tickers:
        ticker_dates.setdefault(t, []).append(row["Date"])

# --- Process each XLSX/CSV ---
for path in folder.glob("*.csv"):
    ticker = path.stem
    print(f"Processing {ticker}...")

    try:
        df = pd.read_csv(path)
        df.columns = [c.strip().replace('"', '') for c in df.columns]

        # Parse date
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Date"])

        # Rename Shares/Close column if needed
        value_col = "Shares" if "Shares" in df.columns else "Close" if "Close" in df.columns else None
        if not value_col:
            raise ValueError(f"No 'Shares' or 'Close' column in {path.name}")

        df = df[["Date", value_col]].sort_values("Date")

        # Build full timeline of all active dates
        if ticker not in ticker_dates:
            print(f"⚠️ {ticker} not found in wk_by_date, skipping.")
            continue

        all_dates = pd.Series(sorted(set(ticker_dates[ticker])))
        full_df = pd.DataFrame({"Date": all_dates})

        # Merge and forward-fill
        full_df = full_df.merge(df, on="Date", how="left")
        full_df[value_col] = full_df[value_col].ffill()

        # Optionally interpolate between quarterly values (smoother)
        # full_df[value_col] = full_df[value_col].interpolate(method='linear')

        # Save back (overwrite)
        full_df["Date"] = full_df["Date"].dt.strftime("%Y-%m-%d")
        df_out = full_df[["Date", value_col]]
        df_out.to_csv(path, index=False)
        print(f"✅ Updated {ticker} with {len(df_out)} daily rows.")

    except Exception as e:
        print(f"❌ Error processing {ticker}: {e}")