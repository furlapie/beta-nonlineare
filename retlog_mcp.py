import pandas as pd
import numpy as np
import time
from pathlib import Path

def main():
    start_time = time.time()
    input_path = Path("mcp.csv")
    simple_output_path = Path("retm.csv")
    log_output_path = Path("logm.csv")

    print(f"\n→ Loading {input_path.name} ...")
    if not input_path.exists():
        print(f"✘ File not found: {input_path}")
        return

    # Load dataset
    df = pd.read_csv(input_path, index_col=0)
    print(f"✔ Loaded {len(df):,} rows × {len(df.columns):,} tickers")

    # --- SIMPLE RETURNS ---
    print("→ Computing simple returns ...")
    simple_returns = (df / df.shift(1)) - 1
    simple_returns = simple_returns.iloc[1:]
    simple_returns.to_csv(simple_output_path)
    print(f"✔ Saved {simple_output_path.name} ({len(simple_returns):,} rows)")

    # --- LOG RETURNS ---
    print("→ Computing log returns ...")
    log_returns = np.log(df / df.shift(1))
    log_returns = log_returns.iloc[1:]
    log_returns.to_csv(log_output_path)
    print(f"✔ Saved {log_output_path.name} ({len(log_returns):,} rows)")

    # --- Summary ---
    duration = time.time() - start_time
    print(f"\n✅ Completed in {duration:.1f}s")
    print(f"Rows: {len(df):,}, Columns: {len(df.columns):,}")

if __name__ == "__main__":
    main()