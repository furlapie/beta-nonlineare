import pandas as pd
import yfinance as yf
import time
from pathlib import Path
import requests

# --- Create browser-like session ---
session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
})
yf.shared._requests = session  # Inject the session into yfinance

# === INPUT FILES & PATHS ===
wk_file = "wk_by_date.csv"
local_data_path = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\tCP")
master_file = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\mcp.csv")

# === SETTINGS ===
BATCH_SIZE = 103
MAX_DAYS = 1260
SLEEP_TIME = 0.3

# === LOAD WEEKLY DATA ===
df = pd.read_csv(wk_file, parse_dates=["Date"]).head(MAX_DAYS)

# === LOAD EXISTING MASTER DF OR CREATE EMPTY ===
if master_file.exists():
    master_df = pd.read_csv(master_file, index_col=0, parse_dates=True)
else:
    master_df = pd.DataFrame()

results = []

print(f"Testing {len(df)} days ({df['Date'].min().date()} → {df['Date'].max().date()})...\n")

for _, row in df.iterrows():
    date = row["Date"]
    tickers = [t.strip() for t in str(row["Tickers"]).split(",") if t.strip()]
    total = len(tickers)
    missing = 0
    missing_list = []
    missing_reasons = {}

    start_time = time.time()
    current_idx = _ + 1  # progress counter (1-based)
    print(f"→ {date.date()} ({total})... ", end="", flush=True)
    closes = {}

    # Loop over tickers in batches
    for i in range(0, total, BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        batch_to_download = []

        # --- First, check local CSVs ---
        for t in batch:
            if t in master_df.columns and pd.notna(master_df.loc[date, t] if date in master_df.index else None):
                closes[t] = master_df.loc[date, t]
                continue

            csv_path = local_data_path / f"{t}.csv"
            if csv_path.exists():
                try:
                    local_df = pd.read_csv(csv_path, parse_dates=["Date"])
                    local_close = local_df.loc[local_df["Date"] == pd.Timestamp(date), "Close"]
                    if not local_close.empty:
                        closes[t] = local_close.iloc[0]
                        continue
                    else:
                        missing_reasons[t] = "Date not found in local CSV"
                except Exception as e:
                    missing_reasons[t] = f"Error reading local CSV: {e}"
            else:
                missing_reasons[t] = "CSV not found locally"

            batch_to_download.append(t)

        # --- Download missing tickers from yfinance ---
        if batch_to_download:
            attempt = 0
            max_attempts = 3
            success = False

            while attempt < max_attempts and not success:
                try:
                    data = yf.download(
                        batch_to_download,
                        start=date,
                        end=date + pd.Timedelta(days=1),
                        progress=False,
                        auto_adjust=True,
                        group_by="ticker"
                    )

                    if isinstance(data.columns, pd.MultiIndex):
                        for t in batch_to_download:
                            try:
                                val = data[t]["Close"].iloc[0]
                                closes[t] = val if not pd.isna(val) else None
                                if pd.isna(val):
                                    missing_reasons[t] = "Empty Yahoo data"
                            except Exception:
                                closes[t] = None
                                missing_reasons[t] = "Ticker missing in Yahoo batch"
                    else:
                        for t in batch_to_download:
                            try:
                                val = data["Close"].iloc[0]
                                closes[t] = val if not pd.isna(val) else None
                                if pd.isna(val):
                                    missing_reasons[t] = "Empty Yahoo data"
                            except Exception:
                                closes[t] = None
                                missing_reasons[t] = "Ticker missing in Yahoo batch"

                    success = True  # success if no exception
                except yf.shared._exceptions.YFRateLimitError:
                    attempt += 1
                    wait_time = 3 * attempt
                    print(f"⚠ Rate limit hit — waiting {wait_time}s before retry ({attempt}/{max_attempts})...")
                    time.sleep(wait_time)
                except Exception as e:
                    print(f"⚠ Error downloading batch starting with {batch_to_download[0]}: {e}")
                    attempt += 1
                    time.sleep(2)

            if not success:
                # mark tickers as failed after all retries
                for t in batch_to_download:
                    closes[t] = None
                    missing_reasons[t] = "Download failed after retries"

            time.sleep(SLEEP_TIME)

        # --- Count missing ---
        for t in batch:
            if t not in closes or pd.isna(closes[t]):
                missing += 1
                missing_list.append(t)

    # --- Append daily closes to master_df ---
    if closes:
        day_df = pd.DataFrame.from_dict(closes, orient="index", columns=[date])
        day_df = day_df.T
        master_df = pd.concat([master_df, day_df], axis=0)
        master_df = master_df[~master_df.index.duplicated(keep="last")]

    duration = time.time() - start_time

    # --- Print summary ---
    if missing > 0:
        preview = ", ".join(missing_list[:10])
        if len(missing_list) > 10:
            preview += ", ..."
        print(f"⚠  {missing} ({preview}) ✔  {duration:.1f}s ({current_idx}/{MAX_DAYS})")
    else:
        print(f"✔  {duration:.1f}s ({current_idx}/{MAX_DAYS})")

    # --- Save daily result ---
    results.append({
        "Date": date,
        "Total_Tickers": total,
        "Missing_Close": missing,
        "Missing_Tickers": ",".join(missing_list),
        "Missing_Reasons": "; ".join([f"{t}:{missing_reasons.get(t, 'Unknown')}" for t in missing_list]),
        "Duration_sec": round(duration, 1)
    })

# === SAVE MASTER DF & REPORT ===
master_df.sort_index(inplace=True)
master_df.to_csv(master_file)
print(f"✅ Master close prices updated to mcp.csv")

results_df = pd.DataFrame(results)
avg_missing = results_df["Missing_Close"].mean()
max_missing = results_df["Missing_Close"].max()
worst_day = results_df.loc[results_df["Missing_Close"].idxmax(), "Date"]

print("\n=== SUMMARY ===")
print(f"Average missing tickers per day: {avg_missing:.2f}")
print(f"Maximum missing tickers in a day: {max_missing} ({worst_day.date()})")
print(f"Total missing tickers over {len(results)} days: {results_df['Missing_Close'].sum()}")

results_df.to_csv("missing_prices_report.csv", index=False)
print("Saved detailed report to missing_prices_report.csv")