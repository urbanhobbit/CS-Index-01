import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np

# Load and prepare data
df_raw = pd.read_excel("SC Indicators Data Prep.xlsx", sheet_name="1.Legitimacy")

# Clean header and extract data
df = df_raw.copy()
df.columns = df.iloc[1]  # Use second row as header
headers = df.iloc[0]      # Subdomain row

df = df[2:].reset_index(drop=True)
df.insert(0, "Country", df_raw.iloc[2:, 0].values)
df = df.drop(columns=["COUNTRY"])

# Build subdomain map
subdomain_map = {}
for col, sub in zip(df.columns[1:], headers[1:]):
    sub_str = str(sub)
    if sub_str not in subdomain_map:
        subdomain_map[sub_str] = []
    subdomain_map[sub_str].append(col)

# Global drag-and-drop subdomain selection
st.sidebar.markdown("### Select Subdomains for Composite Index")
all_subdomains = list(subdomain_map.keys())
ordered_subdomains = st.sidebar.multiselect("Order and Select Subdomains", options=all_subdomains, default=all_subdomains)

# Sidebar - Indicator selection within subdomains with select/deselect all toggle
st.sidebar.markdown("### Indicators by Subdomain")
global_toggle = st.sidebar.checkbox("Select/Deselect All Indicators", value=True)
normalize_all = st.sidebar.checkbox("Normalize All Indicators (HDI-like)", value=False)

selected_indicators = []
for sub in ordered_subdomains:
    indicators = subdomain_map[sub]
    with st.sidebar.expander(f"{sub} (Drag to Prioritize)", expanded=True):
        sub_toggle_all = st.checkbox(f"Select/Deselect All in {sub}", value=global_toggle, key=f"toggle_all_{sub}")
        selected = st.multiselect(f"{sub} Indicators", indicators, default=indicators if sub_toggle_all else [], key=f"selected_{sub}")
        selected_indicators.extend(selected)

# Country selection
all_countries = df["Country"].unique().tolist()
selected_countries = st.sidebar.multiselect("Countries", options=all_countries, default=all_countries, key="country_selector")

# Compute composite index
df_filtered = df[df["Country"].isin(selected_countries)]
df_numeric = df_filtered[selected_indicators].apply(pd.to_numeric, errors='coerce')

if normalize_all:
    df_normalized = df_numeric.copy()
    for col in df_numeric.columns:
        min_val = df_numeric[col].min()
        max_val = df_numeric[col].max()
        df_normalized[col] = (df_numeric[col] - min_val) / (max_val - min_val)
    df_filtered["Composite Index"] = df_normalized.mean(axis=1, skipna=True)
    df_filtered["Normalized Index"] = df_filtered["Composite Index"]
else:
    df_filtered["Composite Index"] = df_numeric.mean(axis=1, skipna=True)
    df_filtered["Normalized Index"] = df_filtered["Composite Index"]

# Extract EU average for baseline
try:
    eu_average = df_filtered[df_filtered["Country"] == "EU27"]["Composite Index"].values[0]
except IndexError:
    eu_average = None

# Main panel - Output
st.title("Legitimacy Composite Index Dashboard")
st.markdown("Average and normalized values of selected indicators by country with EU baseline.")

# Optional summary stats panel
if selected_indicators and st.checkbox("Show Summary Statistics"):
    st.subheader("Summary Statistics for Selected Indicators")
    stats_df = df_numeric[selected_indicators].agg(['mean', 'std', 'min', 'max']).transpose()
    stats_df.columns = ['Mean', 'Std. Dev.', 'Min', 'Max']
    st.dataframe(stats_df.style.format("{:.2f}"))

# Optional country comparison
if st.checkbox("Enable Country Comparison"):
    with st.expander("Compare Two Countries"):
        country1 = st.selectbox("Select First Country", selected_countries, key="compare1")
        country2 = st.selectbox("Select Second Country", selected_countries, key="compare2")
        if country1 != country2:
            comp_data = df_filtered[df_filtered["Country"].isin([country1, country2])]
            st.bar_chart(comp_data.set_index("Country")["Normalized Index"])

# Visualization mode selector
viz_mode = st.radio("Select Visualization Mode", ["Bar Chart", "Choropleth Map", "Both"], horizontal=True)

if viz_mode in ["Bar Chart", "Both"]:
    fig, ax = plt.subplots(figsize=(10, 6))
    df_plot = df_filtered.set_index("Country")["Normalized Index"].sort_values()
    colors = ['red' if idx == "EU27" else 'blue' for idx in df_plot.index]
    df_plot.plot(kind='barh', ax=ax, color=colors)
    if eu_average:
        ax.axvline(eu_average, color='red', linestyle='--', label='EU27 Avg')
        ax.legend()
    ax.set_xlabel("Normalized Index" if normalize_all else "Composite Index")
    ax.set_ylabel("Country")
    ax.set_title("Normalized Composite Index by Country" if normalize_all else "Composite Index by Country")
    st.pyplot(fig)

# Show data table
st.subheader("Composite Index Table")
st.dataframe(df_filtered[["Country"] + selected_indicators + ["Composite Index", "Normalized Index"]])

# Export options
st.download_button("Download Table as CSV", df_filtered.to_csv(index=False), file_name="composite_index.csv")

# Choropleth map using Plotly
if viz_mode in ["Choropleth Map", "Both"]:
    st.subheader("Choropleth Map")

    iso_alpha3 = {
        "BE": "BEL", "BG": "BGR", "DE": "DEU", "FR": "FRA", "IT": "ITA",
        "ES": "ESP", "PL": "POL", "RO": "ROU", "NL": "NLD", "SE": "SWE", "CZ": "CZE",
        "EU27": "EUU"
    }

    map_data = df_filtered[df_filtered["Country"].isin(iso_alpha3.keys())].copy()
    map_data["iso_alpha"] = map_data["Country"].map(iso_alpha3)

    indicator_to_map = st.selectbox("Select Indicator to Map", options=selected_indicators + ["Composite Index", "Normalized Index"])

    map_data[indicator_to_map] = pd.to_numeric(map_data[indicator_to_map], errors='coerce')
    map_data = map_data.dropna(subset=[indicator_to_map])

    fig = px.choropleth(
        map_data,
        locations="iso_alpha",
        color=indicator_to_map,
        hover_name="Country",
        color_continuous_scale="Blues",
        scope="europe",
        title=f"{indicator_to_map} by Country"
    )
    st.plotly_chart(fig, use_container_width=True)
