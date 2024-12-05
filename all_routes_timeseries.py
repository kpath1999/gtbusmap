import pandas as pd
import folium
import os
from datetime import datetime
from folium.plugins import MousePosition
import numpy as np

def get_time_of_day(phase):
    if phase == 1:
        return "Morning"
    elif phase == 2:
        return "Noon"
    elif phase == 3:
        return "Afternoon"
    elif phase == 4:
        return "Evening"
    else:
        return "Night"

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

def create_route_layer(df, route_name, map_object, initial_phase):
    feature_group = folium.FeatureGroup(name=route_name)
    
    # Drop rows with missing lat/lon and sort by time
    df = df.dropna(subset=['latitude', 'longitude']).sort_values('time')
    
    def create_phase_layer(phase):
        phase_group = folium.FeatureGroup(name=f"{route_name}, {get_time_of_day(phase)}")
        for i in range(len(df) - 1):
            start_row = df.iloc[i]
            end_row = df.iloc[i + 1]
            
            # Draw the line segment
            folium.PolyLine(
                locations=[[start_row['latitude'], start_row['longitude']],
                           [end_row['latitude'], end_row['longitude']]],
                color=get_color_for_condition(start_row[f'road_condition_{phase}']),
                weight=7,
                opacity=0.7,
                popup=f"{route_name} - Ride Quality: {start_row[f'road_condition_{phase}']:.2f}"
            ).add_to(phase_group)
        return phase_group
    
    # Create initial phase layer
    initial_phase_layer = create_phase_layer(initial_phase)
    initial_phase_layer.add_to(feature_group)
    
    feature_group.add_to(map_object)
    return feature_group, create_phase_layer

# Load the data
blue_df = pd.read_csv("condensed/blue_timeseries.csv")
red_df = pd.read_csv("condensed/red_timeseries.csv")
green_df = pd.read_csv("condensed/green_timeseries.csv")
gold_df = pd.read_csv("condensed/gold_timeseries.csv")

# Initialize the map
center_lat = np.mean([df['latitude'].mean() for df in [blue_df, red_df, green_df, gold_df]])
center_lon = np.mean([df['longitude'].mean() for df in [blue_df, red_df, green_df, gold_df]])
map_ = folium.Map(location=[center_lat, center_lon], zoom_start=16)

# Add phase control
phase_control = folium.LayerControl(collapsed=False, name="Phase")
map_.add_child(phase_control)

# Create layers for each route
phase_layers = {}
for route, df in zip(['Blue', 'Red', 'Green', 'Gold'], [blue_df, red_df, green_df, gold_df]):
    route_layer, create_phase_func = create_route_layer(df, f'{route} Route', map_, 1)
    phase_layers[route] = create_phase_func
    route_layer.add_to(map_)

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
    var currentPhase = 1;
    
    // Hide the OpenStreetMap option
    labels[0].style.display = 'none';
    
    // Retrieve each route layer and save them
    Array.from(layers).forEach((layer, index) => {
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
    
    // Add phase toggle buttons
    var phaseControl = L.control({position: 'bottomright'});
    phaseControl.onAdd = function(map) {
        var div = L.DomUtil.create('div', 'phase-control');
        div.innerHTML = '<button id="prevPhase">◀</button> <span id="currentPhase">Phase 1</span> <button id="nextPhase">▶</button>';
        return div;
    };
    phaseControl.addTo(map);
    
    // Phase toggle functionality
    document.getElementById('prevPhase').addEventListener('click', function() {
        currentPhase = currentPhase > 1 ? currentPhase - 1 : 5;
        updatePhase();
    });
    document.getElementById('nextPhase').addEventListener('click', function() {
        currentPhase = currentPhase < 5 ? currentPhase + 1 : 1;
        updatePhase();
    });
    
    function updatePhase() {
        document.getElementById('currentPhase').textContent = 'Phase ' + currentPhase;
        
        map.eachLayer(function(layer) {
            if (layer instanceof L.FeatureGroup) {
                map.removeLayer(layer);
                var routeName = layer.options.name.split(',')[0].trim();
                if (phase_layers[routeName]) {
                    var newPhaseLayer = phase_layers[routeName](currentPhase);
                    newPhaseLayer.addTo(map);
                }
            }
        });
    }
});
</script>
"""

# Add this function to your Python code to make phase_layers available in JavaScript
map_.get_root().script.add_child(folium.Element(f"""
    var phase_layers = {{}};
    {';'.join([f"phase_layers['{route}'] = {phase_func.__name__}" for route, phase_func in phase_layers.items()])};
"""))

# Save map to HTML file
viz_dir = "C:/temp/bus_maps"
if not os.path.exists(viz_dir):
    os.makedirs(viz_dir)
timenow = datetime.now().strftime("%Y%m%d%H%M%S")
output_path = os.path.join(viz_dir, f"all_routes_map_{timenow}.html")

map_.save(output_path)

# Add XOR JavaScript and CSS to the saved HTML file
with open(output_path, 'r') as file:
    content = file.read()
    content = content.replace('</head>', '''
    <style>
    .phase-control {
        background: white;
        padding: 5px;
        border-radius: 5px;
    }
    .phase-control button {
        cursor: pointer;
    }
    </style>
    </head>''')
    content = content.replace('</body>', xor_js + '</body>')
    
with open(output_path, 'w') as file:
    file.write(content)