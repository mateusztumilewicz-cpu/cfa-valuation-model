import yfinance as yf
import pandas as pd
import numpy as np
import requests
import warnings

# Ignorujemy ostrzeżenia z yfinance dla czystości konsoli
warnings.filterwarnings('ignore')

def get_correlations():
    print("1. Pobieram listę tickerów z Wikipedii (S&P 500)...")
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers)
    table = pd.read_html(io=response.text)
    
    df_tickers = table[0]
    tickers = df_tickers['Symbol'].tolist()
    
    # YFinance wymaga myślników zamiast kropek w nazwach tickerów
    tickers = [ticker.replace('.', '-') for ticker in tickers]
    
    print(f"2. Pobieram dzienne ceny dla {len(tickers)} spółek za ostatni rok.")
    data = yf.download(tickers, period="1y", interval="1d", progress=False)['Close']
    
    print("3. Obliczam dzienne stopy zwrotu...")
    returns = data.pct_change().dropna(how='all')
    
    print("4. Tworzę macierz korelacji...")
    corr_matrix = returns.corr()
    
    print("5. Analizuję macierz i szukam skrajności...")
    # Wyciągamy tylko dolny trójkąt macierzy, by uniknąć duplikatów i korelacji 1.0
    mask = np.tril(np.ones(corr_matrix.shape), k=-1).astype(bool)
    lower_triangle = corr_matrix.where(mask)
    stacked_lower = lower_triangle.stack()
    
    # --- LOGIKA 1: Szukanie korelacji najbliższej -1 ---
    negative_pairs = stacked_lower.sort_values(ascending=True)
    
    # --- LOGIKA 2: Szukanie korelacji najbliższej 0 ---
    zero_pairs_abs = stacked_lower.abs().sort_values(ascending=True)
    
    print("\n=======================================================")
    print("TOP 5 PAR O NAJBARDZIEJ UJEMNEJ KORELACJI (Cel: blisko -1)")
    print("=======================================================")
    for i, (stock1, stock2) in enumerate(negative_pairs.head(5).index):
        corr_val = negative_pairs.iloc[i]
        print(f"{i+1}. {stock1} oraz {stock2} | Korelacja: {corr_val:.6f}")
        
    print("\n=======================================================")
    print("TOP 5 PAR O KORELACJI NAJBLIŻSZEJ 0 (Brak korelacji)")
    print("=======================================================")
    for i, (stock1, stock2) in enumerate(zero_pairs_abs.head(5).index):
        original_corr = stacked_lower.loc[(stock1, stock2)]
        print(f"{i+1}. {stock1} oraz {stock2} | Korelacja: {original_corr:.6f}")

if __name__ == "__main__":
    get_correlations()