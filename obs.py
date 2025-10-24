import pandas as pd
from pathlib import Path
import time

def main():
    base_dir = Path("C:/Users/furla/Documents/Personal/Uni/Tesi/beta-nonlineare/yobs")
    input_path = Path("C:/Users/furla/Documents/Personal/Uni/Tesi/beta-nonlineare/mcp.csv")

    base_dir.mkdir(parents=True, exist_ok=True)  # ensure folder exists

    print(f"\n→ Loading {input_path.name} ...")
    if not input_path.exists():
        print(f"✘ File not found: {input_path}")
        return

    df = pd.read_csv(input_path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index)
    df['Year'] = df.index.year

    for year, group in df.groupby('Year'):
        output_path = base_dir / f"{year}_obs.csv"

        total_days = len(group)
        days_active = group.drop(columns=['Year']).notna().sum()
        da_percent = (days_active / total_days)

        obs_df = pd.DataFrame({
            'Ticker': days_active.index,
            'Days Active': days_active.values,
            'DA %': da_percent.round(5)
        }).sort_values(by='Ticker', ascending=True)

        obs_df.to_csv(output_path, index=False)

        print(f"✅ Saved {year} observed % for {len(obs_df):,} tickers in \\yobs\\{year}_obs.csv")

if __name__ == "__main__":
    main()