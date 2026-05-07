import pandas as pd
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings('ignore')

# Wczytanie naszej ostatecznej bazy 
df = pd.read_csv('master_panel_data.csv')

print("==========================================================")
print("=== ROBUSTNESS CHECK: STATIC PANEL FIXED EFFECTS (OLS) ===")
print("==========================================================\n")

# Model statyczny OLS z efektami stałymi dla krajów (C(Country))
model_nl_fe = smf.ols('ln_TP_NL ~ HICP + IR10Y + C(Country)', data=df).fit()
print("--- STATIC MODEL 1: NON-LIFE RESERVES ---")
print(model_nl_fe.summary().tables[1])

model_l_fe = smf.ols('ln_TP_L ~ HICP + IR10Y + C(Country)', data=df).fit()
print("\n--- STATIC MODEL 2: LIFE RESERVES ---")
print(model_l_fe.summary().tables[1])