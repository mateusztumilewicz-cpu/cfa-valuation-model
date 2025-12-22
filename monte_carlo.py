import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title=" Valuation Model", layout="wide")
st.title("Monte Carlo Valuation Engine")
st.markdown("""
**Objective:** Probabilistic valuation simulation based on a 2-Stage DCF Model.
This engine assesses the impact of assumption volatility (WACC, Growth) on the intrinsic share value.
""")
#zmniana test 2 
# --- SECTION 1: SIDEBAR INPUTS & CHEAT SHEET ---
with st.sidebar:
    st.header("1. Key Assumptions (Base Case)")
    
    # --- ANALYST CHEAT SHEET ---
    with st.expander(" Analyst Cheat Sheet: Formula Guide"):
        st.markdown(r"""
        **1. Free Cash Flow (FCF Year 0):**
        $$FCF = EBIT(1-t) + D\&A - CAPEX - \Delta NWC$$
        *Derived from the latest Annual Report.*
        
        **2. Net Debt:**
        $$Net Debt = Total Debt - Cash \& Equivalents$$
        *Includes interest-bearing loans, bonds, and leases.*
        
        **3. WACC (Discount Rate):**
        $$WACC = \frac{E}{V} \times K_e + \frac{D}{V} \times K_d(1-t)$$
        *Based on Risk-Free Rate, Beta, and Equity Risk Premium.*
        """)
    # --------------------------------
    
    fcf_year_0 = st.number_input("FCF (Year 0) [PLN m]", value=100.0, help="Free Cash Flow to Firm (Latest Actuals)")
    net_debt = st.number_input("Net Debt [PLN m]", value=400.0, help="Interest-bearing debt minus cash")
    shares = st.number_input("Shares Outstanding [m]", value=14.0)
    
    st.markdown("---")
    st.header("2. Forecast Phase (Years 1-5)")
    st.info("FCF Dynamics for the explicit forecast period.")
    
    g_growth_mean = st.slider("Avg. FCF Growth (CAGR) [%]", 0.0, 25.0, 12.0) / 100
    g_growth_std = st.slider("Forecast Uncertainty (+/- %)", 0.0, 10.0, 3.0) / 100
    
    st.markdown("---")
    st.header("3. Terminal Phase (Year 5+)")
    
    col_wacc, col_g = st.columns(2)
    with col_wacc:
        st.write("**WACC (Risk)**")
        wacc_mean = st.number_input("Target WACC [%]", value=9.5, step=0.1) / 100
        wacc_std = st.number_input("Volatility (+/- %)", value=1.0, step=0.1) / 100
    
    with col_g:
        st.write("**Terminal Growth**")
        g_term_mean = st.number_input("Terminal g [%]", value=2.5, step=0.1) / 100
        g_term_std = st.number_input("Volatility g (+/-)", value=0.5, step=0.1) / 100

    st.markdown("---")
    simulations = st.select_slider("Simulation Count (Iterations)", options=[1000, 5000, 10000, 20000], value=10000)

# --- SECTION 2: CALCULATION ENGINE ---
def run_simulation():
    # 1. Vectorized Randomization (Generating 10k scenarios)
    wacc_sim = np.random.normal(wacc_mean, wacc_std, simulations)
    g_term_sim = np.random.normal(g_term_mean, g_term_std, simulations)
    g_growth_sim = np.random.normal(g_growth_mean, g_growth_std, simulations)
    
    # 2. 5-Year Projection (Explicit Period)
    pv_projection = np.zeros(simulations)
    current_fcf = np.full(simulations, fcf_year_0)
    
    for year in range(1, 6):
        current_fcf = current_fcf * (1 + g_growth_sim)
        discount_factor = (1 + wacc_sim) ** year
        pv_projection += current_fcf / discount_factor
        
    fcf_year_5 = current_fcf
    
    # 3. Terminal Value (Gordon Growth Model)
    # Sanity check: WACC must be > g (min spread 0.5%)
    denominator = np.maximum(wacc_sim - g_term_sim, 0.005)
    
    tv = (fcf_year_5 * (1 + g_term_sim)) / denominator
    pv_tv = tv / ((1 + wacc_sim) ** 5)
    
    # 4. Enterprise to Equity Bridge
    enterprise_value = pv_projection + pv_tv
    equity_value = enterprise_value - net_debt
    share_price = np.maximum(equity_value / shares, 0)
    
    return share_price

# --- SECTION 3: RESULTS DASHBOARD ---
if st.button(" Run Monte Carlo Simulation"):
    
    with st.spinner('Simulating 10,000 market scenarios...'):
        results = run_simulation()
        
        # Statistics (95% Confidence Interval)
        mean_val = np.mean(results)
        low_val = np.percentile(results, 2.5)   # Bear Case
        high_val = np.percentile(results, 97.5) # Bull Case
        prob_upside = np.mean(results > mean_val) * 100 

        # 1. KPI Metrics
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Bear Case (2.5%)", f"{low_val:.2f} PLN", delta="-Risk")
        kpi2.metric("Mean Target Price", f"{mean_val:.2f} PLN")
        kpi3.metric("Bull Case (97.5%)", f"{high_val:.2f} PLN", delta="+Upside")
        
        # 2. Main Distribution Chart
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.histplot(results, bins=70, kde=True, color="#2ecc71", edgecolor="white", alpha=0.7, ax=ax)
        
        # Reference Lines
        ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'Base Case: {mean_val:.2f}')
        ax.axvline(low_val, color='black', linestyle=':', label='95% Confidence Interval')
        ax.axvline(high_val, color='black', linestyle=':')
        
        # Chart Aesthetics
        ax.set_title(f"Implied Share Price Distribution (n={simulations})", fontsize=14)
        ax.set_xlabel("Implied Share Price (PLN)")
        ax.set_ylabel("Frequency / Scenario Count")
        ax.legend()
        ax.grid(axis='y', alpha=0.2)
        
        st.pyplot(fig)
        
        # 3. Automatic Interpretation
        st.success(f"""
        **Model Interpretation:**
        Based on the current volatility assumptions, the fundamental value implies a 
        **95% probability range between {low_val:.2f} PLN and {high_val:.2f} PLN**.
        The mean target price is **{mean_val:.2f} PLN**.
        """)