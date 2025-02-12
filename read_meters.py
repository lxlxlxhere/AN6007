import os
import json
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

USER_DATA_FILE = "users.json"
TODAY_CSV_FILE = "electricity_data_today.csv"
DAILY_CSV_FILE = "electricity_data_daily.csv"
METER_API_URL = "http://127.0.0.1:5001/get_meter_data/"

# 加载用户数据
def load_users():

    with open(USER_DATA_FILE, "r") as f:
        return json.load(f)

# 获取电表 ID
def fetch_meter_data(meter_id):

    response = requests.get(f"{METER_API_URL}{meter_id}")
    data = response.json()
    return float(data["reading_kwh"])

# 存档前一天数据
def archive_previous_day():

    users = load_users()
    meter_ids = [data["meter_id"] for data in users.values()]  # 获取所有电表 ID

    if not os.path.exists(DAILY_CSV_FILE):

        df_daily = pd.DataFrame(columns=["date"] + meter_ids)
        df_daily.to_csv(DAILY_CSV_FILE, index=False)

    df_today = pd.read_csv(TODAY_CSV_FILE)

    # 提取前一天 23:30 的数据，并去掉时间戳
    last_timestamp = "23:30"
    last_day = df_today[df_today["timestamp"] == last_timestamp].drop(columns=["timestamp"])

    if not last_day.empty:
        today = datetime.today().strftime("%Y-%m-%d")
        last_day["date"] = today
        last_day.to_csv(DAILY_CSV_FILE, mode="a", header=False, index=False)
        print(f"Archived previous day data to: {DAILY_CSV_FILE}")

    os.remove(TODAY_CSV_FILE)
    ensure_csv_structure()

# 检测 csv 文件格式是否正确
def ensure_csv_structure():

    today = datetime.today().strftime("%Y-%m-%d")
    users = load_users()
    meter_ids = [data["meter_id"] for data in users.values()]

    # 生成 01:00 - 23:30，每隔 30 分钟的时间戳
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

    users = load_users()
    if not users:
        return

    now = datetime.now()
    timestamp = now.strftime("%H:%M")

    df = pd.read_csv(TODAY_CSV_FILE)

    if timestamp not in df["timestamp"].values:
        return

    meter_data = {"timestamp": timestamp}
    for username, data in users.items():
        meter_id = data["meter_id"]
        reading = fetch_meter_data(meter_id)
        meter_data[meter_id] = reading

    row_index = df[df["timestamp"] == timestamp].index[0]
    for meter_id, value in meter_data.items():
        df.at[row_index, meter_id] = value

    df.to_csv(TODAY_CSV_FILE, index=False)

if __name__ == "__main__":
    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        # 数据归档
        if now.hour == 0 and now.minute < 60:
            archive_previous_day()

        # 检验 csv 是否正确
        ensure_csv_structure()

        # 仅在 01:00 - 23:30 运行电表读数更新
        if 1 <= now.hour < 24:
            update_meter_readings()

        # 计算下一个 :00 或 :30 的时间
        next_run = now.replace(second=0, microsecond=0) + timedelta(minutes=30 - now.minute % 30)
        sleep_seconds = (next_run - datetime.now()).total_seconds()

        print(f"Current time：{current_time}, Next run：{next_run.strftime('%H:%M')}, Sleep {sleep_seconds:.0f} s")
        time.sleep(sleep_seconds)