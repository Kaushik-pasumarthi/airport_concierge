"""
VIP Journey Auto-Simulation Script
===================================
Simulates the full VIP airport journey by firing events automatically.
Run this while server.py is running to demo the system hands-free.
"""

import requests
import time
import sys

API_URL = "http://127.0.0.1:8000/event"

# Full VIP journey event sequence (logical order)
JOURNEY_EVENTS = [
    ("RESET", "Resetting system to initial state..."),
    ("VIP_ENTERED_TERMINAL", "VIP has arrived at the terminal"),
    ("FACE_VERIFIED", "Biometric verification complete"),
    ("FLIGHT_DELAYED", "Flight delay announced (+30 min)"),
    ("FLIGHT_DELAYED", "Another delay! Risk escalating..."),
    ("BOARDING_STARTED", "Boarding call - VIP moving to gate"),
    ("VIP_ARRIVED_AT_GATE", "VIP reached boarding gate"),
    ("FLIGHT_LANDED", "Flight landed at transit hub"),
    ("BAGGAGE_TRANSFERRED", "Baggage transferred to next leg"),
    ("FLIGHT_LANDED", "Final destination reached"),
    ("BAGGAGE_CLAIMED", "Baggage collected"),
    ("VIP_EXITED_TERMINAL", "VIP exiting - driver dispatched"),
]

def print_header():
    print("\n" + "=" * 60)
    print("  VIP JOURNEY AUTO-SIMULATION")
    print("  Simulating complete airport journey sequence")
    print("=" * 60 + "\n")

def print_event(index, total, event, description):
    progress = f"[{index}/{total}]"
    print(f"\033[96m{progress}\033[0m \033[93m→\033[0m Injecting: \033[92m{event}\033[0m")
    print(f"       \033[90m{description}\033[0m")

def inject_event(event):
    try:
        response = requests.post(
            API_URL,
            json={"event": event},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            state = data.get("context", {}).get("overall_state", "UNKNOWN")
            risk = data.get("context", {}).get("connection_risk_score", 0)
            print(f"       \033[90m└─ State: {state} | Risk: {risk}%\033[0m\n")
            return True
        else:
            print(f"       \033[91m└─ ERROR: HTTP {response.status_code}\033[0m\n")
            return False
    except requests.exceptions.ConnectionError:
        print(f"       \033[91m└─ ERROR: Cannot connect to server at {API_URL}\033[0m")
        print(f"       \033[91m   Make sure server.py is running!\033[0m\n")
        return False
    except Exception as e:
        print(f"       \033[91m└─ ERROR: {str(e)}\033[0m\n")
        return False

def run_simulation(delay=4):
    print_header()
    print(f"Starting simulation with {delay}s delay between events...\n")
    time.sleep(2)
    
    total = len(JOURNEY_EVENTS)
    for i, (event, description) in enumerate(JOURNEY_EVENTS, 1):
        print_event(i, total, event, description)
        
        if not inject_event(event):
            print("\033[91mSimulation aborted due to error.\033[0m")
            sys.exit(1)
        
        if i < total:
            time.sleep(delay)
    
    print("=" * 60)
    print("  \033[92mSIMULATION COMPLETE\033[0m")
    print("  VIP journey finished successfully!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    # Optional: custom delay from command line
    delay = 4
    if len(sys.argv) > 1:
        try:
            delay = float(sys.argv[1])
        except ValueError:
            print(f"Invalid delay: {sys.argv[1]}. Using default 4 seconds.")
    
    run_simulation(delay)
