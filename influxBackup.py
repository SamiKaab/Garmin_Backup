import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
from tqdm import tqdm

from datetime import datetime, timedelta
import plotly.graph_objects as go

token = "A49iA1gHiDq0px7bGAig6ldxcWy9f-eYx0Dw3Ir4FHq4sr2_mCj1ZV3QThGOW6HcCg2mx0l2l9V8h3rEoZBV2w=="
org = "garmin_ws"
url = "http://localhost:8086"
bucket="garmin"




def getInfuxClient(url=url, token=token):
    client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
    return client

def deleteData(client, startDate, stopDate, measurement, bucket=bucket, org=org):
    delete_api = client.delete_api()
    delete_api.delete(startDate, stopDate, f'_measurement="{measurement}"', bucket=bucket, org=org)
    print("Data deleted")
    
# def deleteDatawithField(client, startDate, stopDate, measurement, field, bucket=bucket, org=org):
#     delete_api = client.delete_api()
#     query = f'_measurement="{measurement}" AND _field="{field}"'
#     print(query)
#     delete_api.delete(startDate, stopDate, query, bucket=bucket, org=org)
#     print("Data deleted")
    
def checkIfExists(client, data_point, bucket=bucket, org=org):
    # check if data_point already exists. use _measurement, _field, _time, _value
    query_api = client.query_api()
    # check if data already exists from forever ago
    query = f'from(bucket: "{bucket}")\
        |> range(start: 0)\
        |> filter(fn: (r) => r._measurement == "{data_point["measurement"]}")\
        |> filter(fn: (r) => r.userProfilePK == "{data_point["tags"]["userProfilePK"]}")\
        |> filter(fn: (r) => r._time == "{data_point["time"]}")'
        
    tables = query_api.query(query)
    print(tables)
    if tables and len(tables) > 0 and len(tables[0].records) > 0:
        return True
    else:
        return False
    
def backupData(client, data, bucket=bucket, org=org):
    write_api = client.write_api(write_options=SYNCHRONOUS)
    #check if data already exists
    print("Backing up data")
    for data_point in tqdm(data):
        write_api.write(bucket, org, data_point)
        # dataPointExists = checkIfExists(client, data_point)
        # if not dataPointExists:
        #     write_api.write(bucket, org, data_point)
        # else:
        #     print("Data point already exists")

def getListOfMeasurements(client, bucket=bucket, org=org):
    query_api = client.query_api()
    query = f'from(bucket: "{bucket}")\
        |> range(start: 0)'
    tables = query_api.query(query)
    data = {}
    for table in tables:
        measurement = table.records[0].values["_measurement"]
        field = table.records[0].values["_field"]
        if measurement not in data:
            data[measurement] = []
        data[measurement].append(field)
    return data

def get(client, measurements, fields, startDate, stopDate, bucket=bucket, org=org):
    query_api = client.query_api()
    query = f'from(bucket: "{bucket}")|> range(start: {startDate}, stop: {stopDate})'
    query += f'|> filter(fn: (r) => r._measurement == "{measurements[0]}"'
    if len(measurements) > 1:
        for measurement in measurements[1:]:
            query += f' or r._measurement == "{measurement}"'
    query += ')'
    query += f'|> filter(fn: (r) => r._field == "{fields[0]}"'
    if len(fields) > 1:
        for field in fields[1:]:
            query += f' or r._field == "{field}"'
            
    query += ')'
    print(query)
    tables = query_api.query(query)
    return tables

def populate_df(client, selected_measurements, selected_fields):
    start = datetime.today() - timedelta(days=365)
    stop = datetime.today() - timedelta(days=1)
    start = start.isoformat("T") + "Z"
    stop = stop.isoformat("T") + "Z"
    tables =  get(client, selected_measurements, selected_fields, start, stop)
    data = {}
    timestamps = {}
    for table in tables:
        sub_data = []
        sub_timestamps = []
        field = table.records[0].values["_field"]
        for record in table.records:
            sub_data.append(record.values["_value"])
            sub_timestamps.append(record.values["_time"])
        data[field] = sub_data
        timestamps[field] = sub_timestamps
    dfs = []
    for field in data:
        df = pd.DataFrame({"time": timestamps[field], field: data[field]})
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time")
        df = df.sort_index()
        dfs.append(df)
    return dfs

            
if __name__ == "__main__":
    client = getInfuxClient()
    # start = datetime.datetime(2021, 1, 1, 0, 0, 0, 0).isoformat("T") + "Z"
    # stop = datetime.datetime.now().isoformat("T") + "Z"
    # deleteData(client, start, stop, "HeartRateMetrics")
    # deleteData(client, start, stop, "RealTimeHeartRate")
    # deleteData(client, start, stop, "Weight")
    # deleteData(client, start, stop, "HRV")
    # deleteData(client, start, stop, "VO2Max")
    # deleteData(client, start, stop, "BloodPressure")
    
    # print(getListOfMeasurements(client))
    start = datetime.today() - timedelta(days=365)
    stop = datetime.today() - timedelta(days=1)
    start = start.isoformat("T") + "Z"
    stop = stop.isoformat("T") + "Z"
    # {'BloodPressure': ['diastolic', 'pulse', 'systolic'], 'HeartRateMetrics': ['lastSevenDaysAvgRestingHeartRate', 'restingHeartRate'], 'RealTimeHeartRate': ['heartRateValue'], 'Sleep': ['averageRespirationValue', 'averageSpO2HRSleep', 'averageSpO2Value', 'avgSleepStress', 'awakeCount', 'awakeSleepSeconds', 'calendarDate', 'deepPercentage', 'deepSleepSeconds', 'highestRespirationValue', 'highestSpO2Value', 'lightPercentage', 'lightSleepSeconds', 'lowestRespirationValue', 'lowestSpO2Value', 'overallScore', 'remPercentage', 'remSleepSeconds', 'sleepEndTimestampLocal', 'sleepStartTimestampLocal', 'sleepTimeSeconds'], 'Weight': ['weight'], 'hrv': ['balancedLow', 'balancedUpper', 'lastNightAvg', 'weeklyAvg'], 'vo2max': ['vo2MaxPreciseValue']}
    # tables = get(client, ["HeartRateMetrics", "BloodPressure"], ["restingHeartRate", "systolic", "diastolic"], start, stop)
    # data = {}
    # timestamps = {}
    # for table in tables:
    #     sub_data = []
    #     sub_timestamps = []
    #     field = table.records[0].values["_field"]
    #     for record in table.records:
    #         sub_data.append(record.values["_value"])
    #         sub_timestamps.append(record.values["_time"])
    #     data[field] = sub_data
    #     timestamps[field] = sub_timestamps
    
    # dfs = []
    # for field in data:
    #     df = pd.DataFrame({"time": timestamps[field], field: data[field]})
    #     df["time"] = pd.to_datetime(df["time"])
    #     df = df.set_index("time")
    #     df = df.sort_index()
    #     dfs.append(df)
    
    dfs = populate_df(client, ["HeartRateMetrics", "BloodPressure"], ["restingHeartRate", "systolic", "diastolic"])
        
    #plot the data
    fig = go.Figure()
    for df in dfs:
        fig.add_trace(go.Scatter(x=df.index, y=df[df.columns[0]], mode="lines", name=df.columns[0]))
    fig.show()
    client.close()