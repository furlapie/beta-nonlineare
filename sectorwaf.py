import pandas as pd
from pathlib import Path
import numpy as np

# === CONFIG ===
base = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare")
beta_dir = base / "nbetafinish"  # contains YEAR_bf.csv files
output_file = base / "nbetasec_full.csv"

YEARS = [2020, 2021, 2022, 2023, 2024]

# === INIT RESULTS ===
sector_results = []

for year in YEARS:
    file = beta_dir / f"{year}_bf.csv"
    if not file.exists():
        print(f"⚠️ {file} not found, skipping year {year}")
        continue

    df = pd.read_csv(file)

    # Ensure numeric columns
    for col in ["Beta", "Positive Beta", "Negative Beta", "Avg_MC", "DA %"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Sector", "Beta", "Positive Beta", "Negative Beta", "Avg_MC", "DA %"])

    # Adjust market cap by DA %
    df["Adj_MC"] = df["Avg_MC"] * df["DA %"]

    # Group by sector
    for sector, sub in df.groupby("Sector"):
        if sub.empty:
            continue

        total_mc = sub["Adj_MC"].sum()
        if total_mc == 0:
            continue

        # Weights
        sub["weight"] = sub["Adj_MC"] / total_mc

        # Weighted averages
        weighted_beta = (sub["Beta"] * sub["weight"]).sum()
        weighted_pos_beta = (sub["Positive Beta"] * sub["weight"]).sum()
        weighted_neg_beta = (sub["Negative Beta"] * sub["weight"]).sum()

        # Derived values
        weighted_beta_ratio = weighted_pos_beta / weighted_neg_beta if weighted_neg_beta != 0 else np.nan
        weighted_modified_beta = weighted_beta * weighted_beta_ratio if not np.isnan(weighted_beta_ratio) else np.nan

        # Store
        sector_results.append({
            "Sector": sector,
            "Year": year,
            "Weighted_Beta": weighted_beta,
            "Weighted_Pos_Beta": weighted_pos_beta,
            "Weighted_Neg_Beta": weighted_neg_beta,
            "Weighted_Beta_Ratio": weighted_beta_ratio,
            "Weighted_Modified_Beta": weighted_modified_beta,
            "N_Tickers": len(sub),
            "Total_Marketcap": total_mc
        })

# === EXPORT ===
sector_df = pd.DataFrame(sector_results)
sector_df = sector_df.sort_values(["Sector", "Year"])
sector_df.to_csv(output_file, index=False)

print(f"✅ Saved sector-weighted betas with DA-adjusted market caps: {output_file}")