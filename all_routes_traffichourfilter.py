import pandas as pd
import folium
import os
from datetime import datetime
from folium.plugins import MousePosition
import numpy as np

def filter_df_by_hour(df, hour):
    df['hour_filter'] = pd.to_datetime(df['est_time'], format='%H:%M:%S', errors='coerce').dt.hour
    print(df.head())  # Check if est_time is correctly converted
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

def create_route_layer(df, route_name, map_object, hour=None):
    if hour is not None:
        df = filter_df_by_hour(df, hour)
    
    feature_group = folium.FeatureGroup(name=route_name)
    
    # Drop rows with missing lat/lon and sort by time
    df = df.dropna(subset=['latitude', 'longitude']).sort_values('time')
    
    for i in range(len(df) - 1):
        start_row = df.iloc[i]
        end_row = df.iloc[i + 1]
        
        # Draw the line segment
        folium.PolyLine(
            locations=[[start_row['latitude'], start_row['longitude']],
                       [end_row['latitude'], end_row['longitude']]],
            color=get_color_for_condition(start_row['traffic_congestion']),
            weight=7,
            opacity=0.7,
            popup=f"{route_name}, {start_row['est_time']}, {describe_congestion(start_row['traffic_congestion'])}"
        ).add_to(feature_group)
    
    feature_group.add_to(map_object)
    return feature_group

# Load the data
blue_df = pd.read_csv("real_data/blue_traffic.csv")
red_df = pd.read_csv("real_data/red_traffic.csv")
green_df = pd.read_csv("real_data/green_traffic.csv")
gold_df = pd.read_csv("real_data/gold_traffic.csv")

# Initialize the map
center_lat = np.mean([df['latitude'].mean() for df in [blue_df, red_df, green_df, gold_df]])
center_lon = np.mean([df['longitude'].mean() for df in [blue_df, red_df, green_df, gold_df]])
map_ = folium.Map(location=[center_lat, center_lon], zoom_start=16)

# Create layers for each route
blue_layer = create_route_layer(blue_df, 'Blue Route', map_)
red_layer = create_route_layer(red_df, 'Red Route', map_)
green_layer = create_route_layer(green_df, 'Green Route', map_)
gold_layer = create_route_layer(gold_df, 'Gold Route', map_)

# Add XOR-style layer control
folium.LayerControl(collapsed=False).add_to(map_)

# Add mouse position
formatter = "function(num) {return L.Util.formatNum(num, 5);};"
MousePosition(
    position='topright',
    separator=' | ',
    empty_string='NaN',
    lng_first=True,
    num_digits=20,
    prefix='Coordinates:',
    lat_formatter=formatter,
    lng_formatter=formatter,
).add_to(map_)

hour_filter_html = """
<div id="hour-filter" style="
    position: absolute;
    top: 140px;
    right: 10px;
    z-index: 1000;
    background: white;
    padding: 10px;
    border-radius: 5px;
    box-shadow: 0 0 15px rgba(0,0,0,0.2);">
    <label for="hour-select">Filter by Hour:</label>
    <select id="hour-select">
        <option value="">All Hours</option>
        <option value="7">7 AM</option>
        <option value="8">8 AM</option>
        <option value="9">9 AM</option>
        <option value="10">10 AM</option>
        <option value="11">11 AM</option>
        <option value="12">12 PM</option>
        <option value="13">1 PM</option>
        <option value="14">2 PM</option>
        <option value="15">3 PM</option>
        <option value="16">4 PM</option>
        <option value="17">5 PM</option>
        <option value="18">6 PM</option>
        <option value="19">7 PM</option>
    </select>
</div>
"""

xor_js = """
<script type="text/javascript">
document.addEventListener("DOMContentLoaded", function() {
    var layers = document.getElementsByClassName("leaflet-control-layers-selector");
    var routeLayers = {}; // Store each route's map layer element
    var labels = document.getElementsByClassName("leaflet-control-layers-base")[0].getElementsByTagName("label");
    
    // Hide the OpenStreetMap option
    labels[0].style.display = 'none';
    
    // Retrieve each route layer and save them
    layers.forEach((layer, index) => {
        if (index > 0) {  // Skip the first checkbox (OpenStreetMap)
            routeLayers[layer.value] = layer;
            layer.type = "radio";
            layer.name = "route-selector";
            layer.checked = false; // Uncheck all layers initially
            layer.style.appearance = "none";
            // Other styling here as needed
            layer.addEventListener("change", function() {
                // Toggle route layers based on selected radio button
                Object.keys(routeLayers).forEach(key => {
                    routeLayers[key].style.display = key === this.value ? 'block' : 'none';
                });
            });
        }
    });
});
</script>
"""

hour_filter_js = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    var hourSelect = document.getElementById('hour-select');
    hourSelect.addEventListener('change', function() {
        var selectedHour = this.value;
        console.log("Selected Hour:", selectedHour); // Debugging the selected hour
        var layers = document.getElementsByClassName("leaflet-control-layers-selector");
        layers.forEach((layer, index) => {
            if (index > 0) {  // Skip the first checkbox (OpenStreetMap)
                var layerName = layer.nextSibling.textContent.trim();
                console.log("Layer Name:", layerName); // Debugging layer name
                if (layer.checked) {
                    // Remove existing layer
                    map.removeLayer(window[layerName.toLowerCase().replace(' ', '_') + '_layer']);
                    // Add new filtered layer
                    window[layerName.toLowerCase().replace(' ', '_') + '_layer'] = 
                        create_route_layer(window[layerName.toLowerCase().replace(' ', '_') + '_df'], 
                                           layerName, map, selectedHour ? parseInt(selectedHour) : null);
                }
            }
        });
    });
});
</script>
"""

# Save map to HTML file
viz_dir = "C:/temp/bus_maps"
if not os.path.exists(viz_dir):
    os.makedirs(viz_dir)
timenow = datetime.now().strftime("%Y%m%d%H%M%S")
output_path = os.path.join(viz_dir, f"all_routes_map_{timenow}.html")

map_.save(output_path)

# Add XOR JavaScript and hour filter to the saved HTML file
with open(output_path, 'r') as file:
    content = file.read()
    content = content.replace('</body>', hour_filter_html + xor_js + hour_filter_js + '</body>')

with open(output_path, 'w') as file:
    file.write(content)