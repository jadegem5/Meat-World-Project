import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim

# Load Meat Production Data
@st.cache_data
def load_meat_data():
    url = "https://raw.githubusercontent.com/jadegem5/Meat-World-Project/refs/heads/main/global-meat-production.csv"
    df = pd.read_csv(url)
    df.rename(columns={
        "Entity": "Country",
        "Meat, total | 00001765 || Production | 005510 || tonnes": "Meat_Production"
    }, inplace=True)
    return df

# Load Agricultural Land Data
@st.cache_data
def load_agriculture_data():
    url = "https://raw.githubusercontent.com/jadegem5/Meat-World-Project/refs/heads/main/total-agricultural-area-over-the-long-term.csv"
    df = pd.read_csv(url)
    df.rename(columns={
        "Entity": "Country",
        "Land use: Agriculture": "Agricultural_Area"
    }, inplace=True)
    return df

# Load Meat Consumption Data
@st.cache_data
def load_consumption_data():
    url = "https://raw.githubusercontent.com/jadegem5/Meat-World-Project/refs/heads/main/export-2024-11-27T21_19_40.901Z.csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.replace('"', '').str.strip()
    return df

# Load Obesity Data
@st.cache_data
def load_obesity_data():
    url = "https://raw.githubusercontent.com/jadegem5/Meat-World-Project/refs/heads/main/share-of-adults-defined-as-obese.csv"
    df = pd.read_csv(url)
    df.rename(columns={'Entity': 'Country'}, inplace=True)
    df.rename(columns={'Prevalence of obesity among adults, BMI >= 30 (crude estimate) (%) - Sex: both sexes - Age group: 18+  years': 'Obesity'}, inplace=True)
    return df

# Function to get country coordinates using Geopy
@st.cache_resource
def get_country_coordinates(country_list):
    geolocator = Nominatim(user_agent="data-visualization-app")
    coordinates = []
    for country in country_list:
        location = geolocator.geocode(country)
        if location:
            coordinates.append((country, location.latitude, location.longitude))
        else:
            coordinates.append((country, None, None))  # Handle missing coordinates
    return pd.DataFrame(coordinates, columns=["Country", "Latitude", "Longitude"])

# App title
st.title("Global Trends in Meat Production, Consumption, Obesity, and Land Use")

# User input to select dataset
dataset_choice = st.radio(
    "Choose the dataset to visualize",
    ("Meat Production", "Agricultural Land Use", "Meat Consumption", "Obesity")
)

# Visualizations based on dataset choice
if dataset_choice == "Meat Production" or dataset_choice == "Agricultural Land Use":
    # Load the selected dataset
    if dataset_choice == "Meat Production":
        data = load_meat_data()
        st.header("Meat Production Data Visualization")
        st.markdown("""
        ### Global Meat Production
        This visualization displays trends in meat production across the top ten meat producing countries. Select 'Map' to see a geographical representation, where the larger the dot, the higher the meat production is in that country. Try hovering over the dots to see a specific number in tonnes. Alternatively, select 'Line Graph' to view how meat production has evolved over time for a selected set of countries.
        """)
        selected_countries = [
            "United States", "Argentina", "Pakistan", "Germany", "India",
            "Brazil", "China", "Russia", "Mexico", "Spain"
        ]
    elif dataset_choice == "Agricultural Land Use":
        data = load_agriculture_data()
        st.header("Agricultural Land Use Over Time")
        st.markdown("""
        ### Agricultural Land Use Over Time
        This visualization shows the changes in agricultural land use in the ten countries with the largest agricultural land use. Most of these countries overlap with the top ten countries for meat production. You can view the data by selecting 'Map' to see the spatial distribution of agricultural land, or 'Line Graph' to see how the area used for agriculture has evolved in different countries.
        """)
        selected_countries = [
            "United States", "Argentina","India","Australia", "Brazil",
            "Kazakhstan","China","Russia", "Mexico","Saudi Arabia"
        ]

    # Year selection
    year = st.slider(
        label="Select a Year",
        min_value=int(data["Year"].min()),
        max_value=int(data["Year"].max()),
        value=int(data["Year"].min()) if dataset_choice != "Agricultural Land Use" else 1600,
        step=1
    )
    # Filter data for the selected year
    filtered_data = data[data["Year"] == year]
    filtered_data = filtered_data[filtered_data["Country"].isin(selected_countries)]

    # Get coordinates for the selected countries
    coordinates = get_country_coordinates(selected_countries)
    filtered_data = pd.merge(filtered_data, coordinates, on="Country", how="left")

    # Ensure numeric values for plotting
    if dataset_choice == "Meat Production":
        filtered_data["Meat_Production"] = pd.to_numeric(filtered_data["Meat_Production"], errors="coerce")
    elif dataset_choice == "Agricultural Land Use":
        filtered_data["Agricultural_Area"] = pd.to_numeric(filtered_data["Agricultural_Area"], errors="coerce")

    # Drop rows with missing coordinates
    filtered_data = filtered_data.dropna(subset=["Latitude", "Longitude"])

    # User input option for map or line graph
    visualization_choice = st.radio(
        "Choose Visualization Type",
        ("Map", "Line Graph")
    )

    if visualization_choice == "Map":
        if dataset_choice == "Meat Production":
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=filtered_data,
                get_position="[Longitude, Latitude]",
                get_radius="Meat_Production / 10",
                get_fill_color="[255, 100, Meat_Production / 10000]",
                get_line_color="[0, 0, 0, 50]",
                opacity=0.5,
                pickable=True,
            )
            tooltip = {"text": "{Country}: {Meat_Production} tonnes"}
        elif dataset_choice == "Agricultural Land Use":
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=filtered_data,
                get_position="[Longitude, Latitude]",
                get_radius="Agricultural_Area / 1000",
                get_fill_color="[100, 200, Agricultural_Area / 5000, 150]",
                opacity=0.5,
                pickable=True,
            )
            tooltip = {"text": "{Country}: {Agricultural_Area} sq. km"}

        view_state = pdk.ViewState(
            latitude=20,
            longitude=0,
            zoom=1.5,
            pitch=0
        )

        st.pydeck_chart(pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip=tooltip
        ))

    elif visualization_choice == "Line Graph":
        if dataset_choice == "Meat Production":
            line_graph_data = data[data["Country"].isin(selected_countries)]
            line_graph_data["Meat_Production"] = pd.to_numeric(line_graph_data["Meat_Production"], errors="coerce")
            line_graph_data = line_graph_data.groupby(["Year", "Country"])["Meat_Production"].sum().reset_index()

            fig, ax = plt.subplots(figsize=(10, 6))
            for country in selected_countries:
                country_data = line_graph_data[line_graph_data["Country"] == country]
                ax.plot(country_data["Year"], country_data["Meat_Production"], label=country)

            ax.set_xlabel("Year")
            ax.set_ylabel("Meat Production (Tonnes)")
            ax.set_title("Meat Production Over Time for Selected Countries")
            ax.legend(title="Countries")
            st.pyplot(fig)

        elif dataset_choice == "Agricultural Land Use":
            line_graph_data = data[(data["Year"] >= 1600) & (data["Country"].isin(selected_countries))]
            line_graph_data["Agricultural_Area"] = pd.to_numeric(line_graph_data["Agricultural_Area"], errors="coerce")
            line_graph_data = line_graph_data.groupby(["Year", "Country"])["Agricultural_Area"].sum().reset_index()

            fig, ax = plt.subplots(figsize=(10, 6))
            for country in selected_countries:
                country_data = line_graph_data[line_graph_data["Country"] == country]
                ax.plot(country_data["Year"], country_data["Agricultural_Area"], label=country)

            ax.set_xlim(1600, int(data["Year"].max()))
            ax.set_xlabel("Year")
            ax.set_ylabel("Agricultural Area (sq. km)")
            ax.set_title("Agricultural Area Over Time for Selected Countries")
            ax.legend(title="Countries")
            st.pyplot(fig)

elif dataset_choice == "Meat Consumption":
    data = load_consumption_data()
    st.header("Meat Consumption Data Visualization")
    st.markdown("""
    ### Top Countries for Beef Consumption
    This histogram shows the top 10 countries with the highest beef consumption per capita in 2023. The countries are sorted in descending order based on the amount of beef consumed per person, measured in kilograms. This gives a comparative view of global beef consumption patterns.
    """)
    top_5 = data.nlargest(10, 'Kilograms/capita')

    fig = px.histogram(top_5, x='Country', y='Kilograms/capita',
                       title='Top 10 Countries for Beef Consumption in 2023',
                       labels={'Kilograms/capita': 'Beef Consumption (kg/capita)'})
    st.plotly_chart(fig)

elif dataset_choice == "Obesity":
    data = load_obesity_data()
    st.header("Obesity Data Visualization")
    st.markdown("""
    ### Obesity Trends by Country
    This line graph tracks the prevalence of obesity among adults in the top 10 countries with the highest obesity rates. The data shows the percentage of adults with a BMI of 30 or more, from the earliest year available to the most recent. This provides an insight into how obesity rates have changed over time in these countries. Try hovering over the lines to get a specific number for a year.
    """)

    top_10_countries = data.sort_values(by='Obesity', ascending=False).head(10)

    recent_year = data['Year'].max()
    recent_data = data[data['Year'] == recent_year]

    continents = ['World', 'Asia', 'Africa', 'Europe', 'North America', 'South America', 'Oceania', 'Antarctica', 'Asia (excl. China and India)', 'Europe (excl. Russia)', 'South America (excl. Brazil)']

    recent_data = recent_data[~recent_data['Country'].isin(continents)]

    top_10_countries = recent_data.sort_values(by = ['Obesity'], ascending = False)['Country'].head(10).tolist()
    filtered_df = data[data['Country'].isin(top_10_countries)]

    fig = px.line(filtered_df,
                  x='Year',
                  y='Obesity',
                  color='Country',
                  title='Top 10 Countries by Obesity Rate',
                  range_x=[1980, recent_year],
                  color_discrete_sequence=px.colors.qualitative.Set3)

    st.plotly_chart(fig)
