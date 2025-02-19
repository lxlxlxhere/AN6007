# v1
import time
import random
import json
import os
import requests
from datetime import datetime

USER_DATA_FILE = "users.json"
METERS_FOLDER = "meter_data"
USER_API_URL = "http://127.0.0.1:5000/meter_ids"

# load user info

def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Read or create meter reading TXT

def load_total_kwh(meter_file):

    try:
        with open(meter_file, "r") as f:
            return float(f.read().strip())
    except:
        return 0.0


# Overwrite meter readings

def save_total_kwh(meter_file, kwh):

    with open(meter_file, "w") as f:
        f.write(f"{kwh:.8f}")


# Randomly generate power consumption

def get_next_usage():

    return round(random.uniform(0.1, 1.0), 8)

def load_meter_ids():
    response = requests.get(USER_API_URL)
    meter_ids = response.json()
    return meter_ids

def check_meter_id():
    meter_ids = load_meter_ids()
    users = load_users()
    meters = {u: os.path.join(METERS_FOLDER, f"meter_{data['meter_id']}.txt") for u, data in users.items()}
    
    if not os.path.exists(METERS_FOLDER):
        os.makedirs(METERS_FOLDER)
    
    for meter_id in meter_ids:
        meter_file = os.path.join(METERS_FOLDER, f"meter_{meter_id}.txt")
        if not os.path.exists(meter_file): 
            with open(meter_file, "w") as f:
                f.write("0.0")
            print(f"Created missing meter file: {meter_file}")


def run_meters():
    
    os.makedirs(METERS_FOLDER, exist_ok=True)
    print("Mock Meter started...\n")

    while True:
        users = load_users()
        check_meter_id()
        meters = {u: os.path.join(METERS_FOLDER, f"meter_{data['meter_id']}.txt") for u, data in users.items()}

        print(f"Now updating {len(meters)} meters...\n")

        for username, meter_file in meters.items():
            if not os.path.exists(meter_file):
                with open(meter_file, "w") as f:
                    f.write("0.00")

            kwh = load_total_kwh(meter_file)
            usage = get_next_usage()
            kwh += usage
            save_total_kwh(meter_file, kwh)
            print(f"{datetime.now().strftime('%H:%M:%S')} - {username}: {kwh:.8f} kWh")

        time.sleep(1)



# Meter data output API

import os
from flask import Flask, jsonify
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=5)

def read_meter_data(meter_id):

    meter_file = os.path.join(METERS_FOLDER, f"meter_{meter_id}.txt")
    
    with open(meter_file, "r") as f:
        return float(f.read().strip())


@app.route("/get_meter_data/<meter_id>", methods=["GET"])
def get_meter_data(meter_id):

    future = executor.submit(read_meter_data, meter_id)
    reading = future.result()

    return jsonify({
        "meter_id": meter_id,
        "reading_kwh": reading
    })


import threading

if __name__ == "__main__":
    # 在后台线程中运行 run_meters()
    threading.Thread(target=run_meters, daemon=True).start()

    # 运行 Flask 服务器
    app.run(port=5001, debug=True)
    
    

