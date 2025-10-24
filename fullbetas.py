import pandas as pd
import numpy as np
from pathlib import Path

# === CONFIG ===
base = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare")
ret_file = base / "logm.csv"
spy_file = base / "SPY.csv"
sector_file = base / "smc.csv"
obs_dir = base / "yobs"
output_dir = base / "nbetafull"
sector_out_dir = base / "nbetapart"
output_dir.mkdir(exist_ok=True)
sector_out_dir.mkdir(exist_ok=True)

YEARS = [2020, 2021, 2022, 2023, 2024]

# === LOAD DATA ===
ret_df = pd.read_csv(ret_file, parse_dates=["Date"])
spy_df = pd.read_csv(spy_file, parse_dates=["Date"])
sectors_df = pd.read_csv(sector_file)

ret_df.set_index("Date", inplace=True)
spy_df.set_index("Date", inplace=True)

# Only need Log_Return for SPY
spy_returns = pd.to_numeric(spy_df["Log_Return"], errors="coerce")
spy_returns.index = spy_df.index

# === FUNCTION TO CALCULATE BETA LIKE EXCEL ===
def calc_beta(y, x):
    df = pd.concat([y, x], axis=1).dropna()
    if len(df) < 20:
        return np.nan
    cov = np.cov(df.iloc[:, 0], df.iloc[:, 1], ddof=1)[0, 1]
    var = np.var(df.iloc[:, 1], ddof=1)
    return cov / var if var != 0 else np.nan

# === MAIN LOOP PER YEAR ===
for year in YEARS:
    print(f"\n📊 Processing year {year}...")
    start = pd.Timestamp(f"{year}-01-01")
    end = pd.Timestamp(f"{year+1}-01-01")

    # Load DA info and select tickers with DA% = 1
    obs_file = obs_dir / f"{year}_obs.csv"
    obs_df = pd.read_csv(obs_file)
    da100 = set(obs_df.loc[obs_df["DA %"] == 1, "Ticker"].astype(str))

    # Filter returns for the year
    tickers_to_use = list(da100.intersection(ret_df.columns))
    year_ret = ret_df.loc[start:end, tickers_to_use]
    market_ret = spy_returns.loc[start:end]

    results = []

    for ticker in year_ret.columns:
        r_i = pd.to_numeric(year_ret[ticker], errors="coerce").dropna()
        aligned = pd.concat([r_i, market_ret.rename("Log_Return")], axis=1, join="inner").dropna()
        if len(aligned) < 30:
            continue

        beta_total = calc_beta(aligned[ticker], aligned["Log_Return"])
        beta_up = calc_beta(aligned.loc[aligned["Log_Return"] > 0, ticker],
                            aligned.loc[aligned["Log_Return"] > 0, "Log_Return"])
        beta_down = calc_beta(aligned.loc[aligned["Log_Return"] < 0, ticker],
                              aligned.loc[aligned["Log_Return"] < 0, "Log_Return"])

        beta_ratio = beta_up / beta_down if pd.notna(beta_up) and pd.notna(beta_down) and beta_down != 0 else np.nan
        modified_beta = beta_total * beta_ratio if pd.notna(beta_total) and pd.notna(beta_ratio) else np.nan

        # Attach sector + average market cap
        row = sectors_df.loc[sectors_df["Ticker"] == ticker]
        sector = row["Sector"].values[0] if not row.empty else np.nan
        avg_mc = pd.to_numeric(row[str(year)].values[0], errors="coerce") if str(year) in row.columns else np.nan

        results.append((ticker, beta_total, beta_up, beta_down, beta_ratio, modified_beta, sector, avg_mc))

    # --- Sort alphabetically by Ticker ---
    df_out = pd.DataFrame(results, columns=[
        "Ticker", "Beta", "Positive Beta", "Negative Beta", "Beta Ratio", "Modified Beta", "Sector", "Avg_MC"
    ])
    df_out = df_out.sort_values("Ticker")

    # --- Export yearly ticker-level beta CSV ---
    out_file = output_dir / f"{year}_log_first.csv"
    df_out.to_csv(out_file, index=False)
    print(f"✅ Saved {out_file.name} ({len(df_out)} tickers)")

    # === SECTOR-WEIGHTED SHRINK ===
    print(f"📈 Aggregating sector-weighted averages for {year}...")
    sector_summary = []
    for sector, g in df_out.dropna(subset=["Sector", "Avg_MC"]).groupby("Sector"):
        g = g.dropna(subset=["Beta", "Positive Beta", "Negative Beta"])
        if g.empty:
            continue

        total_cap = g["Avg_MC"].sum()
        w = g["Avg_MC"] / total_cap

        w_beta = np.sum(g["Beta"] * w)
        w_up = np.sum(g["Positive Beta"] * w)
        w_down = np.sum(g["Negative Beta"] * w)
        w_ratio = w_up / w_down if w_down != 0 else np.nan
        w_mod = w_beta * w_ratio if pd.notna(w_ratio) else np.nan

        sector_summary.append([
            sector, year, w_beta, w_up, w_down, w_ratio, w_mod, len(g)
        ])

    df_sector = pd.DataFrame(
        sector_summary,
        columns=[
            "Sector", "Year", "Weighted_Beta", "Weighted_Pos_Beta",
            "Weighted_Neg_Beta", "Weighted_Beta_Ratio",
            "Weighted_Modified_Beta", "N_Tickers"
        ]
    ).sort_values(["Sector", "Year"])

    sector_file = sector_out_dir / f"{year}_log_part.csv"
    df_sector.to_csv(sector_file, index=False)
    print(f"✅ Saved {sector_file.name} ({len(df_sector)} sectors)")

print("\n🎯 All done!")