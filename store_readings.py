# v1
import os
import pandas as pd
import json
import csv
import requests
import time
import threading
import schedule
import requests
from datetime import datetime, timedelta, time
from flask import Flask, jsonify, request
from concurrent.futures import ThreadPoolExecutor

USER_API_URL = "http://127.0.0.1:5000/meter_ids"
METER_API_URL = "http://127.0.0.1:5001/get_meter_data/"
METER_DATA_FOLDER = "meter_data"
USERS_DATA_FILE = "users.json"
TODAY_CSV = "electricity_data_today.csv"
DAILY_CSV = "electricity_data_daily.csv"

acceptAPI = True

data_today = {}
data_daily = {}
server_running = True

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=5)
# Use ThreadPoolExecutor to handle multiple requests concurrently

# 读取所有已注册 meter_id ———————————————————————————————————————————————————————
# Retrieve all registered meter_id

def load_meter_ids():
    response = requests.get(USER_API_URL)
    meter_ids = response.json()
    return meter_ids

# 每半小时读取数据 ---------------------------------------------------------------
# Read data every half hour

# 读取数据至 当日dic
# Read data into today’s dic
def fetch_meter_data():

    global data_today
    meter_ids = load_meter_ids()
    current_time = datetime.now().strftime("%H%M")
    print(current_time)
    print(meter_ids)

    for meter_id in meter_ids:
        response = requests.get(f"{METER_API_URL}{meter_id}")
        reading = response.json().get("reading_kwh", None)
        print(meter_id, reading)
        if reading is not None:
            if meter_id not in data_today:
                data_today[meter_id] = {}
            data_today[meter_id][current_time] = reading
    save_today_data_to_csv(data_today)

# 复制当日 dic 至 当日 csv
# Copy today’s dic to today’s CSV
def save_today_data_to_csv(data_today, filename=TODAY_CSV):
    current_date = datetime.now().strftime("%Y%m%d")

    df = pd.read_csv(filename)

    latest_data = {}
    for meter_id, readings in data_today.items():
        if readings:
            latest_timestamp = max(readings.keys())
            latest_data[meter_id] = readings[latest_timestamp]

    for meter_id in latest_data.keys():
        if meter_id not in df.columns:
            df[meter_id] = ""

    latest_df = pd.DataFrame([[current_date, latest_timestamp] + list(latest_data.values())], 
                             columns=["date", "timestamp"] + list(latest_data.keys()))

    df = pd.concat([df, latest_df], ignore_index=True)

    df.to_csv(filename, index=False)
    print(f"Latest data appended to {filename}")

# 每日数据归档 ——————————————————————————————————————————————————————————————————
# Daily data archiving

# 将 当日dic 存储至 每日dic
# Store today’s dic into the daily dic
def archive_to_data_daily():
    global data_today, data_daily

#    previous_date = int((datetime.now() - timedelta(days=1)).strftime("%Y%m%d"))
    previous_date = int((datetime.now()).strftime("%Y%m%d"))

    for meter_id, readings in data_today.items():
        if readings:
            last_timestamp = max(readings.keys())  # last_timestamp = 2330
            last_reading = readings[last_timestamp]
            
            if meter_id not in data_daily:
                data_daily[meter_id] = {}
            
            data_daily[meter_id][previous_date] = last_reading

    print("Daily data archived:", data_daily)

# 将 每日dic 存储至 每日csv
# Store daily dic into the daily csv
def archive_to_csv_daily():
    global data_today, data_daily

#    previous_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    previous_date = (datetime.now().strftime("%Y%m%d"))

    if os.path.exists(DAILY_CSV):
        df = pd.read_csv(DAILY_CSV)
    else:
        df = pd.DataFrame(columns=["date"])

    readings_2330 = {}
    for meter_id, readings in data_today.items():
        if readings:
            last_timestamp = max(readings.keys())  # last_timestamp = 2330
            last_reading = readings[last_timestamp]  # 读取最新读数
            readings_2330[meter_id] = last_reading  # 存入字典

            if meter_id not in data_daily:
                data_daily[meter_id] = {}
            data_daily[meter_id][int(previous_date)] = last_reading

    for meter_id in readings_2330.keys():
        if meter_id not in df.columns:
            df[meter_id] = ""

    if previous_date in df["date"].values:
        df.loc[df["date"] == previous_date, readings_2330.keys()] = list(readings_2330.values())
    else:
        new_row = {"date": previous_date, **readings_2330}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(DAILY_CSV, index=False)

    print(f"Daily data archived and saved to {DAILY_CSV}")

# 清空 当日dic & 当日csv
# Clear today’s dic & today’s CSV
def clear_data_today():
    global data_today
    data_today.clear()
    print("data_today.dic has been cleared.")

    with open(TODAY_CSV, "w") as f:
        f.write("date,timestamp\n")
    print("electricity_data_today.csv has been cleared, only headers remain.")



# 恢复数据 ——————————————————————————————————————————————————————————————————————
# Restore data to dic from csv (if needed)

def restore_today():
    global data_today

    df = pd.read_csv(TODAY_CSV, dtype={"timestamp": str})

    data_today = {}

    for _, row in df.iterrows():
        timestamp = str(row["timestamp"])
        for meter_id in df.columns[2:]:
            if pd.notna(row[meter_id]):
                if meter_id not in data_today:
                    data_today[meter_id] = {}
                data_today[meter_id][timestamp] = float(row[meter_id])

    print(" Data restored from electricity_data_today.csv to data_today")

def restore_daily():
    global data_daily
    data_daily = {}

    with open(DAILY_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

        for row in reader:
            date = int(row[0].replace("-", ""))
            
            for i, meter_id in enumerate(header[1:], start=1):
                if row[i].strip():
                    if meter_id not in data_daily:
                        data_daily[meter_id] = {}
                    data_daily[meter_id][date] = float(row[i])

    print(" Data restored from electricity_data_daily.csv to data_daily")


# 定时任务 ——————————————————————————————————————————————————————————————————————
# Scheduled task
import time

def start_scheduler():

    schedule.every().hour.at(":00").do(fetch_meter_data)
    schedule.every().hour.at(":30").do(fetch_meter_data)
    schedule.every().hour.at("00:00").do(stop_server)


    # 需要测试的话，可将数字改为接下来即将到来的分钟，如：
    # If testing is needed, you can change the number to the upcoming minute:

#    schedule.every().hour.at(":00").do(fetch_meter_data)
#    schedule.every().hour.at(":01").do(fetch_meter_data)
#    schedule.every().hour.at(":01").do(archive_to_data_daily)
#    schedule.every().hour.at(":01").do(archive_to_csv_daily)

    while server_running:
        schedule.run_pending()
        time.sleep(10)  # 每10秒检查一次 check per 10s

def start_background_scheduler():

    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

# 当日数据查询 api ———————————————————————————————————————————————————————————————
# API for querying today’s data

@app.route("/get_today_data/<meter_id>", methods=["GET"])
def get_today_data(meter_id):
    global acceptAPI
    if acceptAPI:
        if meter_id in data_today:
            latest_timestamp = max(data_today[meter_id].keys())  # 获取最新时间戳
            latest_reading = data_today[meter_id][latest_timestamp]  # 获取最新读数
            return jsonify({
                "meter_id": meter_id,
                "timestamp": latest_timestamp,
                "latest_reading": latest_reading
            })
        else:
            return jsonify({
                "meter_id": meter_id,
                "message": "No data found for this meter ID."
            }), 404
    else:
        return jsonify({
            "meter_id": meter_id,
            "message": "Server is busy."
        }), 404

# 每日数据查询 api ———————————————————————————————————————————————————————————————
# API for querying daily data

@app.route("/get_daily_data/<meter_id>", methods=["GET"])
def get_daily_data(meter_id):
    global acceptAPI
    if acceptAPI:

        query_date = request.args.get("date")

        if not query_date:
            return jsonify({"error": "Missing required parameter: date"}), 400  # 缺少参数

        try:
            query_date = int(query_date)
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYYMMDD"}), 400  # 日期格式错误

        if meter_id in data_daily and query_date in data_daily[meter_id]:
            return jsonify({
                "meter_id": meter_id,
                "date": query_date,
                "reading": data_daily[meter_id][query_date]
            })
        else:
            return jsonify({
                "meter_id": meter_id,
                "date": query_date,
                "message": "No data found for this meter_id on this date."
            }), 404
    else:
        return jsonify({
            "meter_id": meter_id,
            "date": query_date,
            "message": "Server is busy."
        }), 404

# creat test data ——————————————————————————————————————————————————————————————
import random

def create_test_data():
    meter_ids = load_meter_ids()
    start_date = datetime(2024, 12, 31)
    end_date = datetime.today() - timedelta(days=1)
    num_days = (end_date - start_date).days + 1
    
    # generate daily data
    daily_data = [["date"] + meter_ids]
    initial_values = {meter: random.uniform(100, 500) for meter in meter_ids}
    
    for i in range(num_days):
        date = (start_date + timedelta(days=i)).strftime("%Y%m%d")
        row = [date] + [round(initial_values[meter] + i * random.uniform(18, 22), 2) for meter in meter_ids]
        daily_data.append(row)
    
    with open(DAILY_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(daily_data)
    
    from datetime import time
    # generate today's data
    last_day_values = {meter: row[i + 1] for i, meter in enumerate(meter_ids)}
    today_date = datetime.today().strftime("%Y%m%d")
    start_time = datetime.combine(datetime.today(), time(0, 0))
    now = datetime.now()
    last_half_hour = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)
    print(last_half_hour)
    print(start_time)
    num_intervals = (last_half_hour - start_time).seconds // 1800
    
    today_data = [["date", "timestamp"] + meter_ids]
    increment_per_step = {meter: (random.uniform(18, 22) / num_intervals) for meter in meter_ids}
    
    timestamps = []
    for hour in range((num_intervals + 1) // 2 + 1):
        timestamps.append(hour * 100)
        timestamps.append(hour * 100 + 30)

    for i, timestamp in enumerate(timestamps):
        row = [today_date, timestamp] + [
            round(last_day_values[meter] + i * increment_per_step[meter], 2) for meter in meter_ids
        ]
        today_data.append(row)
    
    # updata real-time meter readings
    with open(TODAY_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(today_data)
    
        meter_index = {meter: i+2 for i, meter in enumerate(meter_ids)}
    
    latest_row = today_data[-1]
    meter_index = {meter: i+2 for i, meter in enumerate(meter_ids)}
    
    for meter in meter_ids:
        meter_file_path = os.path.join(METER_DATA_FOLDER, f"meter_{meter}.txt")
        with open(meter_file_path, "w") as meter_file:
            meter_file.write(str(latest_row[meter_index[meter]]) + "\n")

# batch jobs ———————————————————————————————————————————————————————————————————

def batchJobs():

    print("Running batch jobs...\n")

    thread1 = threading.Thread(target=archive_to_csv_daily)
    thread2 = threading.Thread(target=archive_to_data_daily)
    print("data of the past day:\n")
    print(data_daily)
    print(data_today)
    clear_data_today()
    print("\ndata of the past cleared\n")
    print("data of today\n")
    print(data_daily)
    print(data_today)
    thread1.start()
    thread2.start()
    
    thread1.join()
    thread2.join()

# stop server ——————————————————————————————————————————————————————————————————
import time

@app.route("/stopserver", methods=["GET"])
def stop_server():
    global acceptAPI
    acceptAPI = False
    batchJobs()
    time.sleep(8) # time for demonstrating the stopserver page
    acceptAPI = True
    return jsonify({"message": "Server is stopping", "status": "success"})

# 返回 服务器是否接受 API 请求
# return whether the server accepts API requests
@app.route("/api/server_status", methods=["GET"])
def get_server_status():
    return jsonify({"acceptAPI": acceptAPI})

# main ————————————————————————————————————————————————————————————————————————

if __name__ == "__main__":
    create_test_data()
    restore_today()    # restore today's data
    restore_daily()    # restore daily data
    print(data_today)
    print(data_daily)
    start_background_scheduler()
    app.run(port=5002, debug=True)
