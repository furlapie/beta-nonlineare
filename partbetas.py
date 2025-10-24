import pandas as pd
import numpy as np
from pathlib import Path

# ---------------- CONFIG ----------------
BASE = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare")
LOGM = BASE / "logm.csv"          # daily log returns (wide)
SPY = BASE / "SPY.csv"           # contains Log_Return
SMC = BASE / "smc.csv"           # Ticker, Sector, 2020..2024 (Avg_MC per year)
NBETASEC = BASE / "nbetasec.csv" # sector-level weighted betas per year (Sector,Year,...)
YOBS_DIR = BASE / "yobs"         # contains YEAR_obs.csv with "Ticker","Days Active","DA %"
OUT_DIR = BASE / "nbetapart"     # output folder
OUT_DIR.mkdir(exist_ok=True)

YEARS = [2020, 2021, 2022, 2023, 2024]
C = 120.0  # shrinkage constant

MIN_ALIGN_FOR_RAW = 2  # min aligned days to compute raw beta

# ---------------- HELPERS ----------------
def calc_beta(y, x):
    """Compute beta as cov(y,x)/var(x), same as Excel SLOPE."""
    if len(y) < 2:
        return np.nan
    yv = np.asarray(y, dtype=float)
    xv = np.asarray(x, dtype=float)
    mask = (~np.isnan(yv)) & (~np.isnan(xv))
    if mask.sum() < 2:
        return np.nan
    yv = yv[mask]
    xv = xv[mask]
    var_x = np.var(xv, ddof=1)
    if var_x == 0 or np.isnan(var_x):
        return np.nan
    cov = np.cov(yv, xv, ddof=1)[0, 1]
    return cov / var_x

def lambda_from_n(n, c=C):
    """Shrinkage lambda = n / (n + c)."""
    try:
        n = float(n)
    except Exception:
        return 0.0
    if n <= 0:
        return 0.0
    return n / (n + c)

# ---------------- LOAD STATIC FILES ----------------
print("Loading static files...")
logm_df = pd.read_csv(LOGM, parse_dates=["Date"])
spy_df = pd.read_csv(SPY, parse_dates=["Date"])
smc_df = pd.read_csv(SMC)
nbetasec_df = pd.read_csv(NBETASEC)

# Normalize SPY columns
spy_df = spy_df[["Date", "Log_Return"]].rename(columns={"Log_Return": "Market_Return"})
spy_df = spy_df.dropna(subset=["Market_Return"]).set_index("Date")

# Prepare sector lookup from SMC
smc_sector_lookup = pd.Series(smc_df.Sector.values, index=smc_df.Ticker).to_dict()

# Prepare Avg_MC lookup per year
avg_mc_by_year = {}
for y in YEARS:
    col = str(y)
    if col in smc_df.columns:
        avg_mc_by_year[y] = pd.Series(smc_df[col].values, index=smc_df.Ticker).to_dict()
    else:
        avg_mc_by_year[y] = {}

# Transform nbetasec for fast lookup: (year, sector) -> row
nbetasec_lookup = {}
if not nbetasec_df.empty:
    for _, r in nbetasec_df.iterrows():
        yr = int(r["Year"]) if "Year" in r and not pd.isna(r["Year"]) else None
        sec = r["Sector"]
        if yr is None:
            continue
        nbetasec_lookup[(yr, sec)] = r

# ---------------- MAIN PROCESS ----------------
for year in YEARS:
    print("\n" + "="*40)
    print(f"Processing year {year}")

    obs_file = YOBS_DIR / f"{year}_obs.csv"

    obs_df = pd.read_csv(obs_file)

    # Normalize names
    if "Days Active" not in obs_df.columns and "Days_Active" in obs_df.columns:
        obs_df = obs_df.rename(columns={"Days_Active": "Days Active"})
    if "DA %" not in obs_df.columns and "DA_pct" in obs_df.columns:
        obs_df = obs_df.rename(columns={"DA_pct": "DA %"})

    obs_df["Days Active"] = pd.to_numeric(obs_df.get("Days Active", 0), errors="coerce").fillna(0).astype(int)
    obs_df["DA %"] = pd.to_numeric(obs_df.get("DA %", 0.0), errors="coerce").fillna(0.0)

    # Tickers with DA% < 1 and DA% = 0
    partial_df = obs_df.loc[obs_df["DA %"] < 1.0].copy()
    partial_tickers = partial_df["Ticker"].astype(str).tolist()
    print(f"Tickers with DA% < 1: {len(partial_tickers)}")

    empty_df = obs_df.loc[obs_df["DA %"] == 0.0].copy()
    empty_tickers = empty_df["Ticker"].astype(str).tolist()
    print(f"Tickers with DA% = 0: {len(empty_tickers)}")

    # Subset daily returns for this year
    start, end = pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year+1}-01-01")
    year_logm = logm_df[(logm_df["Date"] >= start) & (logm_df["Date"] < end)].copy()
    if year_logm.empty:
        print(f"No daily returns for year {year} -> skipping")
        continue

    merged_daily = year_logm.merge(spy_df.reset_index(), on="Date", how="left")
    if merged_daily["Market_Return"].isna().all():
        print("No market returns available -> skipping year")
        continue

    merged_daily = merged_daily.set_index("Date")
    existing_cols = [c for c in partial_tickers if c in merged_daily.columns]
    missing_cols = set(partial_tickers) - set(existing_cols)
    if missing_cols:
        print(f"⚠️ Skipping {len(missing_cols)} tickers missing in logm.csv")

    results = []
    shrunk_count = raw_count = cannot_compute = 0

    for ticker in sorted(existing_cols):
        s_t = pd.to_numeric(merged_daily[ticker], errors="coerce")
        s_m = pd.to_numeric(merged_daily["Market_Return"], errors="coerce")

        aligned = pd.concat([s_t, s_m], axis=1, join="inner").dropna()
        aligned.columns = [ticker, "Market_Return"]

        n_i = len(aligned["Market_Return"].dropna())
        da_pct = float(partial_df.loc[partial_df["Ticker"] == ticker, "DA %"].iloc[0]) if ticker in partial_df["Ticker"].values else 0.0

        if len(aligned) < MIN_ALIGN_FOR_RAW:
            cannot_compute += 1
            raw_beta = raw_pos = raw_neg = np.nan
        else:
            raw_beta = calc_beta(aligned[ticker], aligned["Market_Return"])
            mask_up = aligned["Market_Return"] >= 0
            mask_down = aligned["Market_Return"] < 0

            print("TICKER", ticker)
            print("Total aligned rows:", len(aligned))
            print("Up days:", mask_up.sum(), "Down days:", mask_down.sum())

            raw_pos = calc_beta(aligned.loc[mask_up, ticker], aligned.loc[mask_up, "Market_Return"]) if mask_up.any() else np.nan
            raw_neg = calc_beta(aligned.loc[mask_down, ticker], aligned.loc[mask_down, "Market_Return"]) if mask_down.any() else np.nan
            raw_count += 1

        sector = smc_sector_lookup.get(ticker, np.nan)
        sec_row = nbetasec_lookup.get((year, sector), None)
        if sec_row is None:
            df_year = nbetasec_df[nbetasec_df["Year"] == year]
            if not df_year.empty:
                sec_wbeta = df_year["Weighted_Beta"].mean()
                sec_wpos = df_year["Weighted_Pos_Beta"].mean()
                sec_wneg = df_year["Weighted_Neg_Beta"].mean()
            else:
                sec_wbeta = sec_wpos = sec_wneg = np.nan
        else:
            sec_wbeta = sec_row.get("Weighted_Beta", np.nan)
            sec_wpos = sec_row.get("Weighted_Pos_Beta", np.nan)
            sec_wneg = sec_row.get("Weighted_Neg_Beta", np.nan)

        if da_pct < 1.0 and not np.isnan(raw_beta):
            lam = lambda_from_n(n_i, C)
            shrunk_beta = lam * raw_beta + (1 - lam) * sec_wbeta if not np.isnan(sec_wbeta) else raw_beta
            shrunk_pos = lam * raw_pos + (1 - lam) * sec_wpos if not np.isnan(sec_wpos) else raw_pos
            shrunk_neg = lam * raw_neg + (1 - lam) * sec_wneg if not np.isnan(sec_wneg) else raw_neg
            shrunk_count += 1
        else:
            shrunk_beta, shrunk_pos, shrunk_neg = raw_beta, raw_pos, raw_neg

        shrunk_ratio = shrunk_mod = np.nan
        if pd.notna(shrunk_pos) and pd.notna(shrunk_neg) and shrunk_neg != 0:
            shrunk_ratio = shrunk_pos / shrunk_neg
            shrunk_mod = shrunk_beta * shrunk_ratio if pd.notna(shrunk_beta) else np.nan

        avg_mc = avg_mc_by_year.get(year, {}).get(ticker, np.nan)

        results.append({
            "Ticker": ticker,
            "Year": year,
            "Beta": shrunk_beta,
            "Positive Beta": shrunk_pos,
            "Negative Beta": shrunk_neg,
            "Beta Ratio": shrunk_ratio,
            "Modified Beta": shrunk_mod,
            "Sector": sector,
            "Avg_MC": avg_mc,
            "Days Active": n_i,
            "DA %": da_pct,
            "Raw Beta": raw_beta,
            "Raw Positive Beta": raw_pos,
            "Raw Negative Beta": raw_neg
        })

    out_df = pd.DataFrame(results).sort_values("Ticker").reset_index(drop=True)
    out_path = OUT_DIR / f"{year}_log_part.csv"
    out_df.to_csv(out_path, index=False)

    print(f"✅ Saved {out_path} (rows: {len(out_df)})")
    print(f"Summary {year}: raw computed={raw_count}, shrunk applied={shrunk_count}, not computed={cannot_compute}")

print("\nAll years processed.")