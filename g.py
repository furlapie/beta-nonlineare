import pandas as pd
import matplotlib.pyplot as plt
import sys
from pathlib import Path

# === CONFIG ===
base = Path(r"C:\Users\furla\Documents\Personal\Uni\Tesi\beta-nonlineare")
combined_file = base / "nbetafinish" / "mnbf.csv"        # all tickers all years
sector_tot_file = base / "nbetasec_full.csv"              # sector-weighted data

# === Metric selection ===
metric_choice = input("Visualizzare grafici per (1) Beta Ratio o (2) Modified Beta? ").strip()
if metric_choice == "1":
    metric = "Beta Ratio"
    weighted_metric = "Weighted_Beta_Ratio"
elif metric_choice == "2":
    metric = "Modified Beta"
    weighted_metric = "Weighted_Modified_Beta"
else:
    print("Scelta non valida.")
    sys.exit()

# === Year selection ===
year = input("Seleziona l'anno (2020–2024) o All: ").strip()
if year not in ["2020", "2021", "2022", "2023", "2024", "All"]:
    print("Anno non valido.")
    sys.exit()

# === Load data once ===
if not combined_file.exists():
    print(f"File non trovato: {combined_file}")
    sys.exit()

tickers = pd.read_csv(combined_file)
if year != "All":
    tickers = tickers[tickers["Year"] == int(year)]

# === Helper for labels ===
def add_labels(ax, rects):
    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=8, rotation=45)

# === Plotting ===
def plot_top_bottom(data, year, metric, top=True, n=20):
    title_type = "Top" if top else "Bottom"
    title = f"{title_type} {n} {metric}s – {year}"

    if top:
        subset = data.nlargest(n, metric)
    else:
        subset = data.nsmallest(n, metric)

    plt.figure(figsize=(16, 7))
    labels = subset["Ticker"] + " (" + subset["Year"].astype(str) + ")"
    bars = plt.bar(labels, subset[metric])
    plt.title(title)
    plt.xlabel("Ticker (Anno)")
    plt.ylabel(metric)
    plt.xticks(rotation=90, fontsize=8)

    for bar in bars:
        h = bar.get_height()
        y_pos = h + 0.02 if h >= 0 else h - 0.02
        va = 'bottom' if h >= 0 else 'top'
        plt.text(bar.get_x() + bar.get_width()/2, y_pos, f'{h:.2f}', ha='center', va=va, rotation=90, fontsize=7)

    plt.tight_layout()
    plt.show()

def plot_sector(data, sector_name, label, metric):
    sub = data[data["Sector"] == sector_name].sort_values(by=metric, ascending=False)
    if sub.empty:
        print(f"Nessun dato per {sector_name} ({label})")
        return

    def color_map(v):
        if v < 0.6: return "blue"
        elif v < 0.8: return "skyblue"
        elif v < 1: return "yellow"
        elif v < 1.3: return "orange"
        else: return "red"

    colors = sub[metric].apply(color_map)
    sub["Label"] = sub["Ticker"].astype(str) + " (" + sub["Year"].astype(str) + ")"

    plt.figure(figsize=(10, 8))
    bars = plt.barh(sub["Label"], sub[metric], color=colors)
    for bar in bars:
        w = bar.get_width()
        plt.text(w, bar.get_y() + bar.get_height()/2, f'{w:.2f}', va='center', ha='left', fontsize=8)
    plt.axvline(x=1, color="dimgray", linestyle="--", linewidth=1)
    plt.xlabel(metric)
    plt.ylabel("Titoli (Anno)")
    plt.title(f"{sector_name} – {metric} ({label}, N={len(sub)})")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.show()

def plot_sector_summary(sector_file, year, weighted_metric, metric):
    df = pd.read_csv(sector_file)
    if year != "All":
        df = df[df["Year"] == int(year)]
    if df.empty:
        print(f"Nessun dato per l'anno {year}")
        return

    df = df.sort_values(weighted_metric, ascending=False)

    plt.figure(figsize=(10, 6))
    bars = plt.bar(df["Sector"], df[weighted_metric], color="teal")
    plt.axhline(y=1, color="gray", linestyle="--")
    plt.title(f"Settori – {metric} ponderato ({year})")
    plt.ylabel(weighted_metric)
    plt.xticks(rotation=45, ha="right")
    for bar in bars:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, h, f'{h:.2f}', ha='center', va='bottom', fontsize=8)
    plt.tight_layout()
    plt.show()

# === Main interactive loop ===
sector_map = {
    "1": "Communication Services",
    "2": "Consumer Discretionary",
    "3": "Consumer Staples",
    "4": "Energy",
    "5": "Financials",
    "6": "Health Care",
    "7": "Industrials",
    "8": "Information Technology",
    "9": "Materials",
    "10": "Real Estate",
    "11": "Utilities"
}

while True:
    print(f"\n=== MENU ({metric}) ===")
    if year == "All":
        print(f"01 = Top 100 per {metric}")
        print(f"02 = Bottom 100 per {metric}")
    else:
        print(f"01 = Top 20 per {metric}")
        print(f"02 = Bottom 20 per {metric}")
    print(f"12 = Settori (media ponderata {metric})")

    for k, v in sector_map.items():
        print(f"{k} = {v}")

    print("e = Esci")

    choice = input("\nInserisci il numero: ").strip().lower()
    if choice == "e":
        print("Uscita dal programma.")
        break

    if choice == "01":
        n = 100 if year == "All" else 20
        label = "2020–2024" if year == "All" else year
        plot_top_bottom(tickers, label, metric, top=True, n=n)
    elif choice == "02":
        n = 100 if year == "All" else 20
        label = "2020–2024" if year == "All" else year
        plot_top_bottom(tickers, label, metric, top=False, n=n)
    elif choice == "12":
        plot_sector_summary(sector_tot_file, year, weighted_metric, metric)
    elif choice in sector_map:
        label = "2020–2024" if year == "All" else year
        plot_sector(tickers, sector_map[choice], label, metric)
    else:
        print("Scelta non valida.")