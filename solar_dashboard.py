# python -m streamlit run solar_dashboard.py
import streamlit as st
import numpy_financial as npf
import pandas as pd
import io

# --- Page config ---
st.set_page_config(page_title="Solar Plant Financial Calculator", layout="centered")

# --- Title ---
st.title("🌞 Solar Power Plant - Financial Calculator")

# --- Sidebar Inputs ---
st.sidebar.header("Technical Parameters")

plant_capacity_manual_mw = st.sidebar.number_input("Plant Capacity (MW)", value=1.0, step=0.1)

panel_type = st.sidebar.selectbox(
    "Solar Panel Type",
    ["Monocrystalline", "Polycrystalline", "Thin Film"],
    index=0
)

solar_irradiation = st.sidebar.number_input("Solar Irradiation (kWh/m²/year)", value=1800.0, step=10.0)

# Panel efficiencies
efficiency_map = {
    "Monocrystalline": 0.20,
    "Polycrystalline": 0.17,
    "Thin Film": 0.12,
}

performance_ratio = 0.75
panel_efficiency = efficiency_map[panel_type]

estimated_cuf = (solar_irradiation * performance_ratio) / 8760
st.sidebar.markdown(f"Estimated CUF: {estimated_cuf * 100:.2f}%")

use_manual_cuf = st.sidebar.checkbox("Override CUF manually", value=False)
if use_manual_cuf:
    cuf = st.sidebar.number_input("CUF (%)", value=estimated_cuf * 100, step=0.1) / 100
else:
    cuf = estimated_cuf

use_manual_capacity = st.sidebar.checkbox("Use manual plant capacity (MW)", value=True)
plant_capacity_mw = plant_capacity_manual_mw if use_manual_capacity else plant_capacity_manual_mw

# --- State-wise Land Requirement ---
st.sidebar.header("Land Requirement by State (India)")

states = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Delhi", "Jammu & Kashmir", "Ladakh", "Chandigarh",
    "Andaman & Nicobar", "Dadra & Nagar Haveli", "Daman & Diu", "Lakshadweep",
    "Puducherry"
]

# Approximate land requirement (acres/MW)
land_per_mw_state_map = {
    "Rajasthan": 5.0,
    "Gujarat": 4.5,
    "Madhya Pradesh": 4.5,
    "Andhra Pradesh": 4.5,
    "Karnataka": 4.5,
    "Tamil Nadu": 4.5,
    "Maharashtra": 4.5,
    "Uttar Pradesh": 4.5,
}

default_land_per_mw = 4.5

selected_state = st.sidebar.selectbox("Select State/UT", states)

state_land_per_mw = land_per_mw_state_map.get(selected_state, default_land_per_mw)

use_manual_land = st.sidebar.checkbox("Override Land per MW (acres)", value=False)
if use_manual_land:
    land_per_mw = st.sidebar.number_input("Land Required per MW (acres)", value=state_land_per_mw, step=0.1)
else:
    land_per_mw = state_land_per_mw

total_land_required_acres = plant_capacity_mw * land_per_mw
total_land_required_hectares = total_land_required_acres * 0.4047

# --- Project Life & Degradation ---
degradation = st.sidebar.number_input("Annual Degradation (%)", value=0.5, step=0.1) / 100
project_life = st.sidebar.slider("Project Life (years)", 10, 35, 25)

# --- Financial Inputs ---
st.sidebar.header("Financial Inputs")

capital_cost_map = {
    "Monocrystalline": 60000000,
    "Polycrystalline": 50000000,
    "Thin Film": 45000000,
}
capital_cost_per_mw_auto = capital_cost_map[panel_type]

use_manual_capital_cost = st.sidebar.checkbox("Override Capital Cost per MW manually", value=False)
if use_manual_capital_cost:
    capital_cost_per_mw = st.sidebar.number_input("Capital Cost per MW (₹)", value=capital_cost_per_mw_auto, step=100000)
else:
    capital_cost_per_mw = capital_cost_per_mw_auto

om_cost_per_mw = st.sidebar.number_input("O&M Cost per MW (Year 1) (₹)", value=300000, step=10000)
om_escalation = st.sidebar.number_input("O&M Escalation Rate (%)", value=5.0, step=0.5) / 100
tariff = st.sidebar.number_input("Tariff (₹/kWh)", value=3.50, step=0.1)
discount_rate = st.sidebar.number_input("Discount Rate (%)", value=8.0, step=0.1) / 100

# --- Loan Inputs ---
st.sidebar.header("Loan Inputs")
loan_percent = st.sidebar.slider("Loan Portion (%)", 0, 100, 70)
loan_interest_rate = st.sidebar.number_input("Loan Interest Rate (%)", value=10.0, step=0.5) / 100
loan_tenure = st.sidebar.number_input("Loan Tenure (Years)", value=10, step=1)
depreciation_rate = st.sidebar.number_input("Depreciation Rate (%)", value=5.28, step=0.1) / 100
tax_rate = st.sidebar.number_input("Income Tax Rate (%)", value=25.0, step=1.0) / 100

# --- Calculations ---
capital_cost = capital_cost_per_mw * plant_capacity_mw
om_cost_year1 = om_cost_per_mw * plant_capacity_mw
energy_y1_kwh = plant_capacity_mw * 1000 * 8760 * cuf

loan_amount = capital_cost * loan_percent / 100
equity_amount = capital_cost - loan_amount
emi = npf.pmt(loan_interest_rate, loan_tenure, -loan_amount) if loan_tenure > 0 else 0

project_cash_flows = [-capital_cost]
equity_cash_flows = [-equity_amount]
energy_outputs = []
om_costs = []
remaining_loan = loan_amount

for year in range(1, project_life + 1):
    energy = energy_y1_kwh * ((1 - degradation) ** (year - 1))
    energy_outputs.append(energy)

    om_cost_year = om_cost_year1 * ((1 + om_escalation) ** (year - 1))
    om_costs.append(om_cost_year)

    revenue = energy * tariff
    depreciation = capital_cost * depreciation_rate

    interest_payment = remaining_loan * loan_interest_rate if year <= loan_tenure else 0
    principal_payment = emi - interest_payment if year <= loan_tenure else 0
    if year <= loan_tenure:
        remaining_loan -= principal_payment

    ebitda = revenue - om_cost_year
    taxable_income_proj = revenue - om_cost_year - depreciation
    income_tax_proj = max(taxable_income_proj, 0) * tax_rate
    net_cash_proj = revenue - om_cost_year - income_tax_proj
    project_cash_flows.append(net_cash_proj)

    taxable_income_equity = max(ebitda - depreciation - interest_payment, 0)
    income_tax_equity = taxable_income_equity * tax_rate
    net_income_after_tax = ebitda - interest_payment - income_tax_equity
    net_cash_to_equity = net_income_after_tax + depreciation - principal_payment
    equity_cash_flows.append(net_cash_to_equity)

project_irr = npf.irr(project_cash_flows)
equity_irr = npf.irr(equity_cash_flows)
npv_project = npf.npv(discount_rate, project_cash_flows)

total_discounted_costs = capital_cost + sum(
    om_costs[year - 1] / ((1 + discount_rate) ** year) for year in range(1, project_life + 1)
)
total_discounted_energy = sum(
    energy_outputs[year - 1] / ((1 + discount_rate) ** year) for year in range(1, project_life + 1)
)
lcoe = total_discounted_costs / total_discounted_energy if total_discounted_energy > 0 else None

cumulative = 0
payback_period = None
for i, cf in enumerate(project_cash_flows[1:], 1):
    cumulative += cf
    if cumulative >= capital_cost:
        payback_period = i
        break

feasibility = "Feasible" if project_irr >= discount_rate else "Not Feasible"

# --- Output ---
st.subheader("Input Summary")
st.write(f"Plant Capacity: {plant_capacity_mw:.2f} MW")
st.write(f"CUF: {cuf * 100:.2f} %")
st.write(f"Capital Cost: ₹{capital_cost:,.0f}")
st.write(f"Tariff: ₹{tariff:.2f} / kWh")
st.write(f"Panel Type: {panel_type}")
st.write(f"State Selected: {selected_state}")
st.write(f"Land per MW: {land_per_mw:.2f} acres")
st.write(f"Total Land Required: {total_land_required_acres:.2f} acres ({total_land_required_hectares:.2f} hectares)")

st.subheader("Financial Metrics")
col1, col2 = st.columns(2)
col1.metric("Project IRR", f"{project_irr * 100:.2f} %")
col1.metric("Equity IRR", f"{equity_irr * 100:.2f} %")
col2.metric("NPV (Project)", f"₹{npv_project:,.0f}")
col2.metric("LCOE", f"₹{lcoe:.2f} / kWh" if lcoe else "N/A")
col2.metric("Payback Period", f"{payback_period} years" if payback_period else "Not within project life")
col2.metric("Feasibility", feasibility)

# --- Cash Flow Table ---
years = list(range(1, project_life + 1))
revenue_list, ebitda_list, profit_list = [], [], []
discounted_cf_proj, discounted_cf_equity = [], []
cumulative_cf_proj = [-capital_cost]
cumulative_cf_equity = [-equity_amount]

cum_proj = -capital_cost
cum_equity = -equity_amount
remaining_loan_check = loan_amount

for year, energy, om_cost_year in zip(years, energy_outputs, om_costs):
    revenue = energy * tariff
    depreciation = capital_cost * depreciation_rate
    interest_payment = remaining_loan_check * loan_interest_rate if year <= loan_tenure else 0
    principal_payment = emi - interest_payment if year <= loan_tenure else 0
    if year <= loan_tenure:
        remaining_loan_check -= principal_payment

    ebitda = revenue - om_cost_year
    taxable_income_proj = revenue - om_cost_year - depreciation
    income_tax_proj = max(taxable_income_proj, 0) * tax_rate
    profit_proj = taxable_income_proj - income_tax_proj

    net_cash_proj = revenue - om_cost_year - income_tax_proj
    discounted_proj = net_cash_proj / ((1 + discount_rate) ** year)
    cum_proj += net_cash_proj

    taxable_income_equity = max(ebitda - depreciation - interest_payment, 0)
    income_tax_equity = taxable_income_equity * tax_rate
    net_income_after_tax = ebitda - interest_payment - income_tax_equity
    net_cash_to_equity = net_income_after_tax + depreciation - principal_payment
    discounted_equity = net_cash_to_equity / ((1 + discount_rate) ** year)
    cum_equity += net_cash_to_equity

    revenue_list.append(revenue)
    ebitda_list.append(ebitda)
    profit_list.append(profit_proj)
    discounted_cf_proj.append(discounted_proj)
    discounted_cf_equity.append(discounted_equity)
    cumulative_cf_proj.append(cum_proj)
    cumulative_cf_equity.append(cum_equity)

df = pd.DataFrame({
    "Year": [0] + years,
    "Energy Output (kWh)": [0] + [round(e) for e in energy_outputs],
    "Revenue (₹)": [0] + [round(r) for r in revenue_list],
    "O&M Cost (₹)": [0] + [round(c) for c in om_costs],
    "EBITDA (₹)": [0] + [round(e) for e in ebitda_list],
    "Profit (₹)": [-capital_cost] + [round(p) for p in profit_list],
    "Discounted CF (Project) (₹)": project_cash_flows,
    "Cumulative CF (Project) (₹)": cumulative_cf_proj,
    "Discounted CF (Equity) (₹)": [0] + [round(d) for d in discounted_cf_equity],
    "Cumulative CF (Equity) (₹)": cumulative_cf_equity,
})

st.subheader("Detailed Cash Flow")
st.dataframe(df.style.format({
    "Revenue (₹)": "₹{:,.0f}",
    "O&M Cost (₹)": "₹{:,.0f}",
    "EBITDA (₹)": "₹{:,.0f}",
    "Profit (₹)": "₹{:,.0f}",
    "Discounted CF (Project) (₹)": "₹{:,.0f}",
    "Cumulative CF (Project) (₹)": "₹{:,.0f}",
    "Discounted CF (Equity) (₹)": "₹{:,.0f}",
    "Cumulative CF (Equity) (₹)": "₹{:,.0f}",
}))

# --- Download CSV ---
buffer = io.StringIO()
df.to_csv(buffer, index=False)
st.download_button(
    label="Download Cash Flow as CSV",
    data=buffer.getvalue(),
    file_name="solar_cash_flow.csv",
    mime="text/csv"
)
