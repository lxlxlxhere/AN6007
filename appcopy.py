# v1
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import requests
import pandas as pd
import json
from datetime import datetime
from meter import MeterManager
from user import UserManager

app = Flask(__name__)
app.secret_key = "secret_key"

user_manager = UserManager()
meter_manager = MeterManager()

# ——————————————————————————————————————————————

@app.route('/')
def usertype():
    response_data = {"page": "usertype.html"}
    return render_template('usertype.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not user_manager.validate_user(username, password):
            flash("Invalid username or password!", "error")
            response_data = {"error": "Invalid username or password"}
            return redirect(url_for("login"))

        session["username"] = username
        session["meter_id"] = user_manager.get_meter_id(username)
        response_data = {"success": True, "username": username}
        return redirect(url_for("main"))

    response_data = {"page": "login.html"}
    return render_template("login.html")

@app.route("/main", methods=["GET"])
def main():
    username = session.get("username")
    meter_id = session.get("meter_id", "N/A")
    response_data = {"username": username, "meter_id": meter_id}
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
            return redirect(url_for("signup"))

        if user_manager.add_user(username, password):
            flash("Sign up successful!", "success")
            response_data = {"success": True, "username": username}
            return redirect(url_for("login"))
        else:
            flash("Username already exists!", "error")
            response_data = {"error": "Username already exists"}
            return redirect(url_for("signup"))

    response_data = {"page": "signup.html"}
    return render_template("signup.html")

@app.route("/user_meter", methods=["GET"])
def user_meter():

    meter_id = session.get("meter_id")
    usage_value = meter_manager.get_meter_reading(meter_id)
    response_data = {"meter_id": meter_id, "usage_kwh": usage_value}
    return render_template("user_meter.html", usage=usage_value)

# 访问 user_usage.html 前先检查 acceptAPI 状态
@app.route("/user_usage", methods=["GET"])
def user_usage():

    response = requests.get("http://127.0.0.1:5002/api/server_status")
    
    if response.status_code == 200 and response.json().get("acceptAPI", False):
        meter_id = session.get("meter_id")
        usage_data = meter_manager.get_user_usage(meter_id)
        return render_template("user_usage.html", **usage_data)
    else:
        return redirect("/server_busy")  # **如果 `acceptAPI = False`，跳转到 `server_busy.html`**

@app.route("/server_busy", methods=["GET"])
def server_busy():
    return render_template("server_busy.html")

# ——————————————————————————————————————————

@app.route("/supplier", methods=["GET", "POST"])
def supplier():
    return render_template("supplier.html")

@app.route("/supplier_result", methods=["POST"])
def supplier_result():
    meter_id = request.form["meter_id"]
    usage_value = meter_manager.get_meter_reading(meter_id)

    return render_template("supplier_result.html", meter_id=meter_id, usage=usage_value)

# ——————————————————————————————————————————

@app.route("/administrator")
def administrator():
    pass

# ——————————————————————————————————————————

@app.route("/logout", methods=["POST"])
def logout():
    username = session.get("username")
    session.clear()
    response_data = {"success": True, "username": username}
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(port=5000, debug=True)
