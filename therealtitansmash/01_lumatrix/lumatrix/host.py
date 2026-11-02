import time
import requests
import serial
from datetime import datetime, timezone

COM_PORT = 'COM5' 
BAUD_RATE = 115200

STATIONS = [
    {"name": "ZEHNTEN", "id": "8576262"},
    {"name": "HUNGER", "id": "8576263"}
]

def fetch_departure(station):
    station_id = station["id"]
    try:
        response = requests.get(
            "https://transport.opendata.ch/v1/stationboard",
            params={"id": station_id, "limit": 1},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get('stationboard'):
            return None
        dep = data['stationboard'][0]
        departure = dep.get('stop', {}).get('departure')
        if not departure:
            return None

        dep_time = datetime.strptime(departure, "%Y-%m-%dT%H:%M:%S%z")
        mins_to_go = max(0, int((dep_time - datetime.now(timezone.utc)).total_seconds() / 60))
        line_number = dep.get('number') or dep.get('name') or "?"
        return station["name"], line_number, mins_to_go
    except Exception as e:
        print(f"[HOST] Fetch error for {station['name']} ({station_id}): {e}")
        return None

if __name__ == "__main__":
    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        
        # CRITICAL FIX: Assert DTR/RTS so MicroPython doesn't drop the payload
        ser.dtr = True
        ser.rts = True
        time.sleep(2) # Allow USB stack to stabilize
        
        while True:
            for station in STATIONS:
                departure = fetch_departure(station)
                
                if departure:
                    station_name, line_number, mins = departure
                    payload = f"{station_name},{line_number},{mins}\n"
                    print(f"\n[HOST] Transmitting: {payload.strip()}")
                    ser.write(payload.encode('utf-8'))
                    
                    # --- LISTEN FOR ACK ---
                    # Wait briefly for Pico to process and reply
                    time.sleep(0.5) 
                    while ser.in_waiting > 0:
                        ack = ser.readline().decode('utf-8', errors='ignore').strip()
                        print(f"[EDGE] {ack}")
                
                time.sleep(16) # Wait for display cycle to finish
                
    except serial.SerialException as e:
        print(f"COM Port Error. Details: {e}")
