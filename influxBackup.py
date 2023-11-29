import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
from tqdm import tqdm

import datetime

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

def getMeasurement(client, measurement, field, startDate, stopDate, bucket=bucket, org=org):
    query_api = client.query_api()
    query = f'from(bucket: "{bucket}")\
        |> range(start: {startDate}, stop: {stopDate})\
        |> filter(fn: (r) => r._measurement == "{measurement}")\
        |> filter(fn: (r) => r._field == "{field}")'
    tables = query_api.query(query)
    return tables
            
if __name__ == "__main__":
    client = getInfuxClient()
    start = datetime.datetime(2021, 1, 1, 0, 0, 0, 0).isoformat("T") + "Z"
    stop = datetime.datetime.now().isoformat("T") + "Z"
    deleteData(client, start, stop, "HeartRateMetrics")
    deleteData(client, start, stop, "RealTimeHeartRate")
    deleteData(client, start, stop, "Weight")
    deleteData(client, start, stop, "HRV")
    deleteData(client, start, stop, "VO2Max")
    deleteData(client, start, stop, "BloodPressure")
    # deleteDatawithField(client, start, stop, "real_time_heart_rate", "heartRateValues", bucket=bucket, org=org)