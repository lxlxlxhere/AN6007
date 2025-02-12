import requests
import pandas as pd
from datetime import datetime, timedelta

METER_API_URL = "http://127.0.0.1:5001/get_meter_data/"
DAILY_CSV_FILE = "electricity_data_daily.csv"
TODAY_CSV_FILE = "electricity_data_today.csv"

class MeterManager:
    def get_meter_reading(self, meter_id):
        response = requests.get(f"{METER_API_URL}{meter_id}")
        data = response.json()
        return (data.get("reading_kwh", 0))

    def get_user_usage(self, meter_id):
        df_daily = pd.read_csv(DAILY_CSV_FILE)
        df_today = pd.read_csv(TODAY_CSV_FILE)
        
        now = datetime.now()
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        last_weekend = (now - timedelta(days=now.weekday() + 1)).strftime("%Y-%m-%d")
        last_month_end = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
        prev_month_end = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
        
        df_valid = df_today.dropna(subset=[meter_id])
        recent_half_hour_usage = df_valid[meter_id].iloc[-1] - df_valid[meter_id].iloc[-2]

        today_usage = self.get_meter_reading(meter_id) - df_daily[df_daily["date"] == yesterday][meter_id].values[0]
        week_usage = self.get_meter_reading(meter_id) - df_daily[df_daily["date"] == last_weekend][meter_id].values[0]
        month_usage = self.get_meter_reading(meter_id) - df_daily[df_daily["date"] == last_month_end][meter_id].values[0]
        last_month_usage = df_daily[df_daily["date"] == last_month_end][meter_id].values[0] - df_daily[df_daily["date"] == prev_month_end][meter_id].values[0]
        
        return {
            "recent_half_hour_usage": round(recent_half_hour_usage, 2),
            "today_usage": round(today_usage, 2),
            "week_usage": round(week_usage, 2),
            "month_usage": round(month_usage, 2),
            "last_month_usage": round(last_month_usage, 2)
        }