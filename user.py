# v2
import json
import os

class UserManager:
    USER_DATA_FILE = "users.json"
    
    def __init__(self):
        self.users = self.load_users()
        print("loading users...")
    
    def load_users(self):
        if os.path.exists(self.USER_DATA_FILE):
            with open(self.USER_DATA_FILE, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}
    
    def save_users(self):
        with open(self.USER_DATA_FILE, "w") as f:
            json.dump(self.users, f, indent=4)
    
    def generate_meter_id(self):
        last_id = 100000001
        if self.users:
            existing_ids = [int(user["meter_id"]) for user in self.users.values()]
            last_id = max(existing_ids) + 1 if existing_ids else last_id
        return str(last_id)
    
    def add_user(self, username, password):
        if username in self.users:
            return False
        meter_id = self.generate_meter_id()
        self.users[username] = {"password": password, "meter_id": meter_id}
        self.save_users()
        return True
    
    def validate_user(self, username, password):
        return username in self.users and self.users[username]["password"] == password
    
    def get_meter_id(self, username):
        return self.users.get(username, {}).get("meter_id", "N/A")
