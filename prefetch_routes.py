import urllib.request
import json
import time
import os
import sys

# Add current dir to path to import main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import APSRTC_ROUTES

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "osrm_cache.json")

def fetch_route(route_id, stops):
    coords_str = ";".join([f"{stop['lon']},{stop['lat']}" for stop in stops])
    url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TracknTravel/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data.get("code") == "Ok" and data.get("routes"):
                    coords = data["routes"][0]["geometry"]["coordinates"]
                    # Swap [lon, lat] to [lat, lon]
                    return [(c[1], c[0]) for c in coords]
                else:
                    print(f"[{route_id}] OSRM returned non-Ok code: {data.get('code')}")
        except Exception as e:
            print(f"[{route_id}] OSRM attempt {attempt+1} failed: {e}")
            time.sleep(2)
    return None

def main():
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
            print(f"Loaded existing cache with {len(cache)} routes.")
        except Exception as e:
            print(f"Failed to load existing cache: {e}")

    updated = False
    for route_id, route_data in APSRTC_ROUTES.items():
        if route_id in cache and cache[route_id] is not None and len(cache[route_id]) > 0:
            print(f"Route {route_id} already cached with {len(cache[route_id])} coords.")
            continue
        
        print(f"Fetching route {route_id}...")
        coords = fetch_route(route_id, route_data["stops"])
        if coords:
            cache[route_id] = coords
            updated = True
            print(f"Successfully fetched and cached {len(coords)} coordinates for route {route_id}.")
            time.sleep(1) # Be nice to public API
        else:
            print(f"FAILED to fetch route {route_id}.")

    if updated or not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
        print(f"Saved {len(cache)} routes to {CACHE_FILE}.")
    else:
        print("No updates needed. Cache is up to date.")

if __name__ == "__main__":
    main()
