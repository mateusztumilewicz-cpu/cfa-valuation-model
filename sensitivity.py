import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="WIBOR Sensitivity", layout="wide")
st.title(" Macro Stress-Test: WIBOR Transmission Mechanism")

# --- METHODOLOGY NOTE ---
st.markdown(r"""
###  Methodology Note
To isolate the impact of interest rate shocks (**WIBOR**) on the company's valuation, 
this model applies the **ceteris paribus** principle. 

We assume the operational growth parameters (**FCF Growth**) remain constant in the base scenario 
to demonstrate the direct "transmission mechanism":
$$ \text{Higher WIBOR} \rightarrow \text{Higher Cost of Debt} \rightarrow \text{Higher WACC} \rightarrow \text{Lower Valuation} $$
""")

# --- SIDEBAR: INPUTS ---
with st.sidebar:
    st.header("1. Financial Data (Base)")
    fcf_year_0 = st.number_input("FCF (Year 0) [PLN m]", value=100.0)
    net_debt = st.number_input("Net Debt [PLN m]", value=400.0)
    shares = st.number_input("Shares Outstanding [m]", value=14.0)
    
    st.markdown("---")
    st.header("2. Debt Parameters")
    current_wibor = st.number_input("Current WIBOR 6M [%]", value=5.85) / 100
    bank_margin = st.number_input("Bank Margin [%]", value=2.00) / 100
    tax_rate = st.number_input("Tax Rate (CIT) [%]", value=19.0) / 100
    
    st.markdown("---")
    st.header("3. Capital Structure")
    weight_debt = st.slider("Debt Weight (D/V) [%]", 0, 100, 30) / 100
    cost_equity = st.number_input("Cost of Equity (Ke) [%]", value=12.5) / 100
    
    st.markdown("---")
    st.header("4. Growth Assumptions")
    g_growth = st.number_input("Forecast Growth (CAGR 1-5y) [%]", value=10.0) / 100
    g_term_base = st.number_input("Terminal Growth (g) [%]", value=2.5) / 100

# --- CALCULATION ENGINE ---
def calculate_metrics(wibor_val):
    # 1. Cost of Debt (Kd)
    kd = wibor_val + bank_margin
    
    # 2. After-tax Cost of Debt
    kd_after_tax = kd * (1 - tax_rate)
    
    # 3. WACC
    wacc = (cost_equity * (1 - weight_debt)) + (kd_after_tax * weight_debt)
    
    # 4. Valuation (Simplified DCF for Sensitivity)
    pv_projection = 0
    current_fcf = fcf_year_0
    for year in range(1, 6):
        current_fcf = current_fcf * (1 + g_growth)
        pv_projection += current_fcf / ((1 + wacc) ** year)
    
    # Terminal Value
    denominator = max(wacc - g_term_base, 0.005)
    tv = (current_fcf * (1 + g_term_base)) / denominator
    pv_tv = tv / ((1 + wacc) ** 5)
    
    equity = (pv_projection + pv_tv) - net_debt
    price = max(equity / shares, 0)
    
    return kd, wacc, price

# --- MAIN DASHBOARD ---
st.markdown("---")

#  PRZYCISK URUCHAMIAJĄCY 
if st.button(" Run Sensitivity Analysis", type="primary"):
    
    st.header("1. Transmission Table: Interest Rate Shock Analysis")
    st.write("How does a change in WIBOR affect the Discount Rate (WACC) and Share Price?")

    # Generating the Table
    scenarios = [-0.02, -0.01, 0.00, 0.01, 0.02] # -200bps to +200bps
    table_data = []

    for shock in scenarios:
        simulated_wibor = current_wibor + shock
        kd, wacc, price = calculate_metrics(simulated_wibor)
        
        table_data.append({
            "WIBOR Change": f"{shock:+.0%}",
            "Simulated WIBOR": f"{simulated_wibor:.2%}",
            "➡ Cost of Debt (Kd)": f"{kd:.2%}",
            "➡ Resulting WACC": f"{wacc:.2%}",
            " Implied Share Price": f"{price:.2f} PLN"
        })

    df_table = pd.DataFrame(table_data)

    # Wyświetlanie tabeli
    st.dataframe(df_table, hide_index=True)

    st.info(" **Observation:** A 1% increase in WIBOR directly increases the Cost of Debt, pushing WACC higher and reducing the company's Intrinsic Value.")

    st.markdown("---")

    st.header("2. Sensitivity Heatmap (WIBOR vs. Growth)")
    st.write("Scenario Analysis: What if rates rise, but the company manages to grow faster?")

    # Generating Matrix
    wibor_range = np.linspace(current_wibor - 0.02, current_wibor + 0.02, 7)
    g_range = np.linspace(g_term_base - 0.01, g_term_base + 0.01, 5)

    sensitivity_matrix = np.zeros((len(g_range), len(wibor_range)))

    for i, g in enumerate(g_range):
        for j, w in enumerate(wibor_range):
            # Local calculation loop
            kd_temp = w + bank_margin
            wacc_temp = (cost_equity * (1 - weight_debt)) + (kd_temp * (1 - tax_rate) * weight_debt)
            
            pv_proj = 0
            curr_fcf = fcf_year_0
            for y in range(1, 6):
                curr_fcf = curr_fcf * (1 + g_growth) 
                pv_proj += curr_fcf / ((1 + wacc_temp) ** y)
                
            denom = max(wacc_temp - g, 0.005) 
            tv_temp = (curr_fcf * (1 + g)) / denom
            pv_tv_temp = tv_temp / ((1 + wacc_temp) ** 5)
            
            sensitivity_matrix[i, j] = max((pv_proj + pv_tv_temp - net_debt) / shares, 0)

    df_sens = pd.DataFrame(sensitivity_matrix, 
                           index=[f"g={x:.1%}" for x in g_range],
                           columns=[f"WIBOR={x:.1%}" for x in wibor_range])

    # Plotting
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(df_sens, annot=True, fmt=".1f", cmap="RdYlGn", cbar_kws={'label': 'Share Price (PLN)'}, ax=ax)
    ax.set_title("Valuation Sensitivity: WIBOR vs. Terminal Growth")
    ax.set_xlabel("WIBOR 6M Level")
    ax.set_ylabel("Terminal Growth Rate (g)")

    st.pyplot(fig)

else:
    # Komunikat zachęcający do kliknięcia
    st.info(" Adjust parameters in the sidebar and click **'Run Sensitivity Analysis'** to see the results.")