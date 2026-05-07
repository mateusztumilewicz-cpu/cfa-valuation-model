import pandas as pd

# Wczytanie danych
df = pd.read_csv('master_panel_data.csv')

print("===================================================================")
print("=== DESCRIPTIVE STATISTICS BY COUNTRY (FOR EXPANDED CHAPTER 4) ===")
print("===================================================================\n")

countries = df['Country'].unique()
variables = ['ln_TP_NL', 'ln_TP_L', 'HICP', 'IR10Y']

for c in countries:
    print(f"--- COUNTRY: {c.upper()} ---")
    subset = df[df['Country'] == c][variables]
    stats = subset.describe().loc[['mean', 'std', 'min', 'max']].T
    print(stats.round(4))
    print("\n")