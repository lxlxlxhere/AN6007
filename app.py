from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import requests
import pandas as pd
import json
from datetime import datetime
from meter import MeterManager
from user import UserManager

# 创建 Flask 应用
app = Flask(__name__)
app.secret_key = "secret_key"

# 实例化管理类
user_manager = UserManager()
meter_manager = MeterManager()

# 日志记录函数
def log_request(method, endpoint, params=None, response_data=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_message = f"[{timestamp}] {method} {endpoint} - Params: {params} - Response: {json.dumps(response_data)}\n"
    
    with open("log.txt", "a") as log_file:
        log_file.write(log_message)

# ——————————————————————————————————————————

@app.route('/')
def usertype():
    response_data = {"page": "usertype.html"}
    log_request("GET", "/", response_data=response_data)
    return render_template('usertype.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not user_manager.validate_user(username, password):
            flash("Invalid username or password!", "error")
            response_data = {"error": "Invalid username or password"}
            log_request("POST", "/login", {"username": username}, response_data)
            return redirect(url_for("login"))

        session["username"] = username
        session["meter_id"] = user_manager.get_meter_id(username)
        response_data = {"success": True, "username": username}
        log_request("POST", "/login", {"username": username}, response_data)
        return redirect(url_for("main"))

    response_data = {"page": "login.html"}
    log_request("GET", "/login", response_data=response_data)
    return render_template("login.html")

@app.route("/main", methods=["GET"])
def main():
    username = session.get("username")
    meter_id = session.get("meter_id", "N/A")
    response_data = {"username": username, "meter_id": meter_id}
    log_request("GET", "/main", {"username": username}, response_data)
    return render_template("main.html", username=username, meter_id=meter_id)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            response_data = {"error": "Passwords do not match"}
            log_request("POST", "/signup", {"username": username}, response_data)
            return redirect(url_for("signup"))

        if user_manager.add_user(username, password):
            flash("Sign up successful!", "success")
            response_data = {"success": True, "username": username}
            log_request("POST", "/signup", {"username": username}, response_data)
            return redirect(url_for("login"))
        else:
            flash("Username already exists!", "error")
            response_data = {"error": "Username already exists"}
            log_request("POST", "/signup", {"username": username}, response_data)
            return redirect(url_for("signup"))

    response_data = {"page": "signup.html"}
    log_request("GET", "/signup", response_data=response_data)
    return render_template("signup.html")

@app.route("/user_meter", methods=["GET"])
def user_meter():

    meter_id = session.get("meter_id")
    usage_value = meter_manager.get_meter_reading(meter_id)
    response_data = {"meter_id": meter_id, "usage_kwh": usage_value}
    log_request("GET", "/user_meter", {"meter_id": meter_id}, response_data)
    return render_template("user_meter.html", usage=usage_value)

@app.route("/user_usage", methods=["GET"])
def user_usage():
    meter_id = session.get("meter_id")
    usage_data = meter_manager.get_user_usage(meter_id)
    log_request("GET", "/user_usage", {"meter_id": meter_id}, usage_data)
    return render_template("user_usage.html", **usage_data)

@app.route("/logout", methods=["POST"])
def logout():
    username = session.get("username")
    session.clear()
    response_data = {"success": True, "username": username}
    log_request("POST", "/logout", {"username": username}, response_data)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(port=5000, debug=True)