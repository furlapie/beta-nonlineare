import pandas as pd
import re
import yfinance as yf

# PATHS
wk_current_path = r"../beta-nonlineare/wikipedia_current.csv"
wk_changes_path = r"../beta-nonlineare/wikipedia_historic_changes.csv"

# TICKER NORMALIZATION + MANUAL FIXES
ticker_map = {
    "BRK.B": "BRK-B",  # Berkshire Hathaway rename
    "BF.B": "BF-B",    # Brown-Forman rename
    "FBHS": "FBIN",    # Fortune Brands Innovations ticker change
    "DISCA": "WBD",    # Discovery Inc. Class A → Warner Bros. Discovery
    "DISCK": "WBD",    # Discovery Inc. Class C → Warner Bros. Discovery
    "ADS": "BFH",      # Alliance Data Systems → Bread Financial
    "ARNC": "HWM",     # Arconic → Howmet Aerospace
    "FRC" : "FRCB",    # First Republic Bank rename
    "GPS" : "GAP",     # Gap Inc. ticker change
}

def normalize_ticker(ticker: str) -> str:
    # Converts Bloomberg/Wikipedia tickers to Yahoo Finance format.

    if not isinstance(ticker, str) or not ticker.strip():
        return ""
    t = ticker.strip().upper()

    # manual remapping first
    if t in ticker_map:
        return ticker_map[t]

    # standard normalization
    t = t.replace("/", "-").replace(".", "-")
    return t


# WIKIPEDIA PROCESSING
changes = pd.read_csv(wk_changes_path, parse_dates=["Date"], dayfirst=True)
current = pd.read_csv(wk_current_path)

# Current constituents
current_constituents = set(
    normalize_ticker(t) for t in current["Symbol"].dropna().astype(str).str.strip()
)

# Sort changes descending
changes = changes.sort_values("Date", ascending=False).reset_index(drop=True)

history = []

for _, row in changes.iterrows():
    date = row["Date"]
    added = normalize_ticker(str(row["Added Ticker"]).strip()) if pd.notna(row["Added Ticker"]) else None
    removed = normalize_ticker(str(row["Removed Ticker"]).strip()) if pd.notna(row["Removed Ticker"]) else None

    if added:
        current_constituents.discard(added)
    if removed:
        current_constituents.add(removed)

    history.append({
        "Date": date,
        "Tickers": ",".join(sorted([t for t in current_constituents if t]))
    })

history_df = (
    pd.DataFrame(history)
    .sort_values("Date")
    .drop_duplicates(subset=["Date"], keep="last")
    .reset_index(drop=True)
)

# Add base row (day before first change)
earliest_state = history_df.iloc[0]["Tickers"]
first_change_date = history_df.iloc[0]["Date"]
base_row = pd.DataFrame([{
    "Date": first_change_date - pd.Timedelta(days=1),
    "Tickers": earliest_state
}])
history_df = pd.concat([base_row, history_df], ignore_index=True)

# Full daily range
start_all = pd.Timestamp("2019-12-01")
end_all = pd.Timestamp("2025-01-01")
all_days = pd.DataFrame({"Date": pd.date_range(start_all, end_all, freq="D")})

# Merge + forward fill
full_history = pd.merge(all_days, history_df, on="Date", how="left")
full_history["Tickers"] = full_history["Tickers"].ffill()

# === RIMUOVI GIORNI NON DI MERCATO ===
sp500 = yf.download("^GSPC", start=start_all, end=end_all + pd.Timedelta(days=1), progress=False, auto_adjust=True)
trading_days = sp500.index.normalize()
full_history = full_history[full_history["Date"].isin(trading_days)].reset_index(drop=True)

# === FILTRA PER PERIODO FINALE ===
start_export = pd.Timestamp("2020-01-01")
end_export = pd.Timestamp("2025-01-01")
export_df = full_history[
    (full_history["Date"] >= start_export) & (full_history["Date"] <= end_export)
].reset_index(drop=True)

# === EXPORT ===
export_df.to_csv("wk_by_date.csv", index=False)
print(f"wk_by_date.csv creato con {len(export_df)} righe dal {start_export.date()} al {end_export.date()}.")
