import os
import json
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# 文件路径
USER_DATA_FILE = "users.json"
TODAY_CSV_FILE = "electricity_data_today.csv"  # 当天数据
DAILY_CSV_FILE = "electricity_data_daily.csv"  # 存放每日存档数据
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

def archive_previous_day():
    """ 存档前一天 23:30 的读数，并创建新的一天 """
    users = load_users()
    meter_ids = [data["meter_id"] for data in users.values()]  # 获取所有电表 ID

    if not os.path.exists(DAILY_CSV_FILE):
        # 创建每日存档数据文件
        df_daily = pd.DataFrame(columns=["date"] + meter_ids)
        df_daily.to_csv(DAILY_CSV_FILE, index=False)

    df_today = pd.read_csv(TODAY_CSV_FILE)

    # 提取前一天 23:30 的数据，并去掉时间戳
    last_timestamp = "23:30"
    last_day = df_today[df_today["timestamp"] == last_timestamp].drop(columns=["timestamp"])

    if not last_day.empty:
        today = datetime.today().strftime("%Y-%m-%d")
        last_day["date"] = today  # 添加存档日期
        last_day.to_csv(DAILY_CSV_FILE, mode="a", header=False, index=False)
        print(f"Archived previous day data to: {DAILY_CSV_FILE}")

    # 清空 `electricity_data_today.csv`
    os.remove(TODAY_CSV_FILE)
    ensure_csv_structure()

def ensure_csv_structure():
    """ 确保 `electricity_data_today.csv` 存在，并且格式正确 """
    today = datetime.today().strftime("%Y-%m-%d")
    users = load_users()
    meter_ids = [data["meter_id"] for data in users.values()]

    # 生成 01:00 - 23:30，每 30 分钟的时间戳
    time_stamps = pd.date_range(start="01:00", end="23:30", freq="30T").strftime("%H:%M").tolist()

    if not os.path.exists(TODAY_CSV_FILE):
        df = pd.DataFrame({"date": [today] * len(time_stamps), "timestamp": time_stamps})
        for meter_id in meter_ids:
            df[meter_id] = None  # 创建电表数据列
        df.to_csv(TODAY_CSV_FILE, index=False)
        print(f"Created new CSV for today: {TODAY_CSV_FILE}")
    else:
        df = pd.read_csv(TODAY_CSV_FILE)

        # 确保所有电表 ID 都有列
        for meter_id in meter_ids:
            if meter_id not in df.columns:
                df[meter_id] = None
        df.to_csv(TODAY_CSV_FILE, index=False)

def update_meter_readings():
    """ 读取所有用户的电表数据，并更新到当天的 CSV """
    users = load_users()
    if not users:
        return

    now = datetime.now()
    timestamp = now.strftime("%H:%M")  # 只记录时:分

    df = pd.read_csv(TODAY_CSV_FILE)

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

    df.to_csv(TODAY_CSV_FILE, index=False)

if __name__ == "__main__":
    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        # **归档前一天数据 (00:00 - 00:59 运行一次)**
        if now.hour == 0 and now.minute < 60:
            archive_previous_day()

        # **确保数据结构正确**
        ensure_csv_structure()

        # **仅在 01:00 - 23:30 运行电表读数更新**
        if 1 <= now.hour < 24:
            update_meter_readings()

        # **计算下一个 :00 或 :30 的时间**
        next_run = now.replace(second=0, microsecond=0) + timedelta(minutes=30 - now.minute % 30)
        sleep_seconds = (next_run - datetime.now()).total_seconds()

        print(f"当前时间：{current_time}, 计划下次运行时间：{next_run.strftime('%H:%M')}, 休眠 {sleep_seconds:.0f} 秒")
        time.sleep(sleep_seconds)