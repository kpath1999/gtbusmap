import pandas as pd
import folium
import os
from datetime import datetime
from folium.plugins import MousePosition
import numpy as np

def get_color_for_condition(condition):
    if condition <= 0:
        return '#808080'  # Gray for unavailable data
    elif condition <= 1:
        return '#FF0000'  # Red for poor quality
    elif condition <= 2:
        return '#FF7F00'  # Orange for below average
    elif condition <= 3:
        return '#FFFF00'  # Yellow for average
    elif condition <= 4:
        return '#7FFF00'  # Chartreuse for good
    else:
        return '#00FF00'  # Green for excellent

def create_route_layer(df, route_name, map_object):
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
            color=get_color_for_condition(start_row['road_condition']),
            weight=7,
            opacity=0.7,
            popup=f"{route_name} - Avg Road Condition: {start_row['road_condition']:.2f}"
        ).add_to(feature_group)
    
    feature_group.add_to(map_object)
    return feature_group

# Load the data
blue_df = pd.read_csv("real_data/blue_road_all.csv")
red_df = pd.read_csv("real_data/red_road_all.csv")
green_df = pd.read_csv("real_data/green_road_all.csv")
gold_df = pd.read_csv("real_data/gold_road_all.csv")

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

# Save map to HTML file
viz_dir = "C:/temp/bus_maps"
if not os.path.exists(viz_dir):
    os.makedirs(viz_dir)
timenow = datetime.now().strftime("%Y%m%d%H%M%S")
output_path = os.path.join(viz_dir, f"all_routes_map_{timenow}.html")

map_.save(output_path)

# Add XOR JavaScript to the saved HTML file
with open(output_path, 'r') as file:
    content = file.read()
    content = content.replace('</body>', xor_js + '</body>')

with open(output_path, 'w') as file:
    file.write(content)