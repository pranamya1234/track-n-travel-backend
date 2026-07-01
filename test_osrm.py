import urllib.request
import json
import math

def haversine_distance(p1, p2):
    R = 6371.0
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def fetch_whole_osrm_route(stops):
    coords_str = ";".join([f"{stop['lon']},{stop['lat']}" for stop in stops])
    url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data.get("code") == "Ok" and data.get("routes"):
                coords = data["routes"][0]["geometry"]["coordinates"]
                return [(c[1], c[0]) for c in coords]
    except Exception as e:
        print(f"OSRM fetch failed: {e}")
    return None

def get_road_aligned_segments(stops, osrm_coords):
    segments = []
    curr_idx = 0
    
    def find_closest_index(stop, start_idx):
        min_dist = float('inf')
        closest_idx = start_idx
        stop_pos = (stop["lat"], stop["lon"])
        for idx in range(start_idx, len(osrm_coords)):
            d = haversine_distance(stop_pos, osrm_coords[idx])
            if d < min_dist:
                min_dist = d
                closest_idx = idx
        return closest_idx

    stop_indices = []
    for stop in stops:
        curr_idx = find_closest_index(stop, curr_idx)
        stop_indices.append(curr_idx)
        
    for i in range(len(stops) - 1):
        idx_start = stop_indices[i]
        idx_end = stop_indices[i+1]
        if idx_end > idx_start:
            sub_coords = osrm_coords[idx_start:idx_end + 1]
        else:
            sub_coords = [(stops[i]["lat"], stops[i]["lon"]), (stops[i+1]["lat"], stops[i+1]["lon"])]
        segments.append(sub_coords)
        
    return segments

# Let's test with Route 6A stops
route_6a_stops = [
    {"name": "Simhachalam Temple", "lat": 17.7664, "lon": 83.2505, "mins_to_next": 2},
    {"name": "Simhachalam Junction", "lat": 17.7712, "lon": 83.2721, "mins_to_next": 4},
    {"name": "Gopalapatnam", "lat": 17.7587, "lon": 83.2435, "mins_to_next": 4}
]

print("Fetching OSRM route...")
coords = fetch_whole_osrm_route(route_6a_stops)
if coords:
    print(f"Successfully fetched {len(coords)} coordinates.")
    segments = get_road_aligned_segments(route_6a_stops, coords)
    print(f"Segment 1 count: {len(segments[0])}")
    print(f"Segment 2 count: {len(segments[1])}")
else:
    print("Fetch failed or returned None.")
