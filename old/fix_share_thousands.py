import pandas as pd
from pathlib import Path

# --- CONFIG ---
folder_path = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare\tCP")

# --- PROCESS ---
for file_path in folder_path.glob("*.xlsx"):
    print(f"Processing {file_path.name}...")

    try:
        # Read Excel without converting dates to datetime
        df = pd.read_excel(file_path, dtype={"Shares": float})

        if "Shares" not in df.columns:
            print(f"⚠ Skipping {file_path.name}, no 'Shares' column found.")
            continue

        # Fix Shares: multiply by 1000 if value is not an integer
        def fix_shares(value):
            try:
                if not float(value).is_integer():
                    return float(value) * 1000
                return float(value)
            except Exception:
                return value

        df["Shares"] = df["Shares"].apply(fix_shares)

        # Force Date column to date only (no time)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date

        # Save back to Excel
        df.to_excel(file_path, index=False)
        print(f"✅ Updated {file_path.name}")
    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {e}")

print("Done.")