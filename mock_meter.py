import time
import random
import json
import os
from datetime import datetime

USER_DATA_FILE = "users.json"
METERS_FOLDER = "meter_data"

def load_users():
    """ 读取已注册的用户列表 """
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# 读取或创建电表读数 txt
def load_total_kwh(meter_file):

    try:
        with open(meter_file, "r") as f:
            return float(f.read().strip())
    except:
        return 0.0  # 否则返回 0.0

# 覆写电表读数
def save_total_kwh(meter_file, kwh):

    with open(meter_file, "w") as f:
        f.write(f"{kwh:.8f}")  # 直接覆盖旧数据

# 随机生成电量消耗
def get_next_usage():

    return round(random.uniform(0.1, 1.0)/1000000, 8)

def run_meters():
    
    os.makedirs(METERS_FOLDER, exist_ok=True)
    print("Mock Meter started...\n")

    while True:
        users = load_users()  # **每次循环都重新加载用户**
        meters = {u: os.path.join(METERS_FOLDER, f"meter_{data['meter_id']}.txt") for u, data in users.items()}

        print(f"Now updating {len(meters)} meters...\n")

        for username, meter_file in meters.items():
            if not os.path.exists(meter_file):  # 如果文件不存在，则创建并初始化
                with open(meter_file, "w") as f:
                    f.write("0.00")  # 初始总用电量为 0.00

            kwh = load_total_kwh(meter_file)  # 读取当前总电量
            usage = get_next_usage()  # 计算本次新增用电
            kwh += usage  # 叠加用电量
            save_total_kwh(meter_file, kwh)  # 覆盖旧数据
            print(f"{datetime.now().strftime('%H:%M:%S')} - {username}: {kwh:.8f} kWh")

        time.sleep(1)  # 每秒钟更新一次

if __name__ == "__main__":
    run_meters()