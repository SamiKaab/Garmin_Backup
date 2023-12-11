import garmin as garmin
import influxBackup as influxBackup
import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

def readLocalHR():
    df = pd.read_parquet("heartrate.parquet")
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time")
    df = df.sort_index()
    return df


def writeHRToParquet(client, start_date, stop_date):
    tables = influxBackup.getMeasurement(client, "real_time_heart_rate", "heartRateValue", start_date, stop_date)
    #move to pandas dataframe
    heartrates = [record.values["_value"] for record in tables[0].records]
    time = [record.values["_time"] for record in tables[0].records]
    df = pd.DataFrame({"time": time, "heartrate": heartrates})
    #write to parquet
    df.to_parquet("heartrate.parquet")
    
    



    
if __name__ == "__main__":
    
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=365)
    stop_date  = today - datetime.timedelta(days=1)
    
    # Authenticate with Garmin Connect
    garmin_client = garmin.authenticate(garmin.username, garmin.password)
    
    influxdb_client = influxBackup.getInfuxClient()
    
    hr_data = garmin.get_hr_related_data(garmin_client, start_date, stop_date)
    influxBackup.backupData(influxdb_client, hr_data)
    
    hr_data = garmin.get_hr_data(garmin_client, start_date, stop_date)
    influxBackup.backupData(influxdb_client, hr_data)
    
    data = garmin.get_hrv_data(garmin_client, start_date, stop_date)
    influxBackup.backupData(influxdb_client, data)
    
    data = garmin.get_weight(garmin_client, start_date, stop_date)
    influxBackup.backupData(influxdb_client, data)

    data = garmin.get_VO2Max(garmin_client, start_date, stop_date)
    influxBackup.backupData(influxdb_client, data)

    data = garmin.get_blood_pressures(garmin_client, start_date, stop_date)
    influxBackup.backupData(influxdb_client, data)

    data = garmin.get_garmin_sleep_data(garmin_client, start_date, stop_date)
    influxBackup.backupData(influxdb_client, data)
    
    data = garmin.get_personal_info(garmin_client)
    influxBackup.backupData(influxdb_client, data)
    
    # writeHRToParquet(influxdb_client, start_date, stop_date)
    
    influxdb_client.close()
    
    
    # #calculate the time it takes to run the script
    # start_time = time.perf_counter_ns()
    # df = readLocalHR()
    
    # # plot hr data
    # fig = go.Figure()
    # fig.add_trace(go.Scatter(x=df.index, y=df["heartrate"], mode="lines"))
    # fig.show()
    # length = len(df.index)
    # #calculate the time it takes to run the script
    # end_time = time.perf_counter_ns()
    # print(f"Took {(end_time - start_time)/1e9} seconds to load and plot {length} data points")
    # print(f"Average time per data point: {(end_time - start_time)/1e9/length} seconds")
    # print(f"Read frequency: {length/((end_time - start_time)/1e6)} kHz")
    
    
    

    