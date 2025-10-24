import pandas as pd
from pathlib import Path

# === PATHS ===
base_path = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare")
master_file = base_path / "mcp.csv"
wk_file = base_path / "wk_by_date.csv"

# === LOAD FILES ===
if not master_file.exists():
    raise FileNotFoundError(f"File not found: {master_file}")
if not wk_file.exists():
    raise FileNotFoundError(f"File not found: {wk_file}")

print(f"Reading master close prices from: {master_file}")
df = pd.read_csv(master_file, index_col=0, parse_dates=True)
wk = pd.read_csv(wk_file, parse_dates=["Date"])

# === Build presence matrix ===
# For each date, map which tickers were active in the index
presence_map = {}
for _, row in wk.iterrows():
    tickers = [t.strip() for t in str(row["Tickers"]).split(",") if t.strip()]
    presence_map[pd.Timestamp(row["Date"])] = set(tickers)

# === Check missing values only where ticker should exist ===
missing_rows = []
for ticker in df.columns:
    for date, value in df[ticker].items():
        if date not in presence_map:
            continue
        if ticker in presence_map[date] and pd.isna(value):
            missing_rows.append((ticker, date.strftime("%Y-%m-%d")))

# === Summarize ===
if not missing_rows:
    print("✅ No missing values found for active tickers.")
else:
    missing_df = pd.DataFrame(missing_rows, columns=["Ticker", "Date"])
    summary = missing_df["Ticker"].value_counts()
    print(f"⚠ Found {len(summary)} tickers with missing data (only on active days):\n")
    print(summary.head(10))
    missing_df.to_csv("missing_rows.csv", index=False)
    print("\nSaved detailed report to missing_rows.csv")

    total_missing = len(missing_rows)
    total_cells = df.size
    pct_missing = 100 * total_missing / total_cells
    print(f"\n=== SUMMARY ===")
    print(f"Total missing cells (active only): {total_missing:,} ({pct_missing:.4f}%)")
    print(f"Tickers affected: {len(summary)} / {df.shape[1]} total")