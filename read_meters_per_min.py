import os
import json
import pandas as pd
import requests
import time
from datetime import datetime


# 文件路径
USER_DATA_FILE = "users.json"
CSV_FILE = "electricity_data_per_min.csv"
METER_API_URL = "http://127.0.0.1:5001/get_meter_data/"

def load_users():
    """ 读取已注册用户列表 """
    with open(USER_DATA_FILE, "r") as f:
        return json.load(f)

def fetch_meter_data(meter_id):
    """ 通过 `meter_api.py` 获取电表数据 """
    response = requests.get(f"{METER_API_URL}{meter_id}")
    data = response.json()
    return float(data["reading_kwh"])

def ensure_csv_structure():
    """ 确保 CSV 文件存在并具有正确的结构（每分钟时间戳） """
    today = datetime.today().strftime("%Y-%m-%d")
    users = load_users()
    meter_ids = [data["meter_id"] for data in users.values()]

    if not os.path.exists(CSV_FILE):
        # 生成每分钟的时间戳（格式 HH:MM）
        time_stamps = pd.date_range(start="00:00", end="23:59", freq="1T").strftime("%H:%M").tolist()
        df = pd.DataFrame({"date": [today] * len(time_stamps), "timestamp": time_stamps})
        for meter_id in meter_ids:
            df[meter_id] = None  # 创建新列
        df.to_csv(CSV_FILE, index=False)
    else:
        df = pd.read_csv(CSV_FILE)

        # 检查日期是否为今天
        last_date = df["date"].iloc[-1] if "date" in df.columns else None
        if last_date != today:
            # 生成今天的新时间戳
            time_stamps = pd.date_range(start="00:00", end="23:59", freq="1T").strftime("%H:%M").tolist()
            new_day_df = pd.DataFrame({"date": [today] * len(time_stamps), "timestamp": time_stamps})
            for meter_id in meter_ids:
                new_day_df[meter_id] = None
            df = pd.concat([df, new_day_df], ignore_index=True)
            df.to_csv(CSV_FILE, index=False)

        # 确保所有电表 ID 都有列
        for meter_id in meter_ids:
            if meter_id not in df.columns:
                df[meter_id] = None
        df.to_csv(CSV_FILE, index=False)

def update_meter_readings():
    """ 读取所有用户的电表数据，并更新到 CSV """
    users = load_users()
    if not users:
        return

    now = datetime.now()
    timestamp = now.strftime("%H:%M")  # 时间戳只精确到分钟

    df = pd.read_csv(CSV_FILE)

    # 确保时间戳存在
    if timestamp not in df["timestamp"].values:
        return

    meter_data = {"timestamp": timestamp}
    for username, data in users.items():
        meter_id = data["meter_id"]
        reading = fetch_meter_data(meter_id)
        meter_data[meter_id] = reading

    # 更新 CSV
    row_index = df[df["timestamp"] == timestamp].index[0]
    for meter_id, value in meter_data.items():
        df.at[row_index, meter_id] = value

    df.to_csv(CSV_FILE, index=False)

if __name__ == "__main__":
    ensure_csv_structure()
    while True:
        update_meter_readings()
        time.sleep(60)  # 每 60 秒运行一次