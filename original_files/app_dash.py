# v1
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
from meter import MeterManager
from user import UserManager
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

app = Flask(__name__)
app.secret_key = "secret_key"
user_manager = UserManager()
meter_manager = MeterManager()

# Initialize Dash app
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/dash/')

# Define layout for Dash app
dash_app.layout = html.Div(
    style={'backgroundColor': '#f9f9f9', 'padding': '20px', 'fontFamily': 'Arial, sans-serif'},
    children=[
        html.H2("Electricity Usage", style={'textAlign': 'center', 'color': '#333'}),

        # Bar Chart: Recent Usage
        html.Div(
            style={'marginBottom': '40px'},
            children=[
                html.H3("Recent Consumption", style={'textAlign': 'center', 'color': '#007bff'}),
                dcc.Graph(id='bar-chart')
            ]
        ),

        # Line Chart: Historical Trends (Last 7 Days)
        html.Div(
            style={'marginBottom': '40px'},
            children=[
                html.H3("Past 7 Days Usage", style={'textAlign': 'center', 'color': '#007bff'}),
                dcc.Graph(id='line-chart')
            ]
        ),

        # Pie Chart: Consumption Breakdown
        html.Div(
            style={'marginBottom': '40px'},
            children=[
                html.H3("Consumption Breakdown", style={'textAlign': 'center', 'color': '#007bff'}),
                dcc.Graph(id='pie-chart')
            ]
        )
    ]
)

# Define callback to update graphs based on usage data
@dash_app.callback(
    [Output('bar-chart', 'figure'),
     Output('line-chart', 'figure'),
     Output('pie-chart', 'figure')],
    [Input('bar-chart', 'id')]
)
def update_graphs(_):
    meter_id = session.get("meter_id")
    usage_data = meter_manager.get_user_usage(meter_id)
    
    # Bar Chart Data
    bar_data = {
        'labels': ['Recent 30 min', 'Today', 'Week', 'Month', 'Last Month'],
        'values': [
            usage_data['recent_half_hour_usage'],
            usage_data['today_usage'],
            usage_data['week_usage'],
            usage_data['month_usage'],
            usage_data['last_month_usage']
        ]
    }
    
    # Line Chart Data (Historical Trends for the Last 7 Days)
    historical_dates = ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05", "2025-01-06", "2025-01-07"]
    historical_usage = [100, 150, 200, 250, 300, 350, 400]  # Example data
    
    # Pie Chart Data (Consumption Breakdown)
    pie_data = {
        'labels': ['Today', 'Week', 'Month'],
        'values': [
            usage_data['today_usage'],
            usage_data['week_usage'],
            usage_data['month_usage']
        ]
    }
    
    bar_chart_figure = {
        'data': [
            {
                'x': bar_data['labels'],
                'y': bar_data['values'],
                'type': 'bar',
                'marker': {
                    'color': ['rgba(75, 192, 192, 0.6)', 'rgba(255, 99, 132, 0.6)', 'rgba(54, 162, 235, 0.6)', 
                              'rgba(255, 206, 86, 0.6)', 'rgba(153, 102, 255, 0.6)']
                }
            }
        ],
        'layout': {
            'title': 'Electricity Consumption (kWh)',
            'yaxis': {'title': 'kWh'},
            'xaxis': {'title': 'Period'},
            'plot_bgcolor': '#f9f9f9',
            'paper_bgcolor': '#f9f9f9'
        }
    }
    
    line_chart_figure = {
        'data': [
            {
                'x': historical_dates,
                'y': historical_usage,
                'type': 'line',
                'fill': 'tozeroy',
                'line': {'color': 'rgba(54, 162, 235, 1)'}
            }
        ],
        'layout': {
            'title': 'Daily Consumption (kWh)',
            'yaxis': {'title': 'kWh'},
            'plot_bgcolor': '#f9f9f9',
            'paper_bgcolor': '#f9f9f9'
        }
    }
    
    pie_chart_figure = {
        'data': [
            {
                'labels': pie_data['labels'],
                'values': pie_data['values'],
                'type': 'pie',
                'marker': {
                    'colors': ['rgba(255, 99, 132, 0.6)', 'rgba(54, 162, 235, 0.6)', 'rgba(255, 206, 86, 0.6)']
                }
            }
        ],
        'layout': {
            'title': 'Consumption Breakdown',
            'plot_bgcolor': '#f9f9f9',
            'paper_bgcolor': '#f9f9f9'
        }
    }
    
    return bar_chart_figure, line_chart_figure, pie_chart_figure


@app.route('/')
def usertype():
    return render_template('usertype.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if not user_manager.validate_user(username, password):
            flash("Invalid username or password!", "error")
            return redirect(url_for("login"))
        session["username"] = username
        session["meter_id"] = user_manager.get_meter_id(username)
        return redirect(url_for("main"))
    return render_template("login.html")

@app.route("/main", methods=["GET"])
def main():
    meter_id = session.get("meter_id", "N/A")
    username = session.get("username", "Guest")
    return render_template("main.html", username=username, meter_id=meter_id)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("signup"))
        if user_manager.add_user(username, password):
            flash("Sign up successful!", "success")
            return redirect(url_for("login"))
        else:
            flash("Username already exists!", "error")
            return redirect(url_for("signup"))
    return render_template("signup.html")

@app.route("/user_meter", methods=["GET"])
def user_meter():
    meter_id = session.get("meter_id")
    usage_value = meter_manager.get_meter_reading(meter_id)
    return render_template("user_meter.html", usage=usage_value)

@app.route("/user_usage", methods=["GET"])
def user_usage():
    return redirect('/dash/')

@app.route("/supplier", methods=["GET", "POST"])
def supplier():
    return render_template("supplier.html")

@app.route("/supplier_result", methods=["POST"])
def supplier_result():
    meter_id = request.form["meter_id"]
    usage_value = meter_manager.get_meter_reading(meter_id)
    return render_template("supplier_result.html", meter_id=meter_id, usage=usage_value)

@app.route("/administrator")
def administrator():
    pass

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(port=5000, debug=True)

