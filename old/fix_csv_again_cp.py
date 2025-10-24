import pandas as pd
from pathlib import Path

# === Paths ===
mcp_path = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\mcp.csv")
ls_folder = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\tCP")

print("📂 Loading mcp.csv ...")

# Read wide-format file
mcp = pd.read_csv(mcp_path)

# Clean column names
mcp.columns = [c.strip().replace('"', '') for c in mcp.columns]

# Parse Date column
mcp["Date"] = pd.to_datetime(mcp["Date"], errors="coerce")
mcp = mcp.dropna(subset=["Date"])

# Melt from wide → long format (Date, Ticker, Close)
mcp_long = mcp.melt(id_vars="Date", var_name="Ticker", value_name="Close")
mcp_long = mcp_long.dropna(subset=["Close"])  # drop missing cells

# Ensure output folder exists
ls_folder.mkdir(parents=True, exist_ok=True)

tickers = mcp_long["Ticker"].unique()
print(f"Found {len(tickers)} tickers in mcp.csv")

# Export one CSV per ticker
for ticker, group in mcp_long.groupby("Ticker"):
    group = group[["Date", "Close"]].sort_values("Date")
    group["Date"] = group["Date"].dt.strftime("%Y-%m-%d")

    out_path = ls_folder / f"{ticker}.csv"
    group.to_csv(out_path, index=False)
    print(f"✅ Recreated {ticker}.csv with {len(group)} rows.")

print("\n🎯 All LS CSVs successfully rebuilt from mcp.csv (wide format).")