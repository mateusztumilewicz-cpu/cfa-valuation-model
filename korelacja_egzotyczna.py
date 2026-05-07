import yfinance as yf
import pandas as pd
import numpy as np
import requests
import warnings

warnings.filterwarnings('ignore')

def full_german_market_correlations():
    print("1. Pobieram listę WSZYSTKICH niemieckich spółek ze strony TopForeignStocks...")
    url = "https://topforeignstocks.com/stock-lists/the-list-of-listed-companies-in-germany/"
    
    # Przebieramy bota za przeglądarkę
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers)
    
    try:
        # Wczytujemy tabelę ze strony
        tables = pd.read_html(io=response.text)
        df = tables[0]
        # Pobieramy tickery i dodajemy rozszerzenie giełdy we Frankfurcie (.DE)
        tickers = df['Ticker'].dropna().astype(str).tolist()
        tickers = [t.strip() for t in tickers]
    except Exception as e:
        print("Błąd podczas pobierania tabeli. Strona mogła zablokować bota.")
        return
        
    # Usuwamy ewentualne duplikaty
    tickers = list(set(tickers))
    print(f"-> Znalazłem {len(tickers)} Prawdziwych Niemieckich Spółek (cały ich rodzimy rynek)!")
    
    print("2. Pobieram dzienne ceny za ostatni rok. To zajmie kilkanaście sekund...")
    data = yf.download(tickers, period="1y", interval="1d", progress=False)['Close']
    
    print("3. Czyszczę dane (usuwam spółki nieaktywne, groszówki i braki w danych)...")
    data = data.dropna(thresh=len(data) * 0.9, axis=1)
    
    # Filtr - omijamy spółki-zombie
    returns = data.pct_change().dropna(how='all')
    zero_movements_pct = (returns == 0.0).mean()
    valid_tickers = zero_movements_pct[zero_movements_pct < 0.05].index
    returns = returns[valid_tickers]
    
    print(f"-> Do ostatecznej bitwy staje {len(valid_tickers)} płynnych, niemieckich biznesów.")
    
    print("4. Tworzę macierz korelacji i szukam skrajnych przeciwieństw...")
    corr_matrix = returns.corr()
    
    mask = np.tril(np.ones(corr_matrix.shape), k=-1).astype(bool)
    lower_triangle = corr_matrix.where(mask)
    stacked_lower = lower_triangle.stack()
    sorted_pairs = stacked_lower.sort_values(ascending=True)
    
    print("\n=======================================================")
    print("TOP 10 PAR O NAJBARDZIEJ UJEMNEJ KORELACJI (CAŁY RYNEK NIEMIEC)")
    print("=======================================================")
    
    for i, (stock1, stock2) in enumerate(sorted_pairs.head(10).index):
        correlation_value = sorted_pairs.loc[(stock1, stock2)]
        
        # Próbujemy szybko pobrać nazwy z Yahoo, żeby wynik był czytelny
        try:
            name1 = yf.Ticker(stock1).info.get('shortName', stock1)
            name2 = yf.Ticker(stock2).info.get('shortName', stock2)
        except:
            name1, name2 = stock1, stock2
            
        print(f"{i+1}. {stock1} ({name1}) oraz {stock2} ({name2}) | Korelacja: {correlation_value:.4f}")

if __name__ == "__main__":
    full_german_market_correlations()