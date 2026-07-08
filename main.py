import asyncio
import math
import time
import json
import urllib.request
import logging
from datetime import datetime, timezone as pytimezone, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI(title="Track n Travel Authentic APSRTC Transit Backend")

from fastapi.middleware.cors import CORSMiddleware

# Tell FastAPI to trust your Netlify website link
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://trackntravel.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentic APSRTC Visakhapatnam City Routes Database Schema with Travel Times
APSRTC_ROUTES = {
    "10K": {
        "service_name": "10K Metro Express",
        "route_name": "RTC Complex -> Kailasagiri Hill Bottom",
        "stops": [
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 5},
            {"name": "Jagadamba Centre", "lat": 17.7119, "lon": 83.3023, "mins_to_next": 4},
            {"name": "RK Beach", "lat": 17.7182, "lon": 83.3283, "mins_to_next": 3},
            {"name": "VUDA Park", "lat": 17.7248, "lon": 83.3377, "mins_to_next": 10},
            {"name": "Tenneti Park", "lat": 17.7471, "lon": 83.3512, "mins_to_next": 8},
            {"name": "Kailasagiri Hill Bottom", "lat": 17.7667, "lon": 83.3541, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 2,  # RK Beach stop
        "fleet_count": 4
    },
    "28K": {
        "service_name": "28K City Ordinary",
        "route_name": "Kothavalasa -> RK Beach",
        "stops": [
            {"name": "Kothavalasa", "lat": 17.8923, "lon": 83.1592, "mins_to_next": 10},
            {"name": "Pendurthi", "lat": 17.8085, "lon": 83.2012, "mins_to_next": 6},
            {"name": "Vepagunta", "lat": 17.7663, "lon": 83.2201, "mins_to_next": 4},
            {"name": "Gopalapatnam", "lat": 17.7587, "lon": 83.2435, "mins_to_next": 4},
            {"name": "NAD X Road", "lat": 17.7475, "lon": 83.2515, "mins_to_next": 12},
            {"name": "Gurudwara Junction", "lat": 17.7369, "lon": 83.2995, "mins_to_next": 3},
            {"name": "Birla Junction", "lat": 17.7305, "lon": 83.2895, "mins_to_next": 3},
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 5},
            {"name": "Jagadamba Centre", "lat": 17.7119, "lon": 83.3023, "mins_to_next": 4},
            {"name": "RK Beach", "lat": 17.7182, "lon": 83.3283, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 4,  # NAD X Road
        "fleet_count": 10
    },
    "38Y": {
        "service_name": "38Y Metro Express",
        "route_name": "RTC Complex -> Duvvada Railway Station",
        "stops": [
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 4},
            {"name": "Gurudwara Junction", "lat": 17.7369, "lon": 83.2995, "mins_to_next": 3},
            {"name": "Akkayyapalem", "lat": 17.7388, "lon": 83.2882, "mins_to_next": 5},
            {"name": "NAD X Road", "lat": 17.7475, "lon": 83.2515, "mins_to_next": 8},
            {"name": "BHPV", "lat": 17.7112, "lon": 83.2285, "mins_to_next": 6},
            {"name": "Gajuwaka Junction", "lat": 17.6904, "lon": 83.2109, "mins_to_next": 6},
            {"name": "Kurmannapalem", "lat": 17.6754, "lon": 83.1592, "mins_to_next": 8},
            {"name": "Duvvada Railway Station", "lat": 17.6890, "lon": 83.1795, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 3,  # NAD X Road
        "fleet_count": 8
    },
    "25P": {
        "service_name": "25P PM Palem Route",
        "route_name": "PM Palem -> Old Post Office",
        "stops": [
            {"name": "PM Palem (Stadium)", "lat": 17.7981, "lon": 83.3442, "mins_to_next": 5},
            {"name": "Yendada", "lat": 17.7788, "lon": 83.3465, "mins_to_next": 5},
            {"name": "Hanumanthawaka", "lat": 17.7589, "lon": 83.3325, "mins_to_next": 5},
            {"name": "Maddilapalem", "lat": 17.7383, "lon": 83.3218, "mins_to_next": 4},
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 5},
            {"name": "Jagadamba Centre", "lat": 17.7119, "lon": 83.3023, "mins_to_next": 6},
            {"name": "Old Post Office", "lat": 17.6975, "lon": 83.2981, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 4,  # RTC Complex
        "fleet_count": 5
    },
    "900K": {
        "service_name": "900K Bheemili Route",
        "route_name": "Bheemili -> Railway Station",
        "stops": [
            {"name": "Bheemili", "lat": 17.8895, "lon": 83.4475, "mins_to_next": 8},
            {"name": "INS Kalinga", "lat": 17.8423, "lon": 83.4212, "mins_to_next": 10},
            {"name": "GITAM University", "lat": 17.7818, "lon": 83.3795, "mins_to_next": 2},
            {"name": "Rushikonda Beach", "lat": 17.7801, "lon": 83.3854, "mins_to_next": 5},
            {"name": "Sagar Nagar", "lat": 17.7588, "lon": 83.3595, "mins_to_next": 6},
            {"name": "MVP Colony", "lat": 17.7412, "lon": 83.3332, "mins_to_next": 5},
            {"name": "Siripuram Junction", "lat": 17.7222, "lon": 83.3154, "mins_to_next": 4},
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 5},
            {"name": "Railway Station", "lat": 17.7215, "lon": 83.2934, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 2,  # GITAM University
        "fleet_count": 5
    },
    "6A": {
        "service_name": "6A Simhachalam Route",
        "route_name": "Simhachalam Temple -> RTC Complex",
        "stops": [
            {"name": "Simhachalam Temple", "lat": 17.7664, "lon": 83.2505, "mins_to_next": 2},
            {"name": "Simhachalam Junction", "lat": 17.7712, "lon": 83.2721, "mins_to_next": 4},
            {"name": "Gopalapatnam", "lat": 17.7587, "lon": 83.2435, "mins_to_next": 4},
            {"name": "NAD X Road", "lat": 17.7475, "lon": 83.2515, "mins_to_next": 9},
            {"name": "Kancharapalem", "lat": 17.7295, "lon": 83.2754, "mins_to_next": 6},
            {"name": "Railway Station", "lat": 17.7215, "lon": 83.2934, "mins_to_next": 5},
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 3,  # NAD X Road
        "fleet_count": 8
    },
    "25M": {
        "service_name": "25M PM Palem Route",
        "route_name": "Marikavalasa -> Old Post Office",
        "stops": [
            {"name": "Marikavalasa", "lat": 17.8429, "lon": 83.4144, "mins_to_next": 6},
            {"name": "Madhurawada", "lat": 17.8178, "lon": 83.3496, "mins_to_next": 5},
            {"name": "PM Palem (Stadium)", "lat": 17.7981, "lon": 83.3442, "mins_to_next": 4},
            {"name": "Yendada", "lat": 17.7788, "lon": 83.3465, "mins_to_next": 5},
            {"name": "Hanumanthawaka", "lat": 17.7589, "lon": 83.3325, "mins_to_next": 5},
            {"name": "Maddilapalem", "lat": 17.7383, "lon": 83.3218, "mins_to_next": 4},
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 5},
            {"name": "Jagadamba Centre", "lat": 17.7119, "lon": 83.3023, "mins_to_next": 6},
            {"name": "Old Post Office", "lat": 17.6975, "lon": 83.2981, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 5,  # Maddilapalem
        "fleet_count": 8
    },
    "540": {
        "service_name": "540 MVP Colony Route",
        "route_name": "Simhachalam Hub -> MVP Colony",
        "stops": [
            {"name": "Simhachalam Hub", "lat": 17.7664, "lon": 83.2505, "mins_to_next": 3},
            {"name": "Vepagunta", "lat": 17.7663, "lon": 83.2201, "mins_to_next": 5},
            {"name": "Gopalapatnam", "lat": 17.7587, "lon": 83.2435, "mins_to_next": 4},
            {"name": "NAD X Road", "lat": 17.7475, "lon": 83.2515, "mins_to_next": 12},
            {"name": "Gurudwara Junction", "lat": 17.7369, "lon": 83.2995, "mins_to_next": 6},
            {"name": "Maddilapalem Junction", "lat": 17.7383, "lon": 83.3218, "mins_to_next": 5},
            {"name": "MVP Colony", "lat": 17.7412, "lon": 83.3332, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 3,  # NAD X Road
        "fleet_count": 10
    },
    "222V": {
        "service_name": "222V Metro Express",
        "route_name": "RTC Complex -> Vizianagaram",
        "stops": [
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 4},
            {"name": "Gurudwara Junction", "lat": 17.7369, "lon": 83.2995, "mins_to_next": 4},
            {"name": "Maddilapalem", "lat": 17.7383, "lon": 83.3218, "mins_to_next": 3},
            {"name": "Venkojipalem", "lat": 17.7508, "lon": 83.3289, "mins_to_next": 5},
            {"name": "Yendada", "lat": 17.7788, "lon": 83.3465, "mins_to_next": 6},
            {"name": "Madhurawada", "lat": 17.8178, "lon": 83.3496, "mins_to_next": 6},
            {"name": "Marikavalasa", "lat": 17.8429, "lon": 83.4144, "mins_to_next": 4},
            {"name": "Pyda College", "lat": 17.8592, "lon": 83.4285, "mins_to_next": 6},
            {"name": "Anandapuram", "lat": 17.8623, "lon": 83.4150, "mins_to_next": 6},
            {"name": "Rajula Tallavalasa", "lat": 17.8921, "lon": 83.4142, "mins_to_next": 8},
            {"name": "Tagarapuvalasa", "lat": 17.9298, "lon": 83.4289, "mins_to_next": 6},
            {"name": "Modhavalasa", "lat": 17.9622, "lon": 83.4312, "mins_to_next": 5},
            {"name": "Raghu College/Dakamarri", "lat": 17.9902, "lon": 83.4322, "mins_to_next": 7},
            {"name": "Jonnada", "lat": 18.0289, "lon": 83.4201, "mins_to_next": 7},
            {"name": "AP Battalion", "lat": 18.0690, "lon": 83.4152, "mins_to_next": 6},
            {"name": "Aruna Jute Mill", "lat": 18.0988, "lon": 83.4101, "mins_to_next": 8},
            {"name": "Vizianagaram", "lat": 18.1119, "lon": 83.3985, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 8,  # Anandapuram
        "fleet_count": 12
    },
    "111V": {
        "service_name": "111V City Ordinary",
        "route_name": "Kurmannapalem -> Vizianagaram",
        "stops": [
            {"name": "Kurmannapalem", "lat": 17.6754, "lon": 83.1592, "mins_to_next": 6},
            {"name": "Gajuwaka", "lat": 17.6904, "lon": 83.2109, "mins_to_next": 14},
            {"name": "NAD X Road", "lat": 17.7475, "lon": 83.2515, "mins_to_next": 12},
            {"name": "Gurudwara Junction", "lat": 17.7369, "lon": 83.2995, "mins_to_next": 4},
            {"name": "Maddilapalem", "lat": 17.7383, "lon": 83.3218, "mins_to_next": 5},
            {"name": "Hanumanthawaka", "lat": 17.7589, "lon": 83.3325, "mins_to_next": 6},
            {"name": "Arilova/Zoo Park", "lat": 17.7712, "lon": 83.3292, "mins_to_next": 10},
            {"name": "Madhurawada", "lat": 17.8178, "lon": 83.3496, "mins_to_next": 15},
            {"name": "Tagarapuvalasa", "lat": 17.9298, "lon": 83.4289, "mins_to_next": 20},
            {"name": "Vizianagaram", "lat": 18.1119, "lon": 83.3985, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 1,  # Gajuwaka
        "fleet_count": 10
    },
    "211V": {
        "service_name": "211V Metro Express",
        "route_name": "Vizianagaram -> Railway Station",
        "stops": [
            {"name": "Vizianagaram", "lat": 18.1119, "lon": 83.3985, "mins_to_next": 20},
            {"name": "Tagarapuvalasa", "lat": 17.9298, "lon": 83.4289, "mins_to_next": 15},
            {"name": "Kommadi", "lat": 17.8285, "lon": 83.3592, "mins_to_next": 5},
            {"name": "Car Shed Junction", "lat": 17.8015, "lon": 83.3482, "mins_to_next": 4},
            {"name": "Madhurawada", "lat": 17.8178, "lon": 83.3496, "mins_to_next": 6},
            {"name": "Yendada", "lat": 17.7788, "lon": 83.3465, "mins_to_next": 5},
            {"name": "Hanumanthawaka", "lat": 17.7589, "lon": 83.3325, "mins_to_next": 5},
            {"name": "Maddilapalem", "lat": 17.7383, "lon": 83.3218, "mins_to_next": 4},
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 5},
            {"name": "Railway Station", "lat": 17.7215, "lon": 83.2934, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 4,  # Madhurawada
        "fleet_count": 12
    },
    "48A": {
        "service_name": "48A Akkayyapalem Route",
        "route_name": "Madhavadhara -> Old Post Office",
        "stops": [
            {"name": "Madhavadhara", "lat": 17.7512, "lon": 83.2721, "mins_to_next": 3},
            {"name": "Muralinagar", "lat": 17.7543, "lon": 83.2688, "mins_to_next": 4},
            {"name": "Kailasapuram", "lat": 17.7465, "lon": 83.2789, "mins_to_next": 4},
            {"name": "Akkayyapalem", "lat": 17.7388, "lon": 83.2882, "mins_to_next": 5},
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 5},
            {"name": "Jagadamba Centre", "lat": 17.7119, "lon": 83.3023, "mins_to_next": 3},
            {"name": "Poorna Market", "lat": 17.7025, "lon": 83.2995, "mins_to_next": 4},
            {"name": "Old Post Office", "lat": 17.6975, "lon": 83.2981, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 3,  # Akkayyapalem
        "fleet_count": 3
    },
    "60C": {
        "service_name": "60C Arilova Route",
        "route_name": "Arilova Colony -> Old Post Office",
        "stops": [
            {"name": "Arilova Colony", "lat": 17.7712, "lon": 83.3292, "mins_to_next": 5},
            {"name": "Hanumanthawaka", "lat": 17.7589, "lon": 83.3325, "mins_to_next": 5},
            {"name": "Maddilapalem", "lat": 17.7383, "lon": 83.3218, "mins_to_next": 4},
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 5},
            {"name": "Jagadamba Centre", "lat": 17.7119, "lon": 83.3023, "mins_to_next": 4},
            {"name": "Town Kotha Road", "lat": 17.6995, "lon": 83.2989, "mins_to_next": 3},
            {"name": "Old Post Office", "lat": 17.6975, "lon": 83.2981, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 3,  # RTC Complex
        "fleet_count": 5
    },
    "52D": {
        "service_name": "52D Ravindra Nagar Route",
        "route_name": "Ravindra Nagar -> Old Post Office",
        "stops": [
            {"name": "Ravindra Nagar", "lat": 17.7654, "lon": 83.3289, "mins_to_next": 3},
            {"name": "Adarsha Nagar", "lat": 17.7523, "lon": 83.3254, "mins_to_next": 4},
            {"name": "Maddilapalem", "lat": 17.7383, "lon": 83.3218, "mins_to_next": 4},
            {"name": "Dwaraka Bus Station (RTC Complex)", "lat": 17.7285, "lon": 83.3071, "mins_to_next": 5},
            {"name": "Jagadamba Centre", "lat": 17.7119, "lon": 83.3023, "mins_to_next": 4},
            {"name": "Town Kotha Road", "lat": 17.6995, "lon": 83.2989, "mins_to_next": 3},
            {"name": "Old Post Office", "lat": 17.6975, "lon": 83.2981, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 2,  # Maddilapalem
        "fleet_count": 4
    },
    "14": {
        "service_name": "14 MVP Colony Route",
        "route_name": "Venkojipalem -> Old Post Office",
        "stops": [
            {"name": "Venkojipalem", "lat": 17.7508, "lon": 83.3289, "mins_to_next": 3},
            {"name": "MVP Colony", "lat": 17.7412, "lon": 83.3332, "mins_to_next": 5},
            {"name": "Chinna Waltair", "lat": 17.7215, "lon": 83.3323, "mins_to_next": 3},
            {"name": "AU Out-Gate", "lat": 17.7233, "lon": 83.3289, "mins_to_next": 3},
            {"name": "Siripuram Junction", "lat": 17.7222, "lon": 83.3154, "mins_to_next": 5},
            {"name": "Jagadamba Centre", "lat": 17.7119, "lon": 83.3023, "mins_to_next": 5},
            {"name": "Old Post Office", "lat": 17.6975, "lon": 83.2981, "mins_to_next": 0}
        ],
        "stall_trigger_stop_idx": 4,  # Siripuram Junction
        "fleet_count": 3
    }
}

STEPS_PER_MINUTE = 30  # Real-Time Pacing: 1 step represents 2 seconds
SIMULATION_SPEED_MULTIPLIER = 1.0
FORCE_ACTIVE_SIMULATION = False

ROUTE_TIMETABLES = {
    "10K": ("06:00", "23:00"),
    "900K": ("05:30", "21:30"),
    "28K": ("05:00", "23:00"),
    "6A": ("06:00", "22:00"),
    "540": ("06:00", "21:45"),
    "38Y": ("05:00", "22:30"),
    "25M": ("06:00", "22:00"),
    "25P": ("06:30", "22:00"),
    "48A": ("06:00", "21:30"),
    "222V": {
        "route_code": "222V",
        "name": "222V Metro Express",
        "start_time": "05:00 AM",
        "end_time": "09:30 PM",
        "depot": "Maddilapalem Depot"
    },
    "111V": ("05:00", "23:00"),
    "211V": ("05:00", "22:00"),
    "60C": ("05:30", "22:00"),
    "52D": ("06:00", "21:15"),
    "14": ("06:00", "21:30")
}

HOME_DEPOTS = {
    "10K": {"name": "Waltair Depot", "lat": 17.7300, "lon": 83.3300},
    "60C": {"name": "Waltair Depot", "lat": 17.7300, "lon": 83.3300},
    "14": {"name": "Waltair Depot", "lat": 17.7300, "lon": 83.3300},
    "25M": {"name": "Maddilapalem Depot", "lat": 17.7383, "lon": 83.3218},
    "25P": {"name": "Maddilapalem Depot", "lat": 17.7383, "lon": 83.3218},
    "222V": {"name": "Maddilapalem Depot", "lat": 17.7383, "lon": 83.3218},
    "211V": {"name": "Maddilapalem Depot", "lat": 17.7383, "lon": 83.3218},
    "28K": {"name": "Simhachalam Depot", "lat": 17.7664, "lon": 83.2505},
    "6A": {"name": "Simhachalam Depot", "lat": 17.7664, "lon": 83.2505},
    "540": {"name": "Simhachalam Depot", "lat": 17.7664, "lon": 83.2505},
    "48A": {"name": "Simhachalam Depot", "lat": 17.7664, "lon": 83.2505},
    "38Y": {"name": "Gajuwaka Depot", "lat": 17.6904, "lon": 83.2109},
    "111V": {"name": "Visakha Steel City Depot", "lat": 17.6754, "lon": 83.1592},
    "900K": {"name": "Madhurawada Depot", "lat": 17.8178, "lon": 83.3496},
    "52D": {"name": "Madhurawada Depot", "lat": 17.8178, "lon": 83.3496}
}

def is_past_operating_hours(route_id):
    import re
    # Clean incoming route ID by stripping trailing regional suffixes (like 'V' or 'New')
    clean_id = re.sub(r'[A-Za-z\s]+$', '', route_id)
    
    # Try exact match first
    timetable = None
    if route_id in ROUTE_TIMETABLES:
        timetable = ROUTE_TIMETABLES[route_id]
    elif clean_id in ROUTE_TIMETABLES:
        timetable = ROUTE_TIMETABLES[clean_id]
    else:
        # Fallback to key cleaning comparison
        for k, v in ROUTE_TIMETABLES.items():
            k_clean = re.sub(r'[A-Za-z\s]+$', '', k)
            if k_clean == clean_id:
                timetable = v
                break
                
    if not timetable:
        timetable = ("06:00", "22:00")
        
    if isinstance(timetable, dict):
        start_str = timetable.get("start_time", "06:00 AM")
        end_str = timetable.get("end_time", "10:00 PM")
        try:
            start_dt = datetime.strptime(start_str, "%I:%M %p")
            end_dt = datetime.strptime(end_str, "%I:%M %p")
            start_h, start_m = start_dt.hour, start_dt.minute
            end_h, end_m = end_dt.hour, end_dt.minute
        except Exception:
            start_h, start_m = 6, 0
            end_h, end_m = 22, 0
    else:
        start_str, end_str = timetable
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
        
    current_dt = get_ist_time()
    current_mins = current_dt.hour * 60 + current_dt.minute
    start_mins = start_h * 60 + start_m
    end_mins = end_h * 60 + end_m
    
    return not (start_mins <= current_mins < end_mins)

def is_route_active(route_id, current_dt):
    if FORCE_ACTIVE_SIMULATION:
        return True
    return not is_past_operating_hours(route_id)

def get_ist_time():
    ist_tz = pytimezone(timedelta(hours=5, minutes=30))
    return datetime.now(pytimezone.utc).astimezone(ist_tz)

def get_ist_time_str():
    return get_ist_time().strftime("%I:%M:%S %p IST")

def haversine_distance(p1, p2):
    R = 6371.0  # Earth's radius in kilometers
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

OSRM_ROUTE_CACHE = {}

import os
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "osrm_cache.json")
try:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            OSRM_ROUTE_CACHE = json.load(f)
            logging.info(f"Loaded {len(OSRM_ROUTE_CACHE)} routes from persistent OSRM cache.")
except Exception as e:
    logging.warning(f"Failed to load OSRM cache from file: {e}")

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
        logging.warning(f"OSRM fetch failed for stops route: {e}")
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

def interpolate_path(coords, num_steps):
    if len(coords) < 2:
        return [coords[0]] * num_steps if coords else []
        
    dists = [0.0]
    for i in range(len(coords) - 1):
        dists.append(dists[-1] + haversine_distance(coords[i], coords[i+1]))
        
    total_dist = dists[-1]
    if total_dist == 0.0:
        return [coords[0]] * num_steps
        
    segment_coords = []
    for j in range(num_steps):
        t = j / num_steps
        target_dist = t * total_dist
        idx = 0
        while idx < len(dists) - 1 and dists[idx+1] < target_dist:
            idx += 1
        if dists[idx+1] == dists[idx]:
            segment_coords.append(coords[idx])
        else:
            ratio = (target_dist - dists[idx]) / (dists[idx+1] - dists[idx])
            lat = coords[idx][0] + (coords[idx+1][0] - coords[idx][0]) * ratio
            lon = coords[idx][1] + (coords[idx+1][1] - coords[idx][1]) * ratio
            segment_coords.append((lat, lon))
    return segment_coords

def get_remaining_distance(current_idx, current_pos, route, direction="FORWARD"):
    if direction == "FORWARD":
        if current_idx >= len(route) - 1:
            return 0.0
        dist = haversine_distance(current_pos, route[current_idx + 1])
        for i in range(current_idx + 1, len(route) - 1):
            dist += haversine_distance(route[i], route[i + 1])
        return dist
    else:
        if current_idx <= 0:
            return 0.0
        dist = haversine_distance(current_pos, route[current_idx - 1])
        for i in range(current_idx - 1, 0, -1):
            dist += haversine_distance(route[i], route[i - 1])
        return dist

def calculate_eta(remaining_dist_km, speed_kmh=40.0):
    if remaining_dist_km <= 0:
        return "Arrived"
    hours = remaining_dist_km / speed_kmh
    total_seconds = int(hours * 3600)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    if minutes > 0:
        return f"{minutes} min {seconds} sec"
    return f"{seconds} sec"

class VehicleSimulator:
    def __init__(self, bus_id, route_data, instance_idx=0, fleet_count=1):
        self.bus_id = bus_id
        self.name = route_data["service_name"]
        self.route_name = route_data["route_name"]
        self.stops_raw = route_data["stops"]
        self.stall_trigger_stop_idx = route_data["stall_trigger_stop_idx"]
        
        # Calculate dynamic route indices for each stop in the database
        self.stops = []
        cumulative_idx = 0
        for stop in self.stops_raw:
            stop_copy = stop.copy()
            stop_copy["route_index"] = cumulative_idx
            self.stops.append(stop_copy)
            cumulative_idx += stop["mins_to_next"] * STEPS_PER_MINUTE
            
        self.stall_trigger_idx = self.stops[self.stall_trigger_stop_idx]["route_index"]
        # Build coordinates route
        self.route = self._interpolate_route()
        
        # Stagger start direction and index
        self.direction = "FORWARD" if (instance_idx % 2 == 0) else "REVERSE"
        total_steps = len(self.route)
        spacing = total_steps / fleet_count
        self.current_idx = int(instance_idx * spacing)
        self.current_idx = min(self.current_idx, total_steps - 1)
        self.current_pos = self.route[self.current_idx]
        self.last_moved_time = time.time()
        
        self.stalled = False
        self.speed = 35.0
        self.alert_active = False
        self.alert_message = ""
        self.is_stalling = False
        self.stall_duration_ticks = 0
        self.max_stall_ticks = 4
        self.standby_ticks = 0
        self.active = True
        self.force_active = False

    def _interpolate_route(self):
        route_id = self.bus_id.split("-")[0]
        if route_id not in OSRM_ROUTE_CACHE or OSRM_ROUTE_CACHE[route_id] is None:
            # Fetch from OSRM
            osrm_coords = fetch_whole_osrm_route(self.stops)
            if osrm_coords:
                OSRM_ROUTE_CACHE[route_id] = osrm_coords
                try:
                    with open(CACHE_FILE, "w") as f:
                        json.dump(OSRM_ROUTE_CACHE, f, indent=2)
                except Exception as e:
                    logging.warning(f"Failed to write to OSRM cache file: {e}")
            else:
                OSRM_ROUTE_CACHE[route_id] = None
        
        osrm_coords = OSRM_ROUTE_CACHE[route_id]
        
        route_coords = []
        if osrm_coords:
            # We have OSRM coordinates! Segment and interpolate along the road.
            segments = get_road_aligned_segments(self.stops, osrm_coords)
            for i in range(len(self.stops) - 1):
                segment_steps = self.stops[i]["mins_to_next"] * STEPS_PER_MINUTE
                sub_coords = segments[i]
                segment_coords = interpolate_path(sub_coords, segment_steps)
                route_coords.extend(segment_coords)
        else:
            # Fallback to straight-line interpolation
            for i in range(len(self.stops) - 1):
                start = (self.stops[i]["lat"], self.stops[i]["lon"])
                end = (self.stops[i+1]["lat"], self.stops[i+1]["lon"])
                segment_steps = self.stops[i]["mins_to_next"] * STEPS_PER_MINUTE
                for j in range(segment_steps):
                    t = j / segment_steps
                    lat = start[0] + (end[0] - start[0]) * t
                    lon = start[1] + (end[1] - start[1]) * t
                    route_coords.append((lat, lon))
                    
        route_coords.append((self.stops[-1]["lat"], self.stops[-1]["lon"]))
        return route_coords

    def get_current_base_speed(self):
        if self.stalled:
            return 0.0
        for i in range(len(self.stops) - 1):
            if self.stops[i]["route_index"] <= self.current_idx < self.stops[i+1]["route_index"]:
                stop_name = self.stops[i]["name"]
                if "NAD Junction" in stop_name or "Jagadamba" in stop_name or "Gurudwara" in stop_name:
                    return round(18.0 + (self.current_idx % 7), 1)
                else:
                    return round(32.0 + (self.current_idx % 9), 1)
        return 35.0

    def update(self):
        now = time.time()
        ist_dt = get_ist_time()
        route_id = self.bus_id.split("-")[0]
        
        # Target vehicle 222V-01 specifically by operational hours
        if self.bus_id == "222V-01" and not FORCE_ACTIVE_SIMULATION:
            if is_past_operating_hours("222V"):
                self.current_pos = (17.7284, 83.3150)
                self.speed = 0.0
                self.stalled = False
                self.alert_active = False
                self.alert_message = ""
                self.is_stalling = False
                self.standby_ticks = 0
                self.active = False
                return
                
        is_active = self.force_active or is_route_active(route_id, ist_dt)
        
        if not is_active:
            if route_id == "222V":
                self.current_pos = (17.7284, 83.3150)
            else:
                depot = HOME_DEPOTS.get(route_id, {"lat": 17.7300, "lon": 83.3300})
                self.current_pos = (depot["lat"], depot["lon"])
            self.speed = 0.0
            self.stalled = False
            self.alert_active = False
            self.alert_message = ""
            self.is_stalling = False
            self.standby_ticks = 0
            self.active = False
            return
            
        if not self.active:
            self.active = True
            self.current_pos = self.route[self.current_idx]
            self.last_moved_time = now
            
        if self.standby_ticks > 0:
            self.standby_ticks -= 1
            self.speed = 0.0
            return
            
        # Check boundary & toggle direction
        if self.direction == "FORWARD":
            if self.current_idx >= len(self.route) - 1:
                terminal_name = self.stops[-1]["name"].lower()
                is_standby_terminal = any(x in terminal_name for x in ["dwaraka", "rtc complex", "maddilapalem"])
                if is_standby_terminal:
                    self.standby_ticks = 4
                    self.speed = 0.0
                    self.direction = "REVERSE"
                    self.current_idx = len(self.route) - 1
                    self.current_pos = self.route[self.current_idx]
                    self.last_moved_time = now
                    return
                else:
                    self.direction = "REVERSE"
                    self.current_idx = len(self.route) - 1
                    self.current_pos = self.route[self.current_idx]
                    self.last_moved_time = now
                    self.stalled = False
                    self.alert_active = False
                    self.alert_message = ""
                    self.is_stalling = False
                    self.stall_duration_ticks = 0
                    self.speed = self.get_current_base_speed()
                    return
        else:
            if self.current_idx <= 0:
                terminal_name = self.stops[0]["name"].lower()
                is_standby_terminal = any(x in terminal_name for x in ["dwaraka", "rtc complex", "maddilapalem"])
                if is_standby_terminal:
                    self.standby_ticks = 4
                    self.speed = 0.0
                    self.direction = "FORWARD"
                    self.current_idx = 0
                    self.current_pos = self.route[self.current_idx]
                    self.last_moved_time = now
                    return
                else:
                    self.direction = "FORWARD"
                    self.current_idx = 0
                    self.current_pos = self.route[self.current_idx]
                    self.last_moved_time = now
                    self.stalled = False
                    self.alert_active = False
                    self.alert_message = ""
                    self.is_stalling = False
                    self.stall_duration_ticks = 0
                    self.speed = self.get_current_base_speed()
                    return

        # Handle traffic stall triggers
        if self.current_idx == self.stall_trigger_idx:
            if not self.is_stalling:
                self.is_stalling = True
                self.stall_duration_ticks = 0
                self.last_moved_time = now

            if self.stall_duration_ticks < self.max_stall_ticks:
                self.stall_duration_ticks += 1
                elapsed = (now - self.last_moved_time) * SIMULATION_SPEED_MULTIPLIER
                if elapsed > 6.0:
                    self.stalled = True
                    self.alert_active = True
                    alert_time_str = get_ist_time().strftime("%I:%M %p")
                    self.alert_message = f"[{alert_time_str} IST] Delay Alert: {self.name} stalled on route due to heavy traffic!"
                    self.speed = 0.0
                return
            else:
                self.is_stalling = False
                self.stalled = False
                self.alert_active = False
                self.alert_message = ""
                self.speed = self.get_current_base_speed()
                
                # Advance step according to direction
                if self.direction == "FORWARD":
                    self.current_idx += 1
                else:
                    self.current_idx -= 1
                    
                self.current_pos = self.route[self.current_idx]
                self.last_moved_time = now
        else:
            if self.direction == "FORWARD":
                self.current_idx += 1
            else:
                self.current_idx -= 1
                
            self.current_pos = self.route[self.current_idx]
            self.last_moved_time = now
            self.stalled = False
            self.alert_active = False
            self.alert_message = ""
            self.speed = self.get_current_base_speed()


    def get_payload(self):
        route_id = self.bus_id.split("-")[0]
        
        remaining_dist = get_remaining_distance(self.current_idx, self.current_pos, self.route, self.direction)
        speed_for_eta = self.speed if self.speed > 0 else 15.0
        eta_str = calculate_eta(remaining_dist, speed_for_eta)
        
        bus = {
            "bus_id": self.bus_id,
            "route_code": route_id,
            "name": self.name,
            "status": "Delayed" if self.stalled else "On Time",
            "lat": self.current_pos[0],
            "lon": self.current_pos[1],
            "latitude": self.current_pos[0],
            "longitude": self.current_pos[1],
            "route_index": self.current_idx,
            "speed": self.speed,
            "speed_kmh": self.speed,
            "remaining_dist_km": round(remaining_dist, 2),
            "eta": eta_str,
            "alert_active": self.alert_active,
            "alert_message": self.alert_message,
            "stops": self.stops,
            "route_name": self.route_name,
            "stall_trigger_idx": self.stall_trigger_idx,
            "last_updated_ist": get_ist_time_str(),
            "direction": self.direction,
            "is_standby": self.standby_ticks > 0,
            "active": True
        }
        
        if not self.force_active:
            if is_past_operating_hours(bus['route_code']):
                bus['active'] = False
                bus['speed'] = 0
                bus['speed_kmh'] = 0.0
                bus['status'] = "Off-Duty"
                
                # Snap its coordinates directly to Maddilapalem Depot if route is 222V
                if bus['route_code'] == "222V":
                    bus['latitude'] = 17.7284
                    bus['longitude'] = 83.3150
                    bus['lat'] = 17.7284
                    bus['lon'] = 83.3150
                    bus['start_time'] = "05:00 AM"
                    bus['end_time'] = "09:30 PM"
                    bus['home_depot'] = "Maddilapalem Depot"
                    bus['current_stop_index'] = 0
                else:
                    depot = HOME_DEPOTS.get(route_id, {"lat": 17.7300, "lon": 83.3300})
                    bus['latitude'] = depot['lat']
                    bus['longitude'] = depot['lon']
                    bus['lat'] = depot['lat']
                    bus['lon'] = depot['lon']
                    bus['status'] = "[Out of Service - Depot Return]"
                
                bus['remaining_dist_km'] = 0.0
                bus['eta'] = "Out of Service"
                bus['alert_active'] = False
                bus['alert_message'] = ""
                bus['is_standby'] = False
                
        if self.bus_id == "222V-01" and not FORCE_ACTIVE_SIMULATION:
            if is_past_operating_hours("222V"):
                bus['active'] = False
                bus['speed'] = 0
                bus['speed_kmh'] = 0.0
                bus['status'] = "Off-Duty"
                bus['latitude'] = 17.7284
                bus['longitude'] = 83.3150
                bus['lat'] = 17.7284
                bus['lon'] = 83.3150
                bus['start_time'] = "05:00 AM"
                bus['end_time'] = "09:30 PM"
                bus['home_depot'] = "Maddilapalem Depot"
                bus['current_stop_index'] = 0
                bus['remaining_dist_km'] = 0.0
                bus['eta'] = "Out of Service"
                bus['alert_active'] = False
                bus['alert_message'] = ""
                bus['is_standby'] = False
                
        return bus


# Instantiate APSRTC simulators procedurally
SIMULATORS = {}
for route_id, route_data in APSRTC_ROUTES.items():
    fleet_count = route_data.get("fleet_count", 1)
    for i in range(fleet_count):
        bus_id = f"{route_id}-{i+1:02d}"
        SIMULATORS[bus_id] = VehicleSimulator(bus_id, route_data, instance_idx=i, fleet_count=fleet_count)

ACTIVE_CONNECTIONS = set()

def get_global_payload(type_str="telemetry_update"):
    vehicles = []
    seen_ids = set()
    is_222V_inactive = is_past_operating_hours("222V")
    
    for sim in SIMULATORS.values():
        payload = sim.get_payload()
        bus_id = payload.get("bus_id")
        if bus_id in seen_ids:
            continue
            
        # Target vehicle 222V-01 specifically by operational hours override
        if bus_id == "222V-01" and not FORCE_ACTIVE_SIMULATION:
            if is_222V_inactive:
                payload['active'] = False
                payload['speed'] = 0
                payload['speed_kmh'] = 0.0
                payload['status'] = "Off-Duty"
                payload['latitude'] = 17.7284
                payload['longitude'] = 83.3150
                payload['lat'] = 17.7284
                payload['lon'] = 83.3150
                payload['start_time'] = "05:00 AM"
                payload['end_time'] = "09:30 PM"
                payload['home_depot'] = "Maddilapalem Depot"
                payload['current_stop_index'] = 0
            
        # Only override to inactive if the simulator is not forced active for testing
        is_forced = sim.force_active or FORCE_ACTIVE_SIMULATION
        if is_222V_inactive and payload.get("route_code") == "222V" and not is_forced:
            payload['active'] = False
            payload['speed'] = 0
            payload['speed_kmh'] = 0.0
            payload['status'] = "Off-Duty"
            payload['latitude'] = 17.7284
            payload['longitude'] = 83.3150
            payload['lat'] = 17.7284
            payload['lon'] = 83.3150
            payload['start_time'] = "05:00 AM"
            payload['end_time'] = "09:30 PM"
            payload['home_depot'] = "Maddilapalem Depot"
            payload['current_stop_index'] = 0
            
        seen_ids.add(bus_id)
        vehicles.append(payload)
        
    return {
        "type": type_str,
        "vehicles": vehicles,
        "speed_multiplier": SIMULATION_SPEED_MULTIPLIER,
        "force_active_simulation": FORCE_ACTIVE_SIMULATION
    }

async def broadcast_state():
    if not ACTIVE_CONNECTIONS:
        return
    payload = get_global_payload()
    message = json.dumps(payload)
    
    disconnected = set()
    for websocket in ACTIVE_CONNECTIONS:
        try:
            await websocket.send_text(message)
        except Exception:
            disconnected.add(websocket)
            
    for ws in disconnected:
        ACTIVE_CONNECTIONS.remove(ws)

async def simulation_loop():
    global SIMULATION_SPEED_MULTIPLIER
    while True:
        sleep_time = 2.0 / SIMULATION_SPEED_MULTIPLIER
        await asyncio.sleep(sleep_time)
        for sim in SIMULATORS.values():
            sim.update()
        await broadcast_state()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulation_loop())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global SIMULATION_SPEED_MULTIPLIER, FORCE_ACTIVE_SIMULATION
    await websocket.accept()
    ACTIVE_CONNECTIONS.add(websocket)
    try:
        # Send initial route coordinates mapping on client connection
        routes_data = {}
        for bus_id, sim in SIMULATORS.items():
            route_code = bus_id.split("-")[0]
            if route_code not in routes_data:
                # Use high-fidelity cached OSRM coordinates if available, otherwise fallback to sim.route
                high_fid = OSRM_ROUTE_CACHE.get(route_code)
                routes_data[route_code] = high_fid if high_fid else sim.route
        
        init_payload = get_global_payload("init")
        init_payload["routes"] = routes_data
        await websocket.send_json(init_payload)
        
        while True:
            message_text = await websocket.receive_text()
            try:
                data = json.loads(message_text)
                if data.get("type") == "set_speed":
                    SIMULATION_SPEED_MULTIPLIER = float(data.get("multiplier", 1.0))
                    await broadcast_state()
                elif data.get("type") == "set_index":
                    bus_id = data.get("bus_id")
                    target_idx = int(data.get("index"))
                    if bus_id in SIMULATORS:
                        sim = SIMULATORS[bus_id]
                        sim.current_idx = min(target_idx, len(sim.route) - 1)
                        sim.current_pos = sim.route[sim.current_idx]
                        sim.last_moved_time = time.time()
                        sim.direction = "FORWARD"
                        sim.force_active = True  # Bypass timetable for testing this bus
                        await broadcast_state()
                elif data.get("type") == "toggle_force_active":
                    FORCE_ACTIVE_SIMULATION = bool(data.get("value", False))
                    # Reset all force_active overrides on simulators when timetables are re-enabled
                    if not FORCE_ACTIVE_SIMULATION:
                        for sim in SIMULATORS.values():
                            sim.force_active = False
                    await broadcast_state()
            except Exception:
                pass
    except WebSocketDisconnect:
        if websocket in ACTIVE_CONNECTIONS:
            ACTIVE_CONNECTIONS.remove(websocket)
    except Exception:
        if websocket in ACTIVE_CONNECTIONS:
            ACTIVE_CONNECTIONS.remove(websocket)

#app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_index():
    return {"status": "backend is running", "message": "Transit stream active"}
