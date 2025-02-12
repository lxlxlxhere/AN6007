
from flask import Flask
from flask import render_template, request, redirect, url_for, flash, session, json
import textblob
import os
import requests
import pandas as pd


app = Flask(__name__)
app.secret_key = "secret_key"

USER_DATA_FILE = "users.json"
DAILY_CSV_FILE = "electricity_data_daily.csv"
TODAY_CSV_FILE = "electricity_data_today.csv"
METER_API_URL  = "http://127.0.0.1:5001/get_meter_data/"

# 加载用户信息
def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}  # 处理空文件情况
    return {}

# 保存用户信息
def save_users(users):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

# 生成电表 ID
def generate_meter_id(users):
    last_id = 100000001

    if users:
        existing_ids = [int(user["meter_id"]) for user in users.values()]
        if existing_ids:
            last_id = max(existing_ids) + 1
    return str(last_id)

# 添加电表 ID 至 CSV 文件
def update_csv_with_new_meter(meter_id):

    df = pd.read_csv(TODAY_CSV_FILE)

    if meter_id not in df.columns:
        df[meter_id] = None

    df.to_csv(TODAY_CSV_FILE, index=False)

    df = pd.read_csv(DAILY_CSV_FILE)

    if meter_id not in df.columns:
        df[meter_id] = None

    df.to_csv(DAILY_CSV_FILE, index=False)

# 创建电表文件
def create_meter_file(meter_id):

    folder = "meter_data"
    os.makedirs(folder, exist_ok=True)  # 确保文件夹存在（如果不存在，则创建）

    meter_file = os.path.join(folder, f"meter_{meter_id}.txt")  # 组合路径

    if not os.path.exists(meter_file):  # 确保不会覆盖已有数据
        open(meter_file, "w").close()  # 创建空文件

# 读取用户电表数据
def get_meter_reading(meter_id):

    response = requests.get(f"{METER_API_URL}{meter_id}")
    data = response.json()
    return float(data.get("reading_kwh", "No Data"))  # 获取用电量，如果没有就返回 No Data

# 计算用户的用电量统计数据
from datetime import datetime, timedelta
def get_user_usage(meter_id):
    """ 计算用户的用电量统计数据 """
    
    df_daily = pd.read_csv(DAILY_CSV_FILE)
    df_today = pd.read_csv(TODAY_CSV_FILE)
    
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    last_weekend = (now - timedelta(days=now.weekday() + 1)).strftime("%Y-%m-%d")
    last_month_end = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_month_end = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
    
    df_valid = df_today.dropna(subset=[meter_id])
    recent_half_hour_usage = df_valid[meter_id].iloc[-1] - df_valid[meter_id].iloc[-2]

    today_usage = get_meter_reading(meter_id) - df_daily[df_daily["date"] == yesterday_str][meter_id].values[0]
    week_usage = get_meter_reading(meter_id) - df_daily[df_daily["date"] == last_weekend][meter_id].values[0]
    month_usage = get_meter_reading(meter_id) - df_daily[df_daily["date"] == last_month_end][meter_id].values[0]
    last_month_usage = df_daily[df_daily["date"] == last_month_end][meter_id].values[0] - df_daily[df_daily["date"] == prev_month_end][meter_id].values[0]
    
    return {
        "recent_half_hour_usage": round(recent_half_hour_usage, 2),
        "today_usage": round(today_usage, 2),
        "week_usage": round(week_usage, 2),
        "month_usage": round(month_usage, 2),
        "last_month_usage": round(last_month_usage, 2)
    }


# ——————————————————————————————————————————————————————

@app.route('/', methods = ["GET", "POST"])
def usertype():
    return render_template('usertype.html')

@app.route("/login", methods = ["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()

        if username not in users:
            flash("Username does not exist!", "error")
            return redirect(url_for("login"))
        
        elif users[username]["password"] != password:
            flash("Incorrect password!", "error")
            return redirect(url_for("login"))
        
        else:
            session["username"] = username
            session["meter_id"] = users[username]["meter_id"]
            return redirect(url_for("main"))  # 登录成功跳转到 main 页面

    return render_template("login.html")

@app.route("/main", methods=["GET", "POST"])
def main():
    username = session.get("username")  # Retrieve username from session
    meter_id = session.get("meter_id", "N/A")    # Retrieve meter ID from session
    return render_template("main.html", username=username, meter_id=meter_id)

@app.route("/signup", methods = ["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match! Please try again.", "error")
            return redirect(url_for("signup"))

        users = load_users()

        if username in users:
            flash("Username already exists! Please choose another one.", "error")
            return redirect(url_for("signup"))

        meter_id = generate_meter_id(users)

        # 保存到 JSON 文件
        users[username] = {"password": password, "meter_id": meter_id}
        save_users(users)

        # 保存到 CSV 文件
        update_csv_with_new_meter(meter_id)

        # 创建对应的电表数据文件
        create_meter_file(meter_id)

        flash(f"Sign up successful!<br>Your Meter ID is {str(meter_id)[:3]}-{str(meter_id)[3:6]}-{str(meter_id)[6:]}.<br>Redirecting to login page...", "success")
        return redirect(url_for("signup"))  # 先回到 signup.html 显示成功消息，然后 3 秒后跳转

    return render_template("signup.html")

@app.route("/user_meter", methods=["GET"])
def user_meter():

    meter_id = session.get("meter_id")  # 获取当前用户的 meter_id
    usage_value = get_meter_reading(meter_id)

    return render_template("user_meter.html", usage=usage_value)

@app.route("/user_usage", methods=["GET"])
def user_usage():
    """ 渲染电表用电量页面 """
    meter_id = session.get("meter_id")  # 获取当前用户的 meter_id
    
    usage_data = get_user_usage(meter_id)

    return render_template("user_usage.html", 
                           recent_half_hour_usage=usage_data["recent_half_hour_usage"], 
                           today_usage=usage_data["today_usage"], 
                           week_usage=usage_data["week_usage"], 
                           month_usage=usage_data["month_usage"], 
                           last_month_usage=usage_data["last_month_usage"])

@app.route("/supplier", methods=["GET", "POST"])
def supplier():
    return render_template("supplier.html")

@app.route("/supplier_result", methods=["POST"])
def supplier_result():
    meter_id = request.form["meter_id"]  # 获取输入的电表 ID
    usage_value = get_meter_reading(meter_id)  # 通过 API 获取电表数据

    return render_template("supplier_result.html", meter_id=meter_id, usage=usage_value)

@app.route("/administrator")
def administrator():
    if not os.path.exists(DAILY_CSV_FILE):
        return "No data available"

    # 读取数据
    df = pd.read_csv(DAILY_CSV_FILE)
    df = df.sort_values(by="date")  # 确保日期有序

    # 计算每天的总用电量（当天读数 - 前一天读数）
    df.set_index("date", inplace=True)
    df_consumption = df.diff().dropna()  # 计算差值并移除第一行
    df_consumption["total_consumption"] = df_consumption.sum(axis=1)

    # 传递数据给前端
    dates = df_consumption.index.tolist()
    consumption = df_consumption["total_consumption"].tolist()

    return render_template("administrator.html", dates=dates, consumption=consumption)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()  # Clear session data on logout
    return redirect(url_for("login"))  # Redirect to login page

if __name__ == "__main__":
    app.run(port=5000)