import os
import pandas as pd
import json
import csv
import requests
import time
import threading
import schedule
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

METER_API_URL = "http://127.0.0.1:5001/get_meter_data/"
USERS_DATA_FILE = "users.json"
TODAY_CSV = "electricity_data_today.csv"
DAILY_CSV = "electricity_data_daily.csv"

acceptAPI = True

data_today = {}
data_daily = {}
server_running = True

app = Flask(__name__)


# 读取所有已注册 meter_id ———————————————————————————————————————————————————————
def load_meter_ids():

    with open(USERS_DATA_FILE, "r") as f:
        users = json.load(f)
        meter_ids = [data["meter_id"] for data in users.values()] 
        return meter_ids


# 每半小时读取数据 ---------------------------------------------------------------

# 读取数据至 当日dic
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
    print(data_today)
    save_today_data_to_csv(data_today)

# 复制当日 dic 至 当日 csv
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

# 将 当日dic 存储至 每日dic
def archive_to_data_daily():
    global data_today, data_daily

    previous_date = int((datetime.now() - timedelta(days=1)).strftime("%Y%m%d"))

    for meter_id, readings in data_today.items():
        if readings:  # 确保 readings 不是空字典
            last_timestamp = max(readings.keys())  # last_timestamp = 2330
            last_reading = readings[last_timestamp]
            
            if meter_id not in data_daily:
                data_daily[meter_id] = {}
            
            data_daily[meter_id][previous_date] = last_reading

    print("Daily data archived:", data_daily)

def archive_to_csv_daily():
    global data_today, data_daily

    previous_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

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
            data_daily[meter_id][int(previous_date.replace("-", ""))] = last_reading

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
def clear_data_today():
    global data_today
    data_today.clear()
    print("data_today.dic has been cleared.")

    with open(TODAY_CSV, "w") as f:
        f.write("date,timestamp\n")
    print("electricity_data_today.csv has been cleared, only headers remain.")



# 恢复数据 ——————————————————————————————————————————————————————————————————————


def restore_today():
    global data_today  # 确保修改的是全局变量

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

    df = pd.read_csv(DAILY_CSV)

    data_daily = {}

    for _, row in df.iterrows():
        date = int(row["date"].replace("-", ""))
        for meter_id in df.columns[1:]:
            if pd.notna(row[meter_id]):
                if meter_id not in data_daily:
                    data_daily[meter_id] = {}
                data_daily[meter_id][date] = row[meter_id]

    print(" Data restored from electricity_data_daily.csv to data_daily")


# 定时任务 ——————————————————————————————————————————————————————————————————————

def start_scheduler():

    schedule.every().hour.at(":00").do(fetch_meter_data)
    schedule.every().hour.at(":30").do(fetch_meter_data)
    schedule.every().hour.at("00:00").do(stop_server)


    # 需要测试的话，可将数字改为接下来即将到来的分钟，如：
#    schedule.every().hour.at(":00").do(fetch_meter_data)
#    schedule.every().hour.at(":01").do(fetch_meter_data)
#    schedule.every().hour.at(":01").do(archive_to_data_daily)
#    schedule.every().hour.at(":01").do(archive_to_csv_daily)

    while server_running:
        schedule.run_pending()
        time.sleep(10)  # 每10秒检查一次

def start_background_scheduler():

    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

# 当日数据查询 api ———————————————————————————————————————————————————————————————


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

@app.route("/get_daily_data/<meter_id>", methods=["GET"])
def get_daily_data(meter_id):
    global acceptAPI
    if acceptAPI:

        query_date = request.args.get("date")

        if not query_date:
            return jsonify({"error": "Missing required parameter: date"}), 400  # 缺少参数

        try:
            query_date = int(query_date)  # 确保日期是整数格式 (YYYYMMDD)
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

# batch jobs ———————————————————————————————————————————————————————————————————

def batchJobs():

    print(" Running batch jobs...")

    thread1 = threading.Thread(target=archive_to_csv_daily)
    thread2 = threading.Thread(target=archive_to_data_daily)
    
    thread1.start()
    thread2.start()
    
    thread1.join()
    thread2.join()

# stop server ——————————————————————————————————————————————————————————————————

@app.route("/stopserver", methods=["GET"])
def stop_server():
    global acceptAPI
    acceptAPI = False
    batchJobs()
    time.sleep(8)
    acceptAPI = True

@app.route("/api/server_status", methods=["GET"])
def get_server_status():
    """ 返回服务器是否接受 API 请求 """
    return jsonify({"acceptAPI": acceptAPI})

# 主程序 ————————————————————————————————————————————————————————————————————————


# **7️⃣ 启动 Flask 服务器**
if __name__ == "__main__":
    restore_today() #从csv恢复当日数据
    restore_daily() #从csv恢复每日数据
    print(data_today)
    print(data_daily)
    start_background_scheduler()
    app.run(port=5002, debug=True)
