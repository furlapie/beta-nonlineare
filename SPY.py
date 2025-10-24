import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path

def download_spy(output_csv: str, wk_file: str):
    # --- Load wk_by_date.csv to get date range ---
    wk_df = pd.read_csv(wk_file, parse_dates=["Date"])
    start_date = wk_df["Date"].min().strftime("%Y-%m-%d")
    # Add 1 day to include the last date
    end_date = (wk_df["Date"].max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"→ Downloading SPY from {start_date} to {end_date} ...")

    # Download historical data only for this range
    data = yf.download("SPY", start=start_date, end=end_date, progress=True, auto_adjust=True)

    if data.empty:
        print("No data found for SPY")
        return

    # Fix possible MultiIndex columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Keep only price column
    if 'Adj Close' in data.columns:
        price_col = 'Adj Close'
    elif 'Close' in data.columns:
        price_col = 'Close'
    else:
        raise ValueError("Adjusted close column not found in downloaded data.")

    data = data[[price_col]].copy()
    data.rename(columns={price_col: 'Adj Close'}, inplace=True)

    # Compute simple and log returns
    data['Simple_Return'] = data['Adj Close'].pct_change()
    data['Log_Return'] = np.log(data['Adj Close'] / data['Adj Close'].shift(1))

    # Reset index and format date
    data.reset_index(inplace=True)
    data['Date'] = data['Date'].dt.strftime('%Y-%m-%d')

    # Remove any completely empty first row (sometimes comes from auto_adjust)
    data.dropna(how='all', inplace=True)

    # Save CSV
    data.to_csv(output_csv, index=False)
    print(f"✔ Data saved to {Path(output_csv).resolve()} ({len(data):,} rows)")

if __name__ == "__main__":
    wk_file_path = "wk_by_date.csv"
    output_file = "SPY.csv"
    download_spy(output_file, wk_file_path)