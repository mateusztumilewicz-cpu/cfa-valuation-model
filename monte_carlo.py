import streamlit as st
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import datetime

st.set_page_config(page_title="Kompleksowy Model Wyceny: DCF & P/E", layout="wide")

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
        total_debt_raw = info.get('totalDebt', 0) if info.get('totalDebt') else 0.0
        total_cash = info.get('totalCash', 0) if info.get('totalCash') else 0.0
        total_debt = total_debt_raw / 1e9
        net_debt = (total_debt_raw - total_cash) / 1e9
        shares = info.get('sharesOutstanding', 0) / 1e6 if info.get('sharesOutstanding') else 0.0
        growth_est = info.get('earningsGrowth', 0.0) if info.get('earningsGrowth') is not None else 0.0
        beta = info.get('beta', 0.0) if info.get('beta') else 0.0
        market_price = info.get('currentPrice', 0.0)
        
        trailing_eps = info.get('trailingEps', 0.0) if info.get('trailingEps') else 0.0
        trailing_pe = info.get('trailingPE', 0.0) if info.get('trailingPE') else 0.0
        sector = info.get('sector', '')
        
        return {
            "name": info.get('longName', ticker_str),
            "fcf": fcf,
            "total_debt": total_debt,
            "net_debt": net_debt,
            "shares": shares,
            "beta": beta,
            "market_price": market_price,
            "growth_est": growth_est,
            "trailing_eps": trailing_eps,
            "trailing_pe": trailing_pe,
            "sector": sector
        }
    except Exception as e:
        st.error(f"Błąd API Yahoo Finance: {e}. Przełącz na tryb ręczny.")
        return None

# --- GŁÓWNY NAGŁÓWEK ---
st.title("💎 Smart Valuation Tool: DCF & Wycena Wskaźnikowa")

input_mode = st.radio(
    "Wybierz źródło danych:",
    ("Pobierz automatycznie z Yahoo Finance", "Wpisz wszystkie dane ręcznie (Tryb Offline)"),
    horizontal=True
)

data = None

if input_mode == "Pobierz automatycznie z Yahoo Finance":
    ticker_input = st.text_input("Wpisz Ticker spółki (np. GOOGL, AAPL, UBER, PZU.WA):", value="").upper()
    if ticker_input:
        with st.spinner('Pobieram dane z rynku...'):
            data = get_company_data(ticker_input)
            
        if data:
            if "Financial" in data['sector']:
                st.warning("⚠️ **UWAGA:** Ta spółka należy do sektora finansowego (Bank/Ubezpieczenia). Klasyczny model DCF oparty na FCF nie działa dobrze dla instytucji finansowych. Skup się na drugiej zakładce: 'Wycena Wskaźnikowa (P/E & EPS)'!")
            if ticker_input in multi_class_tickers:
                st.warning(f"⚠️ **OSTRZEŻENIE:** {ticker_input} ma strukturę wieloklasową. Sprawdź i popraw łączną liczbę akcji w pierwszej zakładce!")
else:
    data = {
        "name": "Moja_Spolka", "fcf": 0.0, "total_debt": 0.0, "net_debt": 0.0, 
        "shares": 100.0, "beta": 1.0, "market_price": 50.0, "growth_est": 0.10,
        "trailing_eps": 2.50, "trailing_pe": 20.0, "sector": "Technology"
    }

if data:
    safe_name = str(data['name']).replace(" ", "_")

    st.header(f"Analiza: {data['name']}")
    st.write(f"**Obecna cena rynkowa:** ${data['market_price']:.2f}")
    
    tab1, tab2 = st.tabs(["📊 Wycena DCF (Monte Carlo)", "📈 Wycena Wskaźnikowa rok po roku (P/E & EPS)"])
    
    # ==========================================
    # ZAKŁADKA 1: MODEL DCF
    # ==========================================
    with tab1:
        st.subheader("Model Zdyskontowanych Przepływów Pieniężnych (DCF)")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            val_fcf = st.number_input("FCF (Year 0) [$ bn]", value=float(data['fcf']), key=f"fcf_{safe_name}")
        with c2:
            val_debt = st.number_input("Dług Netto [$ bn]", value=float(data['net_debt']), key=f"debt_{safe_name}")
        with c3:
            val_shares = st.number_input("Liczba akcji [m]", value=float(data['shares']), key=f"shares_{safe_name}")

        st.divider()
        st.markdown("#### Kalkulacja WACC i CAPM")
        
        w1, w2, w3, w4 = st.columns(4)
        with w1:
            val_rf = st.number_input("Stopa wolna od ryzyka (Rf) [%]", value=4.20, key=f"rf_{safe_name}") / 100
        with w2:
            val_erp = st.number_input("Premia rynkowa (ERP) [%]", value=5.50, key=f"erp_{safe_name}") / 100
        with w3:
            val_beta = st.number_input("Beta", value=float(data['beta']), key=f"beta_{safe_name}")
        with w4:
            val_cost_debt = st.number_input("Koszt długu (Rd) po opodatkowaniu [%]", value=4.50, key=f"rd_{safe_name}") / 100
            
        market_cap_bn = (val_shares * data['market_price']) / 1000 if data['market_price'] else 0.0
        total_capital = market_cap_bn + data['total_debt']
        auto_eq_weight = (market_cap_bn / total_capital) * 100 if total_capital > 0 else 90.0
        auto_d_weight = (data['total_debt'] / total_capital) * 100 if total_capital > 0 else 10.0

        cw1, cw2 = st.columns(2)
        with cw1:
            weight_equity = st.number_input("Waga Kapitału Własnego [%]", value=float(auto_eq_weight), key=f"weq_{safe_name}") / 100
        with cw2:
            weight_debt = st.number_input("Waga Długu [%]", value=float(auto_d_weight), key=f"wdebt_{safe_name}") / 100

        re = val_rf + (val_beta * val_erp)
        sug_wacc = (re * weight_equity) + (val_cost_debt * weight_debt)
        
        st.info(f"Sugerowany WACC do modelu: **{(sug_wacc*100):.2f}%**")
        
        use_custom_wacc = st.checkbox("Chcę ręcznie nadpisać ostateczny WACC", key=f"check_wacc_{safe_name}")
        wacc_final = st.slider("Własny WACC [%]", 1.0, 25.0, float(sug_wacc*100), key=f"slider_wacc_{safe_name}") / 100 if use_custom_wacc else sug_wacc

        st.divider()
        st.markdown("#### Założenia Wzrostu i Symulacja")
        
        col_g, col_tv = st.columns(2)
        with col_g:
            default_growth = float(data['growth_est'] * 100) if data['growth_est'] else 0.0
            g_high = st.number_input("Wzrost FCF (Lata 1-5) [%]", value=default_growth, key=f"ghigh_{safe_name}") / 100
        with col_tv:
            tv_method = st.radio("Metoda Wartości Terminalnej", ["Wzrost wieczysty (Gordon Growth)", "Mnożnik wyjścia (Exit Multiple)"], key=f"tv_method_{safe_name}")
            if tv_method == "Wzrost wieczysty (Gordon Growth)":
                g_term = st.number_input("Wzrost terminalny [%]", value=2.5, key=f"gterm_{safe_name}") / 100
            else:
                exit_mult = st.number_input("Mnożnik wyjścia (EV/FCF)", value=15.0, key=f"emult_{safe_name}")

        sims = st.select_slider("Liczba symulacji", options=[1000, 5000, 10000], value=5000, key=f"sims_{safe_name}")
        
        if st.button("🚀 Uruchom Kalkulację DCF", type="primary", key=f"btn_dcf_{safe_name}"):
            if val_shares <= 0 or abs((weight_equity + weight_debt) - 1.0) > 0.001:
                st.error("Błędne dane wejściowe (sprawdź akcje lub wagi kapitału).")
            else:
                with st.spinner('Trwają obliczenia Monte Carlo...'):
                    results = []
                    for _ in range(sims):
                        s_wacc = np.random.normal(wacc_final, 0.007)
                        s_g = np.random.normal(g_high, 0.02)
                        pv_projection, current_fcf = 0, val_fcf
                        
                        for year in range(1, 11):
                            growth = s_g if year <= 5 else s_g * (1 - (year - 5) / 5) + (g_term if tv_method == "Wzrost wieczysty (Gordon Growth)" else 0.02) * ((year - 5) / 5)
                            current_fcf *= (1 + growth)
                            pv_projection += current_fcf / ((1 + s_wacc)**year)
                        
                        if tv_method == "Wzrost wieczysty (Gordon Growth)":
                            tv = (current_fcf * (1 + g_term)) / (max(s_wacc - g_term, 0.005))
                        else:
                            tv = current_fcf * np.random.normal(exit_mult, 1.0)
                            
                        pv_tv = tv / ((1 + s_wacc)**10)
                        share_price = max((pv_projection + pv_tv - val_debt) * 1000 / val_shares, 0)
                        results.append(share_price)

                    mean_res, p5, p95 = np.mean(results), np.percentile(results, 5), np.percentile(results, 95)
                    st.success("Obliczenia DCF zakończone!")
                    
                    r1, r2, r3 = st.columns(3)
                    r1.metric("📉 Pesymistycznie (5. percentyl)", f"${p5:.2f}")
                    r2.metric("⚖️ Fair Value (Średnia)", f"${mean_res:.2f}", delta=f"{(mean_res/data['market_price']-1)*100:.1f}% vs Rynek" if data['market_price'] else None)
                    r3.metric("📈 Optymistycznie (95. percentyl)", f"${p95:.2f}")

                    fig, ax = plt.subplots(figsize=(10, 4))
                    sns.histplot(results, kde=True, color="skyblue", bins=80, ax=ax)
                    ax.axvline(mean_res, color='red', linewidth=2, label=f'Fair Value: ${mean_res:.2f}')
                    ax.axvline(p5, color='orange', linestyle='--', label=f'5% Percentile: ${p5:.2f}')
                    ax.axvline(p95, color='green', linestyle='--', label=f'95% Percentile: ${p95:.2f}')
                    if data['market_price']: ax.axvline(data['market_price'], color='black', linewidth=3, label=f'Market Price: ${data["market_price"]:.2f}')
                    ax.legend()
                    st.pyplot(fig)

    # ==========================================
    # ZAKŁADKA 2: WYCENA WSKAŹNIKOWA (ROK PO ROKU)
    # ==========================================
    with tab2:
        st.subheader("Model Relatywny: Ścieżka Zysków i P/E rok po roku")
        
        st.markdown("#### 1. Punkt Startowy (Obecne dane)")
        chk1, chk2, chk3 = st.columns(3)
        with chk1:
            current_eps = st.number_input("Obecny EPS (Zysk na akcję) [$]", value=float(data['trailing_eps']), step=0.1, key=f"ceps_{safe_name}")
        with chk2:
            current_pe = st.number_input("Obecne P/E (Cena/Zysk)", value=float(data['trailing_pe']), step=1.0, key=f"cpe_{safe_name}")
        with chk3:
            implied_price = current_eps * current_pe
            st.info(f"**Obecna Cena z równania:**\n ${current_eps:.2f} × {current_pe:.2f} = **${implied_price:.2f}**")

        st.divider()
        
        st.markdown("#### 2. Twoja Projekcja (Kolejne 5 lat)")
        p1, p2, p3 = st.columns(3)
        with p1:
            proj_growth = st.number_input("Prognozowany roczny wzrost Zysku Netto [%]", value=float(data['growth_est']*100), step=1.0, key=f"pgrowth_{safe_name}") / 100
        with p2:
            proj_buyback = st.number_input("Roczny skup akcji (Buyback Yield) [%]", value=0.0, step=0.5, key=f"pbb_{safe_name}") / 100
        with p3:
            target_pe = st.number_input("Docelowe Bazowe P/E (dla tabeli)", value=float(current_pe) if current_pe > 0 else 15.0, step=1.0, key=f"tpe_{safe_name}")

        st.divider()

        st.markdown("#### 3. Tabela Projekcji Cenowej (Rok po roku)")
        st.write("W nawiasach obok przewidywanej ceny w danym roku znajduje się obliczony roczny zwrot (CAGR) w stosunku do obecnej ceny rynkowej.")
        
        # Proporcjonalne widełki: -20% i +20% od docelowego wskaźnika P/E
        pe_bear = max(target_pe * 0.8, 1.0)
        pe_bull = target_pe * 1.2
        
        year_data = []
        for year in range(1, 6):
            # Skumulowany wzrost EPS
            eps_future = current_eps * ((1 + proj_growth)**year) / ((1 - proj_buyback)**year)
            
            # Ceny w 3 scenariuszach
            price_bear = eps_future * pe_bear
            price_base = eps_future * target_pe
            price_bull = eps_future * pe_bull
            
            # Obliczanie CAGR (Zabezpieczenie na wypadek braku ceny rynkowej)
            if data['market_price'] > 0:
                cagr_bear = ((price_bear / data['market_price'])**(1/year) - 1) * 100
                cagr_base = ((price_base / data['market_price'])**(1/year) - 1) * 100
                cagr_bull = ((price_bull / data['market_price'])**(1/year) - 1) * 100
                
                # Formatowanie wartości z dopiskiem CAGR
                str_bear = f"${price_bear:.2f} ({cagr_bear:+.1f}%)"
                str_base = f"${price_base:.2f} ({cagr_base:+.1f}%)"
                str_bull = f"${price_bull:.2f} ({cagr_bull:+.1f}%)"
            else:
                str_bear = f"${price_bear:.2f}"
                str_base = f"${price_base:.2f}"
                str_bull = f"${price_bull:.2f}"

            year_data.append({
                "Okres": f"Rok {year}",
                "Prognozowany EPS": f"${eps_future:.2f}",
                f"Pesymistycznie (P/E ~{pe_bear:.1f})": str_bear,
                f"Bazowo (P/E ~{target_pe:.1f})": str_base,
                f"Optymistycznie (P/E ~{pe_bull:.1f})": str_bull
            })

        df_years = pd.DataFrame(year_data)
        st.dataframe(df_years, use_container_width=True, hide_index=True)