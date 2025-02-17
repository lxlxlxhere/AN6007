import requests
import pandas as pd
from datetime import datetime, timedelta

METER_API_URL = "http://127.0.0.1:5001/get_meter_data/"
METER_TODAY_API = "http://127.0.0.1:5002/get_today_data/"
METER_DAILY_API = "http://127.0.0.1:5002/get_daily_data/"

class MeterManager:
    def get_meter_reading(self, meter_id):
        response = requests.get(f"{METER_API_URL}{meter_id}")
        data = response.json()
        return data.get("reading_kwh", 0)

    def get_past_date(self):
        now = datetime.now()
        yesterday = (now - timedelta(days=1)).strftime("%Y%m%d")  # 昨天
        last_weekend = (now - timedelta(days=now.weekday() + 1)).strftime("%Y%m%d")  # 上周末（上周日）
        last_month_end = (now.replace(day=1) - timedelta(days=1)).strftime("%Y%m%d")  # 上月底
        prev_month_end = (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y%m%d")  # 上上月底
        return yesterday, last_weekend, last_month_end, prev_month_end

    def get_meter_data(self, meter_id, api_url, date=None):
        url = f"{api_url}{meter_id}"
        if date:
            url += f"?date={date}"
        response = requests.get(url)
        data = response.json()
        return data.get("reading", 0)

    def get_user_usage(self, meter_id):
        yesterday, last_weekend, last_month_end, prev_month_end = self.get_past_date()

        current_reading = self.get_meter_reading(meter_id)

        response = requests.get(f"{METER_TODAY_API}{meter_id}")
        today_data = response.json()

        if "latest_reading" not in today_data:
            return {"error": "No today data found for this meter_id"}

        latest_reading = today_data["latest_reading"]

        recent_half_hour_usage = max(0, current_reading - latest_reading)

        yesterday_reading = self.get_meter_data(meter_id, METER_DAILY_API, yesterday)
        last_weekend_reading = self.get_meter_data(meter_id, METER_DAILY_API, last_weekend)
        last_month_end_reading = self.get_meter_data(meter_id, METER_DAILY_API, last_month_end)
        prev_month_end_reading = self.get_meter_data(meter_id, METER_DAILY_API, prev_month_end)

        today_usage = max(0, current_reading - yesterday_reading)
        week_usage = max(0, current_reading - last_weekend_reading)
        month_usage = max(0, current_reading - last_month_end_reading)
        last_month_usage = max(0, last_month_end_reading - prev_month_end_reading)

        return {
            "recent_half_hour_usage": round(recent_half_hour_usage, 8),
            "today_usage": round(today_usage, 8),
            "week_usage": round(week_usage, 8),
            "month_usage": round(month_usage, 8),
            "last_month_usage": round(last_month_usage, 8)
        }