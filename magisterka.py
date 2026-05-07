import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

top_5 = ['Germany', 'France', 'Italy', 'Spain', 'Netherlands']

# Super elastyczne dopasowywanie krajów (ignoruje dziwne dopiski Eurostatu)
def get_clean_country(c):
    c_up = str(c).upper()
    if 'GERMANY' in c_up: return 'Germany'
    if 'FRANCE' in c_up: return 'France'
    if 'ITALY' in c_up: return 'Italy'
    if 'SPAIN' in c_up: return 'Spain'
    if 'NETHERLANDS' in c_up: return 'Netherlands'
    return None

# ==========================================
# 1. OBRÓBKA DANYCH EIOPA (REZERWY Z CSV)
# ==========================================
print("Przetwarzanie surowej bazy EIOPA (CSV)...")
df_eiopa = pd.read_csv('eiopa.csv', encoding='latin1', low_memory=False)

df_eiopa['Country'] = df_eiopa['Reporting country'].apply(get_clean_country)
df_filtered = df_eiopa[(df_eiopa['Country'].notnull()) & (df_eiopa['Item code'].isin(['R0510', 'R0600']))].copy()

df_filtered['Value'] = pd.to_numeric(df_filtered['Value'].astype(str).str.replace(',', '.'), errors='coerce')
df_filtered.rename(columns={'Reference period': 'Quarter'}, inplace=True)

df_reserves = df_filtered.groupby(['Country', 'Quarter', 'Item code'])['Value'].sum().reset_index()
df_reserves = df_reserves.pivot(index=['Country', 'Quarter'], columns='Item code', values='Value').reset_index()
df_reserves.rename(columns={'R0510': 'TP_NL', 'R0600': 'TP_L'}, inplace=True)
df_reserves.columns.name = None

df_reserves['ln_TP_NL'] = np.log(df_reserves['TP_NL'])
df_reserves['ln_TP_L'] = np.log(df_reserves['TP_L'])

df_reserves['Quarter'] = df_reserves['Quarter'].astype(str).str.strip()
df_reserves[['Year', 'Q']] = df_reserves['Quarter'].str.split(' ', expand=True)
df_reserves['Year'] = pd.to_numeric(df_reserves['Year'], errors='coerce')
df_reserves = df_reserves[(df_reserves['Year'] > 2016) | ((df_reserves['Year'] == 2016) & (df_reserves['Q'].isin(['Q3', 'Q4'])))]

# ==========================================
# FUNKCJA DO ROZKODOWYWANIA EUROSTATU
# ==========================================
def process_eurostat(file_path, value_name):
    xls = pd.ExcelFile(file_path)
    correct_sheet = None
    header_row = None

    # Inteligentne szukanie zakładki z danymi (musi mieć 'TIME'/'GEO' oraz lata np. '2020')
    for sheet in xls.sheet_names:
        temp = pd.read_excel(file_path, sheet_name=sheet, header=None, nrows=50)
        for idx, row in temp.iterrows():
            row_str = row.astype(str).str.upper()
            if (row_str.str.contains('TIME|GEO').any()) and (row_str.str.contains('201|202').any()):
                correct_sheet = sheet
                header_row = idx
                break
        if correct_sheet is not None:
            break

    if correct_sheet is None:
        raise ValueError(f"Nie znaleziono prawidłowej zakładki z danymi w pliku {file_path}")

    df = pd.read_excel(file_path, sheet_name=correct_sheet, header=header_row)

    # Eurostat dodaje puste kolumny-odstępy (Unnamed) -> wyrzucamy je
    valid_cols = [col for col in df.columns if not str(col).startswith('Unnamed')]
    df = df[valid_cols]

    # Pierwsza kolumna to zawsze nazwy państw
    geo_col = df.columns[0]
    df.rename(columns={geo_col: 'Country'}, inplace=True)
    df['Country'] = df['Country'].apply(get_clean_country)
    df = df[df['Country'].notnull()]

    # Meltowanie
    date_cols = [col for col in df.columns if str(col).startswith('20')]
    df_long = pd.melt(df, id_vars=['Country'], value_vars=date_cols, var_name='Month', value_name=value_name)
    df_long[value_name] = pd.to_numeric(df_long[value_name].astype(str).str.replace(':', ''), errors='coerce')

    # Wyciąganie dat
    extracted = df_long['Month'].astype(str).str.extract(r'(\d{4})\D*(\d{2})')
    df_long['Year'] = extracted[0]
    df_long['Month_Num'] = pd.to_numeric(extracted[1], errors='coerce')
    
    df_long = df_long.dropna(subset=['Month_Num'])
    df_long['Month_Num'] = df_long['Month_Num'].astype(int)

    df_long['Q'] = 'Q' + ((df_long['Month_Num'] - 1) // 3 + 1).astype(str)
    df_long['Quarter'] = df_long['Year'] + ' ' + df_long['Q']
    df_long['Quarter'] = df_long['Quarter'].astype(str).str.strip()
    
    return df_long

# ==========================================
# 2. INFLACJA I STOPY PROC.
# ==========================================
print("\nPrzetwarzanie danych Eurostat (Inflacja)...")
df_inf_long = process_eurostat('inflacja.xlsx', 'HICP')
df_hicp_q = df_inf_long.groupby(['Country', 'Quarter'])['HICP'].mean().reset_index()

print("Przetwarzanie danych Eurostat (Stopy procentowe)...")
df_ir_long = process_eurostat('stopy.xlsx', 'IR10Y')
df_ir_q = df_ir_long[df_ir_long['Month_Num'].isin([3, 6, 9, 12])][['Country', 'Quarter', 'IR10Y']]

# ==========================================
# 3. ŁĄCZENIE W PANEL
# ==========================================
print("\n--- TEST KONTROLNY PRZED ZŁĄCZENIEM ---")
print("Kwartały EIOPA:    ", df_reserves['Quarter'].unique()[:3])
print("Kwartały INFLACJA: ", df_hicp_q['Quarter'].unique()[:3])
print("Kwartały STOPY:    ", df_ir_q['Quarter'].unique()[:3])
print("---------------------------------------\n")

print("Łączenie wszystkich baz w panelowy monolit...")
df_final = df_reserves[['Country', 'Quarter', 'Year', 'Q', 'TP_NL', 'TP_L', 'ln_TP_NL', 'ln_TP_L']]
df_final = pd.merge(df_final, df_hicp_q, on=['Country', 'Quarter'], how='left')
df_final = pd.merge(df_final, df_ir_q, on=['Country', 'Quarter'], how='left')

# Wyrzucamy ewentualne braki danych
df_final = df_final.dropna(subset=['ln_TP_NL', 'ln_TP_L', 'HICP', 'IR10Y'])
df_final['D_IFRS17'] = np.where(df_final['Year'].astype(int) >= 2023, 1, 0)
df_final = df_final.sort_values(by=['Country', 'Quarter']).reset_index(drop=True)

df_final.to_csv('master_panel_data.csv', index=False)
print("Sukces! Dane połączone. Plik 'master_panel_data.csv' jest gotowy.")

print("\n=============================================")
print("=== TABELA 4.1: DESCRIPTIVE STATISTICS ===")
print("=============================================")
desc_stats = df_final[['ln_TP_NL', 'ln_TP_L', 'HICP', 'IR10Y']].describe().T
desc_stats = desc_stats[['mean', 'std', 'min', 'max']]
desc_stats.columns = ['Mean', 'Std. Dev.', 'Min', 'Max']
print(desc_stats.round(4))