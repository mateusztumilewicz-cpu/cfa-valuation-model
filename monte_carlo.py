import streamlit as st
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Transparent Monte Carlo DCF", layout="wide")

multi_class_tickers = ['GOOG', 'GOOGL', 'META', 'BRK.B', 'BRK-B', 'BRK.A', 'UAA', 'UA', 'ZILL', 'ZG']

# --- FUNKCJA POBIERANIA DANYCH ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_company_data(ticker_str):
    if not ticker_str:
        return None
    try:
        stock = yf.Ticker(ticker_str)
        info = stock.info
        
        fcf = info.get('freeCashflow', 0) / 1e9 if info.get('freeCashflow') else 0.0
        
        # Pobieramy zarówno dług całkowity (do wag WACC), jak i gotówkę (do długu netto)
        total_debt_raw = info.get('totalDebt', 0) if info.get('totalDebt') else 0.0
        total_cash = info.get('totalCash', 0) if info.get('totalCash') else 0.0
        
        total_debt = total_debt_raw / 1e9
        net_debt = (total_debt_raw - total_cash) / 1e9
        
        shares = info.get('sharesOutstanding', 0) / 1e6 if info.get('sharesOutstanding') else 0.0
        growth_est = info.get('earningsGrowth', 0.0) if info.get('earningsGrowth') is not None else 0.0
        beta = info.get('beta', 0.0) if info.get('beta') else 0.0
        market_price = info.get('currentPrice', 0.0)
        
        return {
            "name": info.get('longName', ticker_str),
            "fcf": fcf,
            "total_debt": total_debt,  # Zapisujemy dług całkowity dla wag WACC
            "net_debt": net_debt,      # Dług netto do ostatecznej wyceny
            "shares": shares,
            "beta": beta,
            "market_price": market_price,
            "growth_est": growth_est
        }
    except Exception as e:
        st.error(f"Błąd API Yahoo Finance: {e}. Przełącz na tryb ręczny powyżej.")
        return None

# --- GŁÓWNY INTERFEJS ---
st.title("💎 Transparent DCF Valuation Tool")

with st.expander("📖 Jak działa ten model DCF? (Mechanika 3 faz)"):
    st.markdown("""
    Nasz model to klasyczny, 3-fazowy model oparty na wolnych przepływach pieniężnych (FCF):
    1. **Faza 1 (Lata 1-5):** Dynamiczny wzrost. Przepływy rosną w tempie, które sam wpiszesz.
    2. **Faza 2 (Lata 6-10):** Liniowe wygaszanie (Fade). Wzrost firmy płynnie spada z wysokiego poziomu (z Fazy 1) aż do stabilnego poziomu terminalnego w roku 10.
    3. **Faza 3 (Wartość Terminalna - TV):** Wycena "reszty życia" firmy po 10 roku. Używamy wzrostu wieczystego (Gordon Growth Model) lub wyjścia przez wskaźnik mnożnikowy (Exit Multiple).
    """)

st.divider()

st.subheader("⚙️ Wybierz tryb działania aplikacji")
input_mode = st.radio(
    "Jak chcesz wprowadzić dane do modelu?",
    ("Pobierz automatycznie z Yahoo Finance", "Wpisz wszystkie dane ręcznie (Tryb Offline)")
)

data = None

if input_mode == "Pobierz automatycznie z Yahoo Finance":
    ticker_input = st.text_input("Wpisz Ticker spółki (np. GOOGL, AAPL, UBER):", value="").upper()
    if ticker_input:
        with st.spinner('Pobieram dane...'):
            data = get_company_data(ticker_input)
            
        if data:
            missing = []
            if data['shares'] == 0.0: missing.append("Liczba akcji")
            if data['beta'] == 0.0: missing.append("Beta")
            if data['growth_est'] == 0.0: missing.append("Szacowany wzrost (Lata 1-5)")
            
            if missing:
                st.error(f"🚨 **UWAGA! Yahoo Finance nie dostarczyło wszystkich danych.** Brakujące parametry to: **{', '.join(missing)}**. \n\nZostały one wyzerowane. **Musisz je odszukać w raportach i wpisać ręcznie w polach poniżej**, inaczej wycena będzie błędna!")
            
            if ticker_input in multi_class_tickers:
                st.warning(f"⚠️ **OSTRZEŻENIE:** {ticker_input} ma strukturę wieloklasową. Sprawdź i popraw łączną liczbę akcji poniżej!")
else:
    st.info("💡 Tryb ręczny: Pola wejściowe zostały odblokowane. Wpisz własne dane z raportów spółki.")
    data = {
        "name": "Moja Spółka (Wycena ręczna)", "fcf": 0.0, "total_debt": 0.0, "net_debt": 0.0, 
        "shares": 0.0, "beta": 0.0, "market_price": 0.0, "growth_est": 0.0
    }

if data:
    st.divider()
    st.subheader("📝 KROK 1: Fundamentalne dane wejściowe")
    
    if input_mode == "Wpisz wszystkie dane ręcznie (Tryb Offline)":
        data['name'] = st.text_input("Nazwa wycenianej firmy:", value=data['name'])
        data['market_price'] = st.number_input("Cena rynkowa do porównania [$] (Opcjonalnie):", value=float(data['market_price']))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        val_fcf = st.number_input("FCF (Year 0) [$ bn]", value=float(data['fcf']))
    with col2:
        val_debt = st.number_input("Dług Netto [$ bn]", value=float(data['net_debt']))
    with col3:
        val_shares = st.number_input("Liczba akcji [m]", value=float(data['shares']))

    st.divider()
    
    st.subheader("⚖️ KROK 2: Kalkulacja WACC i CAPM (Struktura Kapitału)")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        val_rf = st.number_input("Stopa wolna od ryzyka (Rf) [%]", value=4.20) / 100
    with c2:
        val_erp = st.number_input("Premia rynkowa (ERP) [%]", value=5.50) / 100
    with c3:
        val_beta = st.number_input("Beta (Zmienność spółki)", value=float(data['beta']))
    with c4:
        val_cost_debt = st.number_input("Koszt długu (Rd) po opodatkowaniu [%]", value=4.50) / 100
        
    # --- AUTOMATYCZNE WYLICZANIE WAG KAPITAŁU ---
    # Market Cap (w miliardach) = (Akcje w milionach * Cena) / 1000
    market_cap_bn = (val_shares * data['market_price']) / 1000 if data['market_price'] else 0.0
    total_capital = market_cap_bn + data['total_debt']
    
    if total_capital > 0:
        auto_eq_weight = (market_cap_bn / total_capital) * 100
        auto_d_weight = (data['total_debt'] / total_capital) * 100
    else:
        # Fallback jeśli brak danych rynkowych
        auto_eq_weight = 90.0
        auto_d_weight = 10.0

    st.markdown("**Struktura kapitału firmy (Zasugerowana na bazie Market Cap i całkowitego długu):**")
    cw1, cw2 = st.columns(2)
    with cw1:
        weight_equity = st.number_input("Waga Kapitału Własnego (Equity) [%]", value=float(auto_eq_weight)) / 100
    with cw2:
        weight_debt = st.number_input("Waga Długu (Debt) [%]", value=float(auto_d_weight)) / 100

    if abs((weight_equity + weight_debt) - 1.0) > 0.001:
        st.error("🚨 Suma wag kapitału i długu musi wynosić równo 100%!")

    re = val_rf + (val_beta * val_erp)
    sug_wacc = (re * weight_equity) + (val_cost_debt * weight_debt)
    
    st.info(f"**Jak to policzyliśmy?**\n"
            f"1. Koszt Kapitału Własnego (Re) wg modelu CAPM wynosi: **{(re*100):.2f}%**\n"
            f"2. Uśredniamy to z kosztem i wagą długu, co daje ostateczny WACC do modelu: **{(sug_wacc*100):.2f}%**")
    
    use_custom_wacc = st.checkbox("Chcę ręcznie nadpisać ostateczny WACC (zignoruj powyższy wzór)")
    if use_custom_wacc:
        wacc_final = st.slider("Ustaw własny WACC do modelu [%]", 1.0, 25.0, float(sug_wacc*100)) / 100
    else:
        wacc_final = sug_wacc

    st.divider()

    st.subheader("📈 KROK 3: Dynamika wzrostu i Wartość Terminalna")
    
    col_g, col_tv = st.columns(2)
    with col_g:
        default_growth = float(data['growth_est'] * 100) if data['growth_est'] else 0.0
        g_high = st.number_input("Wzrost FCF (Lata 1-5) [%]", value=default_growth) / 100
        
        if input_mode == "Pobierz automatycznie z Yahoo Finance" and data['growth_est'] != 0.0:
            st.caption(f"💡 Sugerowany krótko-średnioterminowy wzrost wg Yahoo: **{data['growth_est']*100:.1f}%**")
        
    with col_tv:
        tv_method = st.radio("Metoda Wartości Terminalnej (TV)", ["Wzrost wieczysty (Gordon Growth)", "Mnożnik wyjścia (Exit Multiple)"])
        
        if tv_method == "Wzrost wieczysty (Gordon Growth)":
            g_term = st.number_input("Wzrost terminalny [%]", value=2.5) / 100
        else:
            exit_mult = st.number_input("Mnożnik wyjścia (EV/FCF)", value=15.0)

    sims = st.select_slider("Liczba symulacji Monte Carlo", options=[1000, 5000, 10000], value=5000)
    
    st.divider()

    if st.button("🚀 Uruchom Kalkulację DCF"):
        if val_shares <= 0:
            st.error("Liczba akcji musi być większa od zera, aby obliczyć cenę za akcję!")
        elif abs((weight_equity + weight_debt) - 1.0) > 0.001:
            st.error("Popraw wagi struktury kapitału (Krok 2) - muszą sumować się do 100%.")
        else:
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
                            target_g = g_term if tv_method == "Wzrost wieczysty (Gordon Growth)" else 0.02
                            fade_factor = (year - 5) / 5
                            growth = s_g * (1 - fade_factor) + target_g * fade_factor
                        
                        current_fcf *= (1 + growth)
                        pv_projection += current_fcf / ((1 + s_wacc)**year)
                    
                    if tv_method == "Wzrost wieczysty (Gordon Growth)":
                        tv = (current_fcf * (1 + g_term)) / (max(s_wacc - g_term, 0.005))
                    else:
                        s_mult = np.random.normal(exit_mult, 1.0)
                        tv = current_fcf * s_mult
                        
                    pv_tv = tv / ((1 + s_wacc)**10)
                    
                    enterprise_value = pv_projection + pv_tv
                    equity_value = enterprise_value - val_debt
                    share_price = max(equity_value * 1000 / val_shares, 0)
                    results.append(share_price)

                mean_res = np.mean(results)
                p5 = np.percentile(results, 5)
                p95 = np.percentile(results, 95)
                
                st.success("Obliczenia zakończone!")
                res1, res2, res3 = st.columns(3)
                res1.metric("Pesymistycznie (5%)", f"${p5:.2f}")
                
                if data['market_price'] and data['market_price'] > 0:
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
                
                if data['market_price'] and data['market_price'] > 0:
                    ax.axvline(data['market_price'], color='black', linewidth=3, label=f'Market Price: ${data["market_price"]:.2f}')
                
                ax.set_title(f"Rozkład Prawdopodobieństwa Ceny Akcji: {data['name']}")
                ax.legend()
                st.pyplot(fig)