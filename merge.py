import pandas as pd
from pathlib import Path

# ---------------- CONFIG ----------------
BASE = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare")

NBETA_FULL = BASE / "nbetafull"
NBETA_PART = BASE / "nbetapart"
OUT_DIR    = BASE / "nbetaall"
OUT_DIR.mkdir(exist_ok=True)

YEARS = [2020, 2021, 2022, 2023, 2024]

def merge_year_data(year):
    print(f"\n🔹 Processing {year}...")

    f_full = NBETA_FULL / f"{year}_log_first.csv"
    f_part = NBETA_PART / f"{year}_log_part.csv"

    for f in [f_full, f_part]:
        if not f.exists():
            print(f"⚠️ Missing file: {f}")
            return None

    # --- Load data ---
    df_full = pd.read_csv(f_full)
    df_part = pd.read_csv(f_part)

    # --- Clean Tickers ---
    for df in [df_full, df_part]:
        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()

    # --- Merge full + partial ---
    combined = pd.concat([df_full, df_part], ignore_index=True)

    # --- Drop rows without valid betas ---
    beta_cols = ["Beta", "Positive Beta", "Negative Beta"]
    combined = combined.dropna(subset=beta_cols, how="all")

    # --- Select and reorder columns ---
    keep_cols = [
        "Ticker",
        "Sector",
        "Beta",
        "Positive Beta",
        "Negative Beta",
        "Beta Ratio",
        "Modified Beta",
        "Avg_MC",
    ]
    combined = combined[keep_cols]

    # --- Save ---
    out_path = OUT_DIR / f"{year}_log_all.csv"
    combined.to_csv(out_path, index=False)
    print(f"✅ Saved {len(combined)} rows to {out_path}")

for y in YEARS:
    merge_year_data(y)