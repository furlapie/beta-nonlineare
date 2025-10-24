import pandas as pd
from pathlib import Path
import numpy as np

# --- Paths ---
base_path = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare")
mos_file = base_path / "mos.csv"
mcp_file = base_path / "mcp.csv"
mmc_file = base_path / "mmc.csv"
avg_file = base_path / "avg_mmc.csv"

# --- Load both files ---
mos = pd.read_csv(mos_file)
mcp = pd.read_csv(mcp_file)

# --- Handle missing or misnamed Date columns ---
def ensure_date_column(df, name):
    if "Date" not in df.columns:
        unnamed_cols = [c for c in df.columns if c.startswith("Unnamed")]
        if unnamed_cols:
            print(f"⚙️ Renaming {unnamed_cols[0]} to 'Date' in {name}.csv")
            df = df.rename(columns={unnamed_cols[0]: "Date"})
        else:
            raise ValueError(f"❌ No Date column found in {name}.csv")
    return df

mos = ensure_date_column(mos, "mos")
mcp = ensure_date_column(mcp, "mcp")

# --- Ensure proper date formatting ---
for df in [mos, mcp]:
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

# --- Column comparison ---
mos_cols = set(mos.columns)
mcp_cols = set(mcp.columns)

if mos_cols == mcp_cols:
    print(f"✅ Columns match perfectly ({len(mos.columns)} total: 1 Date + {len(mos.columns)-1} tickers).")
else:
    missing_in_mos = mcp_cols - mos_cols
    missing_in_mcp = mos_cols - mcp_cols
    print("⚠️ Columns differ between mos and mcp!")
    print(f"   → Total in mos: {len(mos.columns)} | Total in mcp: {len(mcp.columns)}")
    print(f"   → Missing in mos: {missing_in_mos if missing_in_mos else 'none'}")
    print(f"   → Missing in mcp: {missing_in_mcp if missing_in_mcp else 'none'}")

# --- Date comparison ---
if not mos["Date"].equals(mcp["Date"]):
    print("⚠️ Dates differ between mos and mcp!")
else:
    print("✅ Dates match.")

# --- Compare filled cells ---
tickers = [c for c in mos.columns if c != "Date"]
print("\n🔍 Checking non-empty cell counts per ticker...")

diffs = []
for t in tickers:
    mos_filled = mos[t].notna().sum()
    mcp_filled = mcp[t].notna().sum()
    if mos_filled != mcp_filled:
        diffs.append((t, mos_filled, mcp_filled))

if diffs:
    print(f"⚠️ Found {len(diffs)} tickers with mismatched filled cells:")
    for t, mos_c, mcp_c in diffs[:15]:
        print(f"   {t}: mos={mos_c}, mcp={mcp_c}")
else:
    print("✅ All tickers have the same number of filled cells.")

# --- Compute Market Cap ---
print("\n💰 Computing Market Cap...")
mmc = mos.copy()
for t in tickers:
    mmc[t] = mcp[t] * mos[t]

# --- Save master market cap file ---
mmc.to_csv(mmc_file, index=False)
print(f"💾 Saved master market cap file: {mmc_file}")

# --- Compute average market cap per year per ticker ---
print("\n📊 Computing yearly averages...")
mmc["Date"] = pd.to_datetime(mmc["Date"], errors="coerce")
mmc["Year"] = mmc["Date"].dt.year

melted = mmc.melt(id_vars=["Date", "Year"], var_name="Ticker", value_name="MarketCap")
melted = melted.dropna(subset=["MarketCap"])

avg = melted.groupby(["Ticker", "Year"])["MarketCap"].mean().unstack(fill_value=None)
cols_to_keep = [y for y in range(2020, 2025)]
avg = avg.reindex(columns=cols_to_keep)
avg = avg.round(2)
avg.to_csv(avg_file)
print(f"💾 Saved average yearly market cap file: {avg_file}")

# --- Show smallest market caps ---
print("\n🔎 Finding 10 smallest market cap values across all tickers...")

# Drop NaNs and find smallest 10
smallest = melted.nsmallest(10, "MarketCap")[["Date", "Ticker", "MarketCap"]]
print(smallest.to_string(index=False))

print("\n✅ Done! Columns:")
print(avg.columns.tolist())