from flask import Flask, jsonify
import os

app = Flask(__name__)

METERS_FOLDER = "meter_data"

def read_meter_data(meter_id):

    meter_file = os.path.join(METERS_FOLDER, f"meter_{meter_id}.txt")
    
    with open(meter_file, "r") as f:
        return float(f.read().strip())  # 读取唯一的一行数值


@app.route("/get_meter_data/<meter_id>", methods=["GET"])
def get_meter_data(meter_id):
    """ API: 返回指定 `meter_id` 的当前电表读数 """

    reading = read_meter_data(meter_id)

    return jsonify({
        "meter_id": meter_id,
        "reading_kwh": reading
    })

if __name__ == "__main__":
    app.run(port=5001, debug=True)