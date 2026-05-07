import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

df = pd.read_csv('master_panel_data.csv')
corr_data = df[['ln_TP_NL', 'ln_TP_L', 'HICP', 'IR10Y']]
corr_matrix = corr_data.corr()

plt.figure(figsize=(8, 6))
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1, fmt=".3f", linewidths=0.5)
plt.title('Pearson Correlation Matrix of Panel Variables', fontsize=14)
plt.tight_layout()
plt.savefig('fig4_correlation_heatmap.png', dpi=300)

print("Zapisano fig4_correlation_heatmap.png")