import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# 1. KONFIGURACJA STRONY
st.set_page_config(page_title="Tarcza Podatkowa 2025", layout="wide")

def run_tax_app_final_v5():
    st.title("🛡️ Tarcza Podatkowa: IKE vs OKI vs Zwykłe Konto")
    st.markdown("""
    Sprawdź, jak **kapitał początkowy** i regularne wpłaty wpływają na Twoją wycenę netto. 
    Zauważ, że im więcej masz na start, tym szybciej OKI przegrywa z IKE przez podatek od aktywów.
    """)

    # --- SIDEBAR: WEJŚCIE DANYCH ---
    with st.sidebar:
        st.header("⚙️ Parametry inwestycji")
        # NOWE POLE: Kapitał początkowy
        initial_capital = st.number_input("Kapitał początkowy (już na koncie) [PLN]", value=50000, step=5000)
        annual_contribution = st.number_input("Roczna wpłata [PLN]", value=25000, step=1000)
        annual_growth = st.slider("Średni roczny wzrost [%]", 0.0, 20.0, 8.0) / 100
        years = st.slider("Okres inwestycji [lata]", 5, 40, 20)
        
        st.markdown("---")
        ike_type = st.radio("Scenariusz IKE:", 
                            ["Wypłata PRZED 60-tką (19% od zysku)", 
                             "Wypłata PO 60-tce (0% podatku)"])
        
        st.markdown("---")
        st.subheader("Ustawienia OKI")
        oki_tax = st.number_input("Podatek OKI pow. 100k [%/rok]", value=0.9, step=0.1) / 100

        # PRZYCISK OBLICZ
        calculate_btn = st.button("🔥 Oblicz symulację", use_container_width=True)

    # --- LOGIKA SYMULACJI (Wyzwalana przyciskiem) ---
    if calculate_btn:
        # Inicjalizacja z uwzględnieniem kapitału początkowego
        val_reg = float(initial_capital)
        val_ike = float(initial_capital)
        val_oki = float(initial_capital)
        total_invested = float(initial_capital)
        data = []

        # Rok 0 (Stan startowy przed doliczeniem pierwszej wpłaty i wzrostu)
        data.append({
            "Rok": 0, 
            "Suma Wpłat": total_invested, 
            "Zwykłe": val_reg, 
            "IKE (Brutto)": val_ike, 
            "OKI": val_oki
        })

        for year in range(1, years + 1):
            # Dodajemy roczną wpłatę na początku roku
            val_reg += annual_contribution
            val_ike += annual_contribution
            val_oki += annual_contribution
            total_invested += annual_contribution
            
            # 1. Zwykłe konto (podatek Belki co roku od wypracowanego zysku)
            val_reg = val_reg * (1 + annual_growth * 0.81)
            
            # 2. IKE (Brutto - rośnie bez podatku w trakcie)
            val_ike = val_ike * (1 + annual_growth)
            
            # 3. OKI (Podatek 0% do 100k, powyżej X% od aktywów rocznie)
            val_oki = val_oki * (1 + annual_growth)
            if val_oki > 100000:
                tax_amount = (val_oki - 100000) * oki_tax
                val_oki -= tax_amount
                
            data.append({
                "Rok": year, 
                "Suma Wpłat": total_invested, 
                "Zwykłe": val_reg,
                "IKE (Brutto)": val_ike, 
                "OKI": val_oki
            })

        st.session_state['results_df'] = pd.DataFrame(data)
        st.session_state['params'] = {
            "total_invested": total_invested, 
            "ike_type": ike_type, 
            "years": years
        }

    # --- WIZUALIZACJA ---
    if 'results_df' in st.session_state:
        df = st.session_state['results_df']
        p = st.session_state['params']
        
        # Wyliczenia końcowe dla IKE Netto
        final_gross_ike = float(df.iloc[-1]["IKE (Brutto)"])
        gain = final_gross_ike - p["total_invested"]
        final_net_ike = final_gross_ike - (gain * 0.19) if "PRZED" in p["ike_type"] and gain > 0 else final_gross_ike
        final_oki = float(df.iloc[-1]["OKI"])

        # WYKRES
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # 1. Zwykłe konto
        ax.plot(df["Rok"], df["Zwykłe"], label="Zwykłe Konto", color="grey", linestyle=":", alpha=0.5)
        
        # 2. IKE - Gruba zielona linia
        ax.plot(df["Rok"], df["IKE (Brutto)"], label="IKE (Wartość Brutto)", 
                color="#2ecc71", linewidth=6, alpha=0.7, zorder=2)
        
        # 3. OKI - Cieńsza przerywana niebieska linia
        ax.plot(df["Rok"], df["OKI"], label="OKI (Podatek pow. 100k)", 
                color="#3498db", linewidth=2.5, linestyle="--", zorder=3)
        
        # Klif podatkowy na końcu dla IKE
        if "PRZED" in p["ike_type"]:
            ax.vlines(x=p["years"], ymin=final_net_ike, ymax=final_gross_ike, 
                      colors='red', linestyles='-', linewidth=2, label="Podatek Belki")
            ax.scatter(p["years"], final_net_ike, color='red', s=120, zorder=5, label="Wypłata Netto IKE")

        ax.set_title(f"IKE vs OKI - Wpływ Kapitału Początkowego", fontsize=16)
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f} zł'))
        ax.set_xlabel("Lata inwestowania")
        ax.legend(loc="upper left", frameon=True, shadow=True)
        ax.grid(True, alpha=0.2)
        st.pyplot(fig)

        # TABELA I METRYKI
        st.subheader("📋 Wyniki symulacji")
        c1, c2, c3 = st.columns(3)
        c1.metric("Suma Twoich wpłat", f"{p['total_invested']:,.0f} zł")
        c2.metric("Finalnie IKE (Netto)", f"{final_net_ike:,.0f} zł")
        c3.metric("Finalnie OKI", f"{final_oki:,.0f} zł")

        # Dynamiczny wniosek
        diff = final_net_ike - final_oki
        if diff > 0:
            st.success(f"Wygrywa IKE! Mimo podatku na końcu, Twój kapitał rósł szybciej o **{diff:,.0f} zł** niż w OKI.")
        else:
            st.info(f"W tym scenariuszu OKI wygrywa o **{abs(diff):,.0f} zł**.")

        # Tabela co 5 lat
        indices = [i for i in range(0, p["years"] + 1, 5)]
        if p["years"] not in indices: indices.append(p["years"])
        st.table(df.iloc[indices].style.format("{:,.0f}"))

if __name__ == "__main__":
    run_tax_app_final_v5()