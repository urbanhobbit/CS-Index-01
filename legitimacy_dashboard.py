import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
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

# Normalize domain and subdomain indices
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
    colors_dom = ['red' if idx == "EU" else 'blue' for idx in df_plot_dom.index]
    fig_dom, ax_dom = plt.subplots(figsize=(10, 6))
    df_plot_dom[selected_domain_to_plot].plot(kind='barh', ax=ax_dom, color=colors_dom)
    ax_dom.set_xlabel("Composite Index")
    ax_dom.set_ylabel("Country")
    ax_dom.set_title(f"{selected_domain_to_plot} Index by Country")
    st.pyplot(fig_dom)

    st.subheader("Bar Chart for Subdomain Index")
    selected_subdomain_to_plot = st.selectbox("Select a Subdomain to Plot", options=df_sub.columns[1:], key="subdomain_plot")
    df_plot_sub = df_sub.set_index("Country")[[selected_subdomain_to_plot]].sort_values(by=selected_subdomain_to_plot)
    colors_sub = ['red' if idx == "EU" else 'blue' for idx in df_plot_sub.index]
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

# Indicator Charts Section
show_indicator_charts = st.checkbox("Show Indicator Charts", value=False)

if show_indicator_charts:
    st.subheader("Bar Chart for Indicator")
    norm_or_raw = st.radio("Show indicators as:", ["Normalized", "Raw"], horizontal=True)
    sort_order = st.radio("Sort order:", ["Descending", "Ascending"], horizontal=True, key="sort_order")
    ascending = sort_order == "Ascending"

    indicator_df = df_full if norm_or_raw == "Normalized" else pd.concat([df[["Country"]], df_raw_indicators], axis=1)

    grouped_options = {sub: indicators for sub, indicators in grouped_indicators.items() if any(i in indicator_df.columns for i in indicators)}
    if not grouped_options:
        st.warning("No available indicators in the selected structure.")
    else:
        subdomain_selected = st.selectbox("Select a Subdomain", list(grouped_options.keys()), key="subdomain_group")
        indicators_in_group = [i for i in grouped_options[subdomain_selected] if i in indicator_df.columns]
        selected_indicator_to_plot = st.selectbox("Select an Indicator to Plot", options=indicators_in_group, key="indicator_plot")

        df_plot_ind = indicator_df.set_index("Country")[[selected_indicator_to_plot]].sort_values(by=selected_indicator_to_plot, ascending=ascending)
        colors_ind = ['red' if idx == "EU" else 'blue' for idx in df_plot_ind.index]
        fig_ind, ax_ind = plt.subplots(figsize=(10, 6))
        df_plot_ind[selected_indicator_to_plot].plot(kind='barh', ax=ax_ind, color=colors_ind)
        ax_ind.set_xlabel("Indicator Value")
        ax_ind.set_ylabel("Country")
        ax_ind.set_title(f"{selected_indicator_to_plot} by Country ({norm_or_raw})")
        st.pyplot(fig_ind)

        if norm_or_raw == "Normalized":
            st.caption("Values are normalized using min-max scaling to a 0–1 range.")
        else:
            st.caption("Values reflect original scales without normalization.")

# Scatter Plot Comparison
show_scatter = st.checkbox("Show Scatter Plot for Domain/Subdomain Comparison", value=False)
if show_scatter:
    st.subheader("Scatter Plot of Indices")
    level = st.radio("Select level of indices:", ["Domain", "Subdomain"], horizontal=True, key="scatter_level")
    df_to_plot = df_dom if level == "Domain" else df_sub
    x_axis = st.selectbox("Select X-axis index:", df_to_plot.columns[1:], key="x_axis")
    y_axis = st.selectbox("Select Y-axis index:", df_to_plot.columns[1:], key="y_axis")
    fig_scatter = px.scatter(df_to_plot, x=x_axis, y=y_axis, text="Country", color=np.where(df_to_plot["Country"]=="EU", "EU", "Other"))
    fig_scatter.update_traces(textposition='top center')
    fig_scatter.update_layout(title=f"{x_axis} vs {y_axis} by Country")
    st.plotly_chart(fig_scatter, use_container_width=True)

# Radar Chart Comparison
show_radar = st.checkbox("Show Radar Chart for Country Profiles", value=False)
if show_radar:
    st.subheader("Radar Chart Comparison")
    level = st.radio("Select level of indices:", ["Domain", "Subdomain"], horizontal=True, key="radar_level")
    df_radar = df_dom if level == "Domain" else df_sub
    available_countries = df_radar["Country"].tolist()

    # Set default to 'EU' only if it exists in the available countries
    default_countries = ["EU"] if "EU" in available_countries else []

    # Use the multiselect widget to select countries for comparison
    selected_countries_radar = st.multiselect(
        "Select countries to compare:",
        available_countries,
        default=default_countries  # Dynamically set the default
    )

    dimensions = df_radar.columns[1:]
    fig_radar = go.Figure()
    for country in selected_countries_radar:
        values = df_radar[df_radar["Country"] == country][dimensions].values.flatten().tolist()
        fig_radar.add_trace(go.Scatterpolar(r=values, theta=dimensions, fill='toself', name=country))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])), showlegend=True)
    st.plotly_chart(fig_radar, use_container_width=True)
