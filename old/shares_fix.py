import pandas as pd
from pathlib import Path

# --- CONFIG ---
base_folder = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare")
shares_folder = base_folder / "shares"
wk_by_date_path = base_folder / "wk_by_date.csv"
output_folder = shares_folder / "csv"

output_folder.mkdir(exist_ok=True)

# --- Load reference dates ---
wk_dates = pd.read_csv(wk_by_date_path)
wk_dates["Date"] = pd.to_datetime(wk_dates["Date"])
wk_dates_set = set(wk_dates["Date"])

# --- Tracker for missing A2 cells ---
empty_a2_files = []

# --- PROCESS EACH FILE ---
for file_path in shares_folder.glob("*.xlsx"):
    print(f"Processing {file_path.name}...")

    try:
        # Read Excel
        df = pd.read_excel(file_path)

        # Check if A2 (row index 1, column index 0) is empty
        if df.shape[0] > 1 and pd.isna(df.iloc[1, 0]):
            empty_a2_files.append(file_path.name)

        # Check required columns
        if "Date" not in df.columns or "Shares" not in df.columns:
            print(f"⚠ Skipping {file_path.name}, missing columns.")
            continue

        # Clean and convert
        df["Date"] = pd.to_datetime(df["Date"])
        df["Shares"] = pd.to_numeric(df["Shares"], errors="coerce") * 1_000_000  # multiply by 1,000,000

        # --- Determine expansion range ---
        min_date = min(df["Date"].min(), pd.Timestamp("2020-01-01"))
        max_date = max(df["Date"].max(), pd.Timestamp("2025-01-01"))

        # Create daily date range and reindex
        full_dates = pd.date_range(start=min_date, end=max_date, freq="D")
        df = df.set_index("Date").reindex(full_dates)
        df.index.name = "Date"

        # --- Interpolate linearly and round ---
        df["Shares"] = df["Shares"].interpolate(method="linear").round(0)

        # --- Fill any remaining NaNs ---
        df["Shares"] = df["Shares"].ffill().bfill()

        # --- Filter by wk_by_date.csv ---
        df = df.reset_index()
        df = df[df["Date"].isin(wk_dates_set)]

        # --- Save as CSV ---
        output_csv = output_folder / f"{file_path.stem}.csv"
        df.to_csv(output_csv, index=False)
        print(f"✅ Saved {output_csv.name}")

    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {e}")

# --- Summary ---
print("\n=== SUMMARY ===")
if empty_a2_files:
    print("⚠ Files with empty A2 cell:")
    for f in empty_a2_files:
        print(f"   - {f}")
else:
    print("✅ No files with empty A2 cell detected.")

print("Done.")