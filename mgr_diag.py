import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

df = pd.read_csv('master_panel_data.csv')
countries = df['Country'].unique()

def get_ardl_residuals(df, dep_var):
    residuals = []
    for c in countries:
        df_c = df[df['Country'] == c].copy()
        df_c['d_Y'] = df_c[dep_var].diff()
        df_c['Y_L1'] = df_c[dep_var].shift(1)
        df_c['HICP_L1'] = df_c['HICP'].shift(1)
        df_c['IR10Y_L1'] = df_c['IR10Y'].shift(1)
        df_c['d_HICP'] = df_c['HICP'].diff()
        df_c['d_IR10Y'] = df_c['IR10Y'].diff()
        df_c = df_c.dropna()

        formula = 'd_Y ~ Y_L1 + HICP_L1 + IR10Y_L1 + d_HICP + d_IR10Y + D_IFRS17'
        model = smf.ols(formula, data=df_c).fit()
        df_c['Residuals'] = model.resid
        residuals.append(df_c[['Country', 'Residuals']])
    return pd.concat(residuals)

resid_nl = get_ardl_residuals(df, 'ln_TP_NL')
resid_l = get_ardl_residuals(df, 'ln_TP_L')

# Ustawienia stylu
plt.style.use('seaborn-v0_8-whitegrid')

# WYKRES 1: Non-Life
plt.figure(figsize=(8, 6))
sns.histplot(resid_nl['Residuals'], kde=True, color='blue', bins=20)
plt.title('Distribution of Non-Life ARDL Residuals', fontsize=14)
plt.xlabel('Residual Value', fontsize=12)
plt.ylabel('Frequency', fontsize=12)
plt.tight_layout()
plt.savefig('fig4_7_nonlife_resid.png', dpi=300)
plt.close()

# WYKRES 2: Life
plt.figure(figsize=(8, 6))
sns.histplot(resid_l['Residuals'], kde=True, color='green', bins=20)
plt.title('Distribution of Life ARDL Residuals', fontsize=14)
plt.xlabel('Residual Value', fontsize=12)
plt.ylabel('Frequency', fontsize=12)
plt.tight_layout()
plt.savefig('fig4_8_life_resid.png', dpi=300)
plt.close()

print("Gotowe! Zapisano dwa osobne pliki graficzne.")