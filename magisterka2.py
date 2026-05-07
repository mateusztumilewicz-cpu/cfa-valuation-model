import pandas as pd
import warnings
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings('ignore')

# Wczytanie gotowej, pełnej bazy danych (185 wierszy)
df = pd.read_csv('master_panel_data.csv')
variables = ['ln_TP_NL', 'ln_TP_L', 'HICP', 'IR10Y']
countries = df['Country'].unique()

print("=====================================================")
print("=== PANEL UNIT ROOT TEST: IM-PESARAN-SHIN (IPS) ===")
print("=====================================================\n")

for var in variables:
    # --- TEST W POZIOMACH (LEVELS) ---
    ips_stat_level = 0
    p_val_level = 0
    
    for c in countries:
        series = df[df['Country'] == c][var].dropna()
        # Mamy 37 kwartałów, więc opóźnienie maxlag=2 jest bardzo bezpieczne i naukowe
        res = adfuller(series, maxlag=2, autolag='AIC')
        ips_stat_level += res[0]
        p_val_level += res[1]
            
    ips_stat_level /= len(countries)
    p_val_level /= len(countries)

    # --- TEST W PIERWSZYCH RÓŻNICACH (FIRST DIFFERENCES) ---
    ips_stat_diff = 0
    p_val_diff = 0
    
    for c in countries:
        series_diff = df[df['Country'] == c][var].diff().dropna()
        res_diff = adfuller(series_diff, maxlag=2, autolag='AIC')
        ips_stat_diff += res_diff[0]
        p_val_diff += res_diff[1]
            
    ips_stat_diff /= len(countries)
    p_val_diff /= len(countries)

    print(f"--- Variable: {var} ---")
    print(f" [Levels]      IPS t-bar Stat: {ips_stat_level:8.4f} | Avg p-value: {p_val_level:.4f}")
    print(f" [Differences] IPS t-bar Stat: {ips_stat_diff:8.4f} | Avg p-value: {p_val_diff:.4f}")
    print("-" * 60)