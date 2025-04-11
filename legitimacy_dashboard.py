import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("Legitimacy Dashboard with Domains and Subdomains")

# Load the dataset directly
df_raw = pd.read_excel("SC Indicators Data Prep.xlsx", sheet_name=0, header=None)

domain_row = df_raw.iloc[0]
subdomain_row = df_raw.iloc[1]
indicator_row = df_raw.iloc[2]
data = df_raw.iloc[3:].reset_index(drop=True)
data.columns = indicator_row
data.insert(0, "Country", df_raw.iloc[3:, 0].values)

if "COUNTRY" in data.columns:
    data = data.drop(columns=["COUNTRY"])

hierarchy = pd.DataFrame({
    "Domain": domain_row[1:],
    "Subdomain": subdomain_row[1:],
    "Indicator": indicator_row[1:]
})

st.sidebar.header("Filter Structure")
all_domains = hierarchy["Domain"].unique()
select_all_domains = st.sidebar.checkbox("Select All Domains", value=True, key="select_all_domains")
selected_domains = st.sidebar.multiselect("Select Domains", options=all_domains, default=all_domains if select_all_domains else [])
filtered_hierarchy = hierarchy[hierarchy["Domain"].isin(selected_domains)]

all_subdomains = filtered_hierarchy["Subdomain"].unique()
select_all_subdomains = st.sidebar.checkbox("Select All Subdomains", value=True, key="select_all_subdomains")
selected_subdomains = st.sidebar.multiselect("Select Subdomains", options=all_subdomains, default=all_subdomains if select_all_subdomains else [])
filtered_hierarchy = filtered_hierarchy[filtered_hierarchy["Subdomain"].isin(selected_subdomains)]

countries = data["Country"].unique().tolist()
selected_countries = st.sidebar.multiselect("Select Countries", options=countries, default=countries)

df = data[data["Country"].isin(selected_countries)]
grouped_indicators = filtered_hierarchy.groupby("Subdomain")["Indicator"].apply(list).to_dict()

st.sidebar.markdown("### Select Indicators per Subdomain")
selected_indicators = []
select_all_indicators = st.sidebar.checkbox("Select All Indicators", value=True, key="select_all_indicators")

for subdomain, indicators in grouped_indicators.items():
    with st.sidebar.expander(f"{subdomain}", expanded=True):
        selected = st.multiselect(f"Indicators in {subdomain}", indicators, default=indicators if select_all_indicators else [], key=f"sel_{subdomain}")
        selected_indicators.extend(selected)

df_raw_indicators = df[selected_indicators].apply(pd.to_numeric, errors='coerce')
df_numeric = df_raw_indicators.copy()
for col in df_numeric.columns:
    min_val = df_numeric[col].min()
    max_val = df_numeric[col].max()
    if max_val > min_val:
        df_numeric[col] = (df_numeric[col] - min_val) / (max_val - min_val)

df_full = pd.concat([df[["Country"]], df_numeric], axis=1)

subdomain_indices = {}
for sub in filtered_hierarchy["Subdomain"].unique():
    inds = filtered_hierarchy[(filtered_hierarchy["Subdomain"] == sub) & (filtered_hierarchy["Indicator"].isin(selected_indicators))]["Indicator"].tolist()
    if inds:
        subdomain_indices[sub] = df_numeric[inds].mean(axis=1, skipna=True)

df_sub = pd.DataFrame(subdomain_indices)
df_sub.insert(0, "Country", df["Country"].values)

domain_indices = {}
for dom in filtered_hierarchy["Domain"].unique():
    subs = filtered_hierarchy[filtered_hierarchy["Domain"] == dom]["Subdomain"].unique()
    existing_subs = [s for s in subs if s in df_sub.columns]
    if existing_subs:
        domain_indices[dom] = df_sub[existing_subs].mean(axis=1, skipna=True)

df_dom = pd.DataFrame(domain_indices)
df_dom.insert(0, "Country", df["Country"].values)

for col in df_dom.columns[1:]:
    min_val = df_dom[col].min()
    max_val = df_dom[col].max()
    if max_val > min_val:
        df_dom[col] = (df_dom[col] - min_val) / (max_val - min_val)

show_tables = st.checkbox("Show Composite Index Tables", value=True)
show_bar_charts = st.checkbox("Show Bar Charts", value=True)
show_map = st.checkbox("Show Map", value=True)

if show_tables:
    st.subheader("Composite Indices by Domain")
    st.dataframe(df_dom)

    st.subheader("Composite Indices by Subdomain")
    st.dataframe(df_sub)

if show_bar_charts:
    st.subheader("Bar Chart for Domain Index")
    selected_domain_to_plot = st.selectbox("Select a Domain to Plot", options=df_dom.columns[1:], key="domain_plot")
    df_plot_dom = df_dom.set_index("Country")[[selected_domain_to_plot]].sort_values(by=selected_domain_to_plot)
    colors_dom = ['red' if idx == "EU27" else 'blue' for idx in df_plot_dom.index]
    fig_dom, ax_dom = plt.subplots(figsize=(10, 6))
    df_plot_dom[selected_domain_to_plot].plot(kind='barh', ax=ax_dom, color=colors_dom)
    ax_dom.set_xlabel("Composite Index")
    ax_dom.set_ylabel("Country")
    ax_dom.set_title(f"{selected_domain_to_plot} Index by Country")
    st.pyplot(fig_dom)

    st.subheader("Bar Chart for Subdomain Index")
    selected_subdomain_to_plot = st.selectbox("Select a Subdomain to Plot", options=df_sub.columns[1:], key="subdomain_plot")
    df_plot_sub = df_sub.set_index("Country")[[selected_subdomain_to_plot]].sort_values(by=selected_subdomain_to_plot)
    colors_sub = ['red' if idx == "EU27" else 'blue' for idx in df_plot_sub.index]
    fig_sub, ax_sub = plt.subplots(figsize=(10, 6))
    df_plot_sub[selected_subdomain_to_plot].plot(kind='barh', ax=ax_sub, color=colors_sub)
    ax_sub.set_xlabel("Composite Index")
    ax_sub.set_ylabel("Country")
    ax_sub.set_title(f"{selected_subdomain_to_plot} Index by Country")
    st.pyplot(fig_sub)

if show_map:
    st.subheader("Map: Selected Index")
    index_type = st.radio("Choose index type for map:", ["Domain", "Subdomain", "Indicator (normalized)", "Indicator (raw)"], horizontal=True)
    index_df = df_dom if index_type == "Domain" else df_sub if index_type == "Subdomain" else df_full if index_type == "Indicator (normalized)" else pd.concat([df[["Country"]], df_raw_indicators], axis=1)
    index_column = st.selectbox("Select index to map:", options=index_df.columns[1:], key="map_index")

    import pycountry
    def country_to_iso(name):
        try:
            return pycountry.countries.lookup(name).alpha_3
        except:
            return None

    df_map = index_df[["Country", index_column]].copy()
    df_map["iso_alpha"] = df_map["Country"].apply(country_to_iso)
    df_map = df_map.dropna(subset=["iso_alpha"])

    fig_map = px.choropleth(
        df_map,
        locations="iso_alpha",
        color=index_column,
        hover_name="Country",
        color_continuous_scale="Blues",
        scope="europe",
        title=f"{index_column} by Country"
    )
    fig_map.update_geos(
        projection_type="mercator",
        center={"lat": 35, "lon": 25},
        fitbounds="locations"
    )
    fig_map.update_layout(margin={"r":0,"t":30,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

st.download_button("Download Composite Index Data (Domains)", df_dom.to_csv(index=False), file_name="domain_indices.csv")
st.download_button("Download Composite Index Data (Subdomains)", df_sub.to_csv(index=False), file_name="subdomain_indices.csv")
