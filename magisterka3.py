import pandas as pd
import numpy as np
import warnings
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings('ignore')

df = pd.read_csv('master_panel_data.csv')
countries = df['Country'].unique()

def run_kao_test(df, dep_var):
    # Panel FE proxy: demeaning danych dla każdego kraju (pozbycie się stałych efektów)
    df_demeaned = df.copy()
    for c in countries:
        mask = df_demeaned['Country'] == c
        df_demeaned.loc[mask, dep_var] -= df_demeaned.loc[mask, dep_var].mean()
        df_demeaned.loc[mask, 'HICP'] -= df_demeaned.loc[mask, 'HICP'].mean()
        df_demeaned.loc[mask, 'IR10Y'] -= df_demeaned.loc[mask, 'IR10Y'].mean()
    
    # Regresja i test na resztach
    model = smf.ols(f'{dep_var} ~ HICP + IR10Y - 1', data=df_demeaned).fit()
    res = adfuller(model.resid, maxlag=1, autolag=None)
    return res[0], res[1]

print("=====================================================")
print("=== 1. PANEL COINTEGRATION TEST (KAO TEST) ===")
print("=====================================================")
kao_nl_stat, kao_nl_pval = run_kao_test(df, 'ln_TP_NL')
print(f"Non-Life Reserves (ln_TP_NL): ADF Stat = {kao_nl_stat:.4f} | p-value = {kao_nl_pval:.4f}")
kao_l_stat, kao_l_pval = run_kao_test(df, 'ln_TP_L')
print(f"Life Reserves (ln_TP_L):      ADF Stat = {kao_l_stat:.4f} | p-value = {kao_l_pval:.4f}")
print("\n")

print("=====================================================")
print("=== 2. PANEL ARDL ESTIMATION (MG APPROACH) ===")
print("=====================================================")

def estimate_ardl(df, dep_var):
    results = []
    for c in countries:
        df_c = df[df['Country'] == c].copy()
        
        # Przygotowanie zmiennych (Opóźnienia i Różnice)
        df_c['d_Y'] = df_c[dep_var].diff()
        df_c['Y_L1'] = df_c[dep_var].shift(1)
        df_c['HICP_L1'] = df_c['HICP'].shift(1)
        df_c['IR10Y_L1'] = df_c['IR10Y'].shift(1)
        df_c['d_HICP'] = df_c['HICP'].diff()
        df_c['d_IR10Y'] = df_c['IR10Y'].diff()
        df_c = df_c.dropna()
        
        # Równanie ARDL (Error Correction Form)
        formula = 'd_Y ~ Y_L1 + HICP_L1 + IR10Y_L1 + d_HICP + d_IR10Y + D_IFRS17'
        model = smf.ols(formula, data=df_c).fit()
        
        # Wyciąganie i kalkulacja mnożników długoterminowych
        phi = model.params['Y_L1']
        lr_hicp = -(model.params['HICP_L1'] / phi) if phi != 0 else np.nan
        lr_ir = -(model.params['IR10Y_L1'] / phi) if phi != 0 else np.nan
        sr_hicp = model.params['d_HICP']
        sr_ir = model.params['d_IR10Y']
        ifrs = model.params['D_IFRS17']
        
        results.append([phi, lr_hicp, lr_ir, sr_hicp, sr_ir, ifrs])
        
    res_df = pd.DataFrame(results, columns=['ECT (Speed of Adj.)', 'Long-Run: HICP', 'Long-Run: IR10Y', 'Short-Run: HICP', 'Short-Run: IR10Y', 'Break: IFRS17'])
    return res_df.mean()

print("--- MODEL 1: Non-Life Reserves (ln_TP_NL) ---")
nl_res = estimate_ardl(df, 'ln_TP_NL')
print(nl_res.round(4).to_string())

print("\n--- MODEL 2: Life Reserves (ln_TP_L) ---")
l_res = estimate_ardl(df, 'ln_TP_L')
print(l_res.round(4).to_string())
print("=====================================================")