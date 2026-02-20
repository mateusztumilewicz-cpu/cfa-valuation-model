import streamlit as st
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Transparent Monte Carlo DCF", layout="wide")

multi_class_tickers = ['GOOG', 'GOOGL', 'META', 'BRK.B', 'BRK-B', 'BRK.A', 'UAA', 'UA', 'ZILL', 'ZG']

# --- FUNKCJA POBIERANIA DANYCH ---
def get_company_data(ticker_str):
    if not ticker_str:
        return None
    try:
        stock = yf.Ticker(ticker_str)
        info = stock.info
        
        fcf = info.get('freeCashflow', 0) / 1e9 if info.get('freeCashflow') else 0
        total_debt = info.get('totalDebt', 0) if info.get('totalDebt') else 0
        total_cash = info.get('totalCash', 0) if info.get('totalCash') else 0
        net_debt = (total_debt - total_cash) / 1e9
        
        shares = info.get('sharesOutstanding', 0) / 1e6 if info.get('sharesOutstanding') else 100
        
        growth_est = info.get('earningsGrowth', 0.10) # 10% jako fallback gdy brak danych
        beta = info.get('beta', 1.0) if info.get('beta') else 1.0
        
        return {
            "name": info.get('longName', ticker_str),
            "fcf": fcf,
            "net_debt": net_debt,
            "shares": shares,
            "beta": beta,
            "market_price": info.get('currentPrice'),
            "growth_est": growth_est
        }
    except Exception as e:
        st.error(f"Błąd podczas pobierania danych dla {ticker_str}: {e}")
        return None

# --- GŁÓWNY INTERFEJS I EDUKACJA ---
st.title("DCF Valuation Tool")

with st.expander("📖 Jak działa ten model DCF? (Mechanika 3 faz)"):
    st.markdown("""
    Nasz model to klasyczny, 3-fazowy model oparty na wolnych przepływach pieniężnych (FCF):
    1. **Faza 1 (Lata 1-5):** Dynamiczny wzrost. Przepływy rosną w tempie, które sam ustalisz na suwaku.
    2. **Faza 2 (Lata 6-10):** Liniowe wygaszanie (Fade). Wzrost firmy płynnie spada z wysokiego poziomu (z Fazy 1) aż do stabilnego poziomu terminalnego w roku 10.
    3. **Faza 3 (Wartość Terminalna - TV):** Wycena "reszty życia" firmy po 10 roku. Możesz użyć do tego wzrostu wieczystego (Gordon Growth Model) lub wyjścia przez wskaźnik mnożnikowy (Exit Multiple).
    """)

ticker_input = st.text_input("Wpisz Ticker spółki (np. GOOGL, AAPL, UBER):", value="").upper()

if ticker_input:
    with st.spinner('Pobieram dane z Yahoo Finance...'):
        data = get_company_data(ticker_input)
    
    if data:
        st.header(f"Analiza: {data['name']}")
        
        if ticker_input in multi_class_tickers:
            st.warning(f"⚠️ **OSTRZEŻENIE:** {ticker_input} ma strukturę wieloklasową. Sprawdź i popraw łączną liczbę akcji poniżej!")
            
        st.divider()
        st.subheader("📝 KROK 1: Fundamentalne dane wejściowe")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            val_fcf = st.number_input("FCF (Year 0) [$ bn]", value=float(data['fcf']))
        with col2:
            val_debt = st.number_input("Dług Netto [$ bn]", value=float(data['net_debt']))
        with col3:
            val_shares = st.number_input("Liczba akcji [m]", value=float(data['shares']))

        st.divider()
        
        # --- TRANSPARENTNY CAPM & WACC ---
        st.subheader("⚖️ KROK 2: Kalkulacja WACC i CAPM (Pełna transparentność)")
        st.info("Poniżej znajdują się założenia makroekonomiczne. Domyślne wartości to aktualne szacunki dla rynku USA, ale możesz je w pełni edytować.")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            val_rf = st.number_input("Stopa wolna od ryzyka (Rf) [%]", value=4.20, help="Np. 10-letnie obligacje USA") / 100
        with c2:
            val_erp = st.number_input("Premia rynkowa (ERP) [%]", value=5.50, help="Dodatkowy zwrot wymagany za ryzyko akcji") / 100
        with c3:
            val_beta = st.number_input("Beta (Zmienność spółki)", value=float(data['beta']))
        with c4:
            val_cost_debt = st.number_input("Koszt długu (Rd) po opodatkowaniu [%]", value=4.50) / 100
            
        # Obliczenia WACC na oczach użytkownika
        re = val_rf + (val_beta * val_erp)
        st.write(f"👉 **Koszt Kapitału Własnego (Re) z modelu CAPM wyniósł:** {(re*100):.2f}%")
        
        # Zakładamy domyślnie 90% Equity, 10% Debt dla ułatwienia (też można by to rozbić, ale WACC z suwakiem daje kontrolę)
        sug_wacc = (re * 0.9) + (val_cost_debt * 0.1)
        wacc_final = st.slider("Zaakceptuj lub dostosuj finalny WACC do modelu [%]", 4.0, 16.0, float(sug_wacc*100)) / 100

        st.divider()

        # --- WZROST I WARTOŚĆ TERMINALNA (WYBÓR) ---
        st.subheader("📈 KROK 3: Dynamika wzrostu i Wartość Terminalna")
        
        col_g, col_tv = st.columns(2)
        with col_g:
            safe_growth = max(0.0, min(data['growth_est'], 0.40))
            g_high = st.slider("Wzrost FCF (Lata 1-5) [%]", 0.0, 40.0, float(safe_growth*100)) / 100
            st.caption(f"💡 Sugerowany krótko-średnioterminowy wzrost wg Yahoo: **{data['growth_est']*100:.1f}%**")
            
        with col_tv:
            tv_method = st.radio("Metoda wyliczenia Wartości Terminalnej (TV)", ["Wzrost wieczysty (Gordon Growth)", "Mnożnik wyjścia (Exit Multiple)"])
            
            if tv_method == "Wzrost wieczysty (Gordon Growth)":
                g_term = st.number_input("Wzrost terminalny [%]", value=2.5, help="Zwykle na poziomie długoterminowej inflacji (2-3%)") / 100
            else:
                exit_mult = st.number_input("Mnożnik wyjścia (EV/FCF)", value=15.0, help="Za ile krotności wygenerowanej gotówki firma zostanie sprzedana w 10 roku.")

        sims = st.select_slider("Liczba symulacji Monte Carlo", options=[1000, 5000, 10000], value=5000)
        
        st.divider()

        # --- OBLICZENIA ---
        if st.button("🚀 Uruchom Kalkulację DCF"):
            with st.spinner('Trwają obliczenia...'):
                results = []
                for _ in range(sims):
                    s_wacc = np.random.normal(wacc_final, 0.007)
                    s_g = np.random.normal(g_high, 0.02)
                    
                    pv_projection = 0
                    current_fcf = val_fcf
                    
                    for year in range(1, 11):
                        if year <= 5:
                            growth = s_g
                        else:
                            # Faza 2: Fade z s_g do 0 (jeśli Multiple) lub g_term (jeśli Gordon)
                            target_g = g_term if tv_method == "Wzrost wieczysty (Gordon Growth)" else 0.02
                            fade_factor = (year - 5) / 5
                            growth = s_g * (1 - fade_factor) + target_g * fade_factor
                        
                        current_fcf *= (1 + growth)
                        pv_projection += current_fcf / ((1 + s_wacc)**year)
                    
                    # Faza 3: Terminal Value wg wybranej metody
                    if tv_method == "Wzrost wieczysty (Gordon Growth)":
                        tv = (current_fcf * (1 + g_term)) / (max(s_wacc - g_term, 0.005))
                    else:
                        # Mnożnik dodaje też trochę losowości, żeby Monte Carlo działało na multiple (np. +/- 1.0)
                        s_mult = np.random.normal(exit_mult, 1.0)
                        tv = current_fcf * s_mult
                        
                    pv_tv = tv / ((1 + s_wacc)**10)
                    
                    enterprise_value = pv_projection + pv_tv
                    equity_value = enterprise_value - val_debt
                    share_price = max(equity_value * 1000 / val_shares, 0)
                    results.append(share_price)

                # --- WYNIKI ---
                mean_res = np.mean(results)
                p5 = np.percentile(results, 5)
                p95 = np.percentile(results, 95)
                
                st.success("Obliczenia zakończone!")
                res1, res2, res3 = st.columns(3)
                res1.metric("Pesymistycznie (5%)", f"${p5:.2f}")
                
                if data['market_price']:
                    delta_pct = f"{(mean_res/data['market_price']-1)*100:.1f}% vs Market"
                else:
                    delta_pct = "Brak ceny rynkowej"
                    
                res2.metric("Fair Value (Średnia)", f"${mean_res:.2f}", delta=delta_pct)
                res3.metric("Optymistycznie (95%)", f"${p95:.2f}")

                fig, ax = plt.subplots(figsize=(10, 4))
                sns.histplot(results, kde=True, color="skyblue", bins=80, ax=ax)
                ax.axvline(mean_res, color='red', linewidth=2, label=f'Fair Value: ${mean_res:.2f}')
                ax.axvline(p5, color='orange', linestyle='--', label='5% Percentile')
                ax.axvline(p95, color='green', linestyle='--', label='95% Percentile')
                
                if data['market_price']:
                    ax.axvline(data['market_price'], color='black', linewidth=3, label=f'Market Price: ${data["market_price"]:.2f}')
                
                ax.set_title("Rozkład Prawdopodobieństwa Ceny Akcji")
                ax.legend()
                st.pyplot(fig)