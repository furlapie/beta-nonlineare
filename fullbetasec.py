import pandas as pd
from pathlib import Path
import numpy as np

# === CONFIG ===
base = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare")
beta_dir = base / "nbetafull"  # contains YEAR_log_first.csv files
output_file = base / "nbetasec.csv"

YEARS = [2020, 2021, 2022, 2023, 2024]

# === INIT RESULTS ===
sector_results = []

for year in YEARS:
    beta_file = beta_dir / f"{year}_log_first.csv"
    if not beta_file.exists():
        print(f"⚠️ {beta_file} not found, skipping year {year}")
        continue

    beta_df = pd.read_csv(beta_file)

    # Convert numeric columns safely
    for col in ["Beta", "Positive Beta", "Negative Beta", "Avg_MC"]:
        if col in beta_df.columns:
            beta_df[col] = pd.to_numeric(beta_df[col], errors="coerce")

    # Drop missing data
    beta_df = beta_df.dropna(subset=["Beta", "Avg_MC", "Sector"])

    # Group by sector
    for sector, group in beta_df.groupby("Sector"):
        sub = group.copy()
        if sub.empty:
            continue

        # Compute weights
        total_mc = sub["Avg_MC"].sum()
        if total_mc == 0:
            continue

        sub["weight"] = sub["Avg_MC"] / total_mc

        # Weighted averages
        weighted_beta     = (sub["Beta"] * sub["weight"]).sum()
        weighted_pos_beta = (sub["Positive Beta"] * sub["weight"]).sum()
        weighted_neg_beta = (sub["Negative Beta"] * sub["weight"]).sum()

        # Compute sector-level Beta Ratio and Modified Beta
        weighted_beta_ratio = weighted_pos_beta / weighted_neg_beta if weighted_neg_beta != 0 else np.nan
        weighted_modified_beta = weighted_beta * weighted_beta_ratio if not np.isnan(weighted_beta_ratio) else np.nan

        # Store results
        sector_results.append({
            "Sector": sector,
            "Year": year,
            "Weighted_Beta": weighted_beta,
            "Weighted_Pos_Beta": weighted_pos_beta,
            "Weighted_Neg_Beta": weighted_neg_beta,
            "Weighted_Beta_Ratio": weighted_beta_ratio,
            "Weighted_Modified_Beta": weighted_modified_beta,
            "N_Tickers": len(sub)
        })

# === EXPORT ===
sector_df = pd.DataFrame(sector_results)
sector_df = sector_df.sort_values(["Sector", "Year"])
sector_df.to_csv(output_file, index=False)

print(f"✅ Saved sector-weighted betas: {output_file}")