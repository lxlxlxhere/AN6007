from flask import Flask, jsonify, request
import os
import signal
import threading
import time
import random

app = Flask(__name__)
METERS_FOLDER = "meter_data"
acceptAPI = True  # 控制 API 是否允许访问

def read_meter_data(meter_id):

    meter_file = os.path.join(METERS_FOLDER, f"meter_{meter_id}.txt")

    with open(meter_file, "r") as f:
        return float(f.read().strip())


@app.route("/get_meter_data/<meter_id>", methods=["GET"])
def get_meter_data(meter_id):

    reading = read_meter_data(meter_id)

    global acceptAPI
    if not acceptAPI:
            return jsonify({
                "meter_id": meter_id,
                "reading_kwh": "Server under maintenance..."
            })

    return jsonify({
        "meter_id": meter_id,
        "reading_kwh": reading
    })

def batchJobs():

    threads = []
    for i in range(10):  # 启动 10 个任务
        t = threading.Thread(target=job, args=(i, random.randint(2, 6)))
        threads.append(t)
        t.start()
    
    for each in threads:
        each.join()

def job(no, dur):

    print(f"Job {no} starting, will complete in {dur} sec")
    time.sleep(dur)
    print(f"Job {no} exiting, time taken {dur} sec")

@app.route('/stop_server', methods=['GET'])
def stop_server():

    global acceptAPI
    acceptAPI = False  # 关闭 API，防止新请求进入
    print("Server is pausing...")

    batchJobs()  # 运行批处理任务

    acceptAPI = True  # 任务完成后，恢复 API 访问
    print("Server is processing...")

    return jsonify({"success": True, "message": "Server pausing."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)