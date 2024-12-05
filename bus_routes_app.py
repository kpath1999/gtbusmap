import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np

def filter_df_by_hour(df, hour):
    df['hour_filter'] = pd.to_datetime(df['est_time'], format='%H:%M:%S', errors='coerce').dt.hour
    return df[df['hour_filter'] == hour]

def get_color_for_condition(condition):
    if condition <= 0:
        return '#808080'  # Gray for unavailable data
    elif condition <= 1:
        return '#00FF00'  # Green for excellent; no traffic congestion
    elif condition <= 2:
        return '#7FFF00'  # Chartreuse for good; minor traffic congestion
    elif condition <= 3:
        return '#FFFF00'  # Yellow for average; moderate traffic congestion
    elif condition <= 4:
        return '#FF7F00'  # Orange for below average; moderate-heavy traffic congestion
    else:
        return '#FF0000'  # Red for poor quality; heavy traffic congestion

def describe_congestion(num):
    if num <= 1:
        return "No Traffic Congestion"
    elif num <= 2:
        return "Minor Traffic Congestion"
    elif num <= 3:
        return "Moderate Traffic Congestion"
    elif num <= 4:
        return "Moderate-Heavy Traffic Congestion"
    else:
        return "Heavy Traffic Congestion"

def create_route_layer(df, route_name, hour=None):
    if hour is not None:
        df = filter_df_by_hour(df, hour)
    
    feature_group = folium.FeatureGroup(name=route_name)
    
    df = df.dropna(subset=['latitude', 'longitude']).sort_values('time')
    
    for i in range(len(df) - 1):
        start_row = df.iloc[i]
        end_row = df.iloc[i + 1]
        
        folium.PolyLine(
            locations=[[start_row['latitude'], start_row['longitude']],
                       [end_row['latitude'], end_row['longitude']]],
            color=get_color_for_condition(start_row['traffic_congestion']),
            weight=7,
            opacity=0.7,
            popup=f"{route_name}, {start_row['est_time']}, {describe_congestion(start_row['traffic_congestion'])}"
        ).add_to(feature_group)
    
    return feature_group

# Load the data
@st.cache_data
def load_data():
    return {
        "Blue Route": pd.read_csv("real_data/blue_traffic.csv"),
        "Red Route": pd.read_csv("real_data/red_traffic.csv"),
        "Green Route": pd.read_csv("real_data/green_traffic_merged.csv"),
        "Gold Route": pd.read_csv("real_data/gold_traffic_merged.csv")
    }

data = load_data()

st.title("Georgia Tech Traffic Congestion")

# Sidebar for controls
st.sidebar.header("Map Controls")
selected_route = st.sidebar.radio("Select Route", list(data.keys()))
selected_hour = st.sidebar.selectbox("Filter by Hour", ["All Hours"] + list(range(7, 20)))

# Initialize the map
center_lat = np.mean([df['latitude'].mean() for df in data.values()])
center_lon = np.mean([df['longitude'].mean() for df in data.values()])
m = folium.Map(location=[center_lat, center_lon], zoom_start=16)

# Add the selected route layer
hour = int(selected_hour) if selected_hour != "All Hours" else None
route_layer = create_route_layer(data[selected_route], selected_route, hour)
route_layer.add_to(m)

# Add layer control
folium.LayerControl(collapsed=False).add_to(m)

# Display the map
st_folium(m, width=700, height=500)

# Display statistics
st.subheader("Route Statistics")
filtered_data = filter_df_by_hour(data[selected_route], hour) if hour else data[selected_route]
st.write(f"Number of data points: {len(filtered_data)}")
st.write(f"Average traffic congestion: {filtered_data['traffic_congestion'].mean():.2f}")
st.write(f"Max traffic congestion: {filtered_data['traffic_congestion'].max():.2f}")
st.write(f"Min traffic congestion: {filtered_data['traffic_congestion'].min():.2f}")