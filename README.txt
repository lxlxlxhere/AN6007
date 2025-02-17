The execution order is as follows:

1. store_readings.py (include generating test data)
2. mock_meter.py (include generator and API)
3. app.py

store_readings.py includes:
    1. create test data
    2. restore data to dic from csv
    3. archive while server stopped