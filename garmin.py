
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)
import datetime
import json
from tqdm import tqdm
import numpy as np
# use plotly
#pip install plotly
import plotly.graph_objects as go
# use influxdb
import os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

username = os.environ.get('garmin_username')
password = os.environ.get('garmin_password')

# Function to authenticate with Garmin Connect
def authenticate(username, password):
    try:
        # Create Garmin client
        client = Garmin(username, password)

        # Authenticate with Garmin Connect
        client.login()

        return client

    except (
        GarminConnectConnectionError,
        GarminConnectAuthenticationError,
        GarminConnectTooManyRequestsError,
    ) as err:
        if hasattr(err, "response") and err.response.status_code == 429:
            # Extract headers from the response
            headers = err.response.headers
            limit = headers.get("X-RateLimit-Limit")
            remaining = headers.get("X-RateLimit-Remaining")
            reset_time = headers.get("X-RateLimit-Reset")

            print(f"Rate limit exceeded. Retry after {reset_time} seconds.")
            quit()
        else:
            print(f"Error occurred: {err}")
            quit()
    except Exception as err:
        print(f"Unknown error occurred: {err}")
        quit()

def garmin_hr_to_hr_related_schema(response):
    
    return{
            "measurement": "HeartRateMetrics",
            "tags": {
                "unit": "bpm",
            },
            "time": response["calendarDate"],
            "fields": {
                "restingHeartRate": response["restingHeartRate"],
                "lastSevenDaysAvgRestingHeartRate": response["lastSevenDaysAvgRestingHeartRate"]
            }
        }
    
def garmin_hr_to_hr_schema(response):
    return [{
            "measurement": "RealTimeHeartRate",
            "tags": {
                "unit": "bpm",
            },
            "time": datetime.datetime.fromtimestamp(t/1000.0),
            "fields": {
                "heartRateValue": hr
            }
        } for t, hr in response["heartRateValues"]]
    
def garmin_weight_to_weight_schema(response):
    return {
        "measurement": "Weight",
        "tags": {
            "unit": "g"
        },
        "time": response["previousDateWeight"]["calendarDate"],
        "fields": {
            "weight": response["previousDateWeight"]["weight"],
        }
    }
    
def garmin_hrv_to_hrv_schema(response):
    
    # one line version of the above
    weeklyAvg = response["hrvSummary"]["weeklyAvg"] if response["hrvSummary"]["weeklyAvg"] != None else None
    lastNightAvg = response["hrvSummary"]["lastNightAvg"] if response["hrvSummary"]["lastNightAvg"] != None else None
    lastNight5MinHigh = response["hrvSummary"]["lastNight5MinHigh"] if response["hrvSummary"] != None else None
    lowUpper = response["hrvSummary"]["baseline"]["lowUpper"] if response["hrvSummary"]["baseline"] != None else None
    balancedLow = response["hrvSummary"]["baseline"]["balancedLow"] if response["hrvSummary"]["baseline"] != None else None
    balancedUpper = response["hrvSummary"]["baseline"]["balancedUpper"] if response["hrvSummary"]["baseline"] != None else None
    markerValue = response["hrvSummary"]["baseline"]["markerValue"] if response["hrvSummary"]["baseline"] != None else None
    status = response["hrvSummary"]["status"] if response["hrvSummary"]["status"] != None else None
    
    
    return {
        "measurement": "hrv",
        "tags": {
            "unit": "ms"
        },
        "time": response["hrvSummary"]["calendarDate"],
        "fields": {
            "weeklyAvg": weeklyAvg,
            "lastNightAvg": lastNightAvg,
            "balancedLow": balancedLow,
            "balancedUpper": balancedUpper,
        }
    }
    
def garmin_vo2max_to_vo2max_schema(response):
    return {
        "measurement": "vo2max",
        "tags": {
            "unit": "ml/kg/min"
        },
        "time": response["generic"]["calendarDate"],
        "fields": {
            "vo2MaxPreciseValue": response["generic"]["vo2MaxPreciseValue"],
        }
    }

def garmin_blood_pressure_to_blood_pressure_schema(response):
    return [{
            "measurement": "BloodPressure",
            "tags": {
                "unit": "mmHg",
            },
            "time": bp["measurements"][0]["measurementTimestampLocal"],
            "fields": {
                "systolic": bp["measurements"][0]["systolic"],
                "diastolic": bp["measurements"][0]["diastolic"],
                "pulse": bp["measurements"][0]["pulse"],
            }
        } for bp in response["measurementSummaries"]]
    
def get_weight(client, start_date, stop_date):
    """
    Get weight data from Garmin Connect
    
    Args:
        client: Garmin client
        start_date: datetime.date object
        stop_date: datetime.date object
    Returns:
        weight_data: list of weight data using the weight_schema
    """
    print("Getting weight data")
    weight_data = []
    for date in tqdm(list(pd.date_range(start_date, stop_date))):
        response = client.get_weigh_ins(date.isoformat(), date.isoformat())
        if response is None:
            print("No weight data for", date.isoformat())
            continue
        else:
            if response["previousDateWeight"]["weight"] is not None:
                weight_data.append(garmin_weight_to_weight_schema(response))
    
    return weight_data

def get_hrv_data(client, start_date, stop_date):
    """
    Get heart rate variability data from Garmin Connect
    
    Args:
        client: Garmin client
        start_date: datetime.date object
        stop_date: datetime.date object
    Returns:
        hrv_data: list of heart rate variability data using the hrv_schema
    """
    print("Getting hrv data")
    hrv_data = []
    for date in tqdm(list(pd.date_range(start_date, stop_date))):
        response = client.get_hrv_data(date.isoformat())
        if response is None:
            print("No heart rate variability data for", date.isoformat())
            continue
        else:
            hrv_data.append(garmin_hrv_to_hrv_schema(response))
    return hrv_data

def get_hr_related_data(client, start_date, stop_date):
    """
    Get heart rate related data from Garmin Connect
    
    Args:
        client: Garmin client
        start_date: datetime.date object
        stop_date: datetime.date object
    Returns:
        hr_data: list of heart rate related data using the hr_adj_schema
    """
    print("Getting heart rate related data")
    hr_data = []
    for date in tqdm(list(pd.date_range(start_date, stop_date))):
        response = client.get_heart_rates(date.isoformat())
        if response is None:
            print("No heart rate data for", date.isoformat())
            continue
        else:
            hr_data.append(garmin_hr_to_hr_related_schema(response))
    return hr_data

def get_hr_data(client, start_date, stop_date):
    """
    Get heart rate data from Garmin Connect
    
    Args:
        client: Garmin client
        start_date: datetime.date object
        stop_date: datetime.date object
    Returns:
        hr_data: list of heart rate data using the hr_schema
    """
    print("Getting heart rate data")
    hr_data = []
    for date in tqdm(list(pd.date_range(start_date, stop_date))):
        response = client.get_heart_rates(date.isoformat())
        # print(response)
        if response is None:
            print("No heart rate data for", date.isoformat())
            continue
        elif response["heartRateValues"] is not None:
            hrs = garmin_hr_to_hr_schema(response)
            for hr in hrs:
                hr_data.append(hr)
    return hr_data

def get_VO2Max(client, start_date, stop_date):
    """
    Get VO2Max data from Garmin Connect
    
    Args:
        client: Garmin client
        start_date: datetime.date object
        stop_date: datetime.date object
    Returns:
        vo2max_data: list of VO2Max data using the vo2max_schema
    """
    print("Getting VO2Max data")
    vo2max_data = []
    for date in tqdm(list(pd.date_range(start_date, stop_date))):
        response = client.get_max_metrics(date.isoformat())
        # print(response)
        if response is None or len(response) == 0:
            print("No VO2Max data for", date.isoformat())
            continue
        else:
            vo2max_data.append(garmin_vo2max_to_vo2max_schema(response[0]))
    return vo2max_data
    
def get_activities(client, start_date, stop_date):
    """
    Get activities data from Garmin Connect
    
    Args:
        client: Garmin client
        start_date: datetime.date object
        stop_date: datetime.date object
    Returns:
        activities_data: list of activities data using the activities_schema
    """
    print("Getting activities data")
    activities_data = []
    # for date in tqdm(list(pd.date_range(start_date, stop_date))):
    response = client.get_activities_by_date(start_date.isoformat(), stop_date.isoformat())
    print(response)
    #     if response is None:
    #         print("No activities data for", date.isoformat())
    #         continue
    #     else:
    #         activities_data.append(garmin_activities_to_activities_schema(response))
    # return activities_data
    
def get_blood_pressures(client, start_date, stop_date):
    """
    Get blood pressure data from Garmin Connect
    
    Args:
        client: Garmin client
        start_date: datetime.date object
        stop_date: datetime.date object
    Returns:
        blood_pressure_data: list of blood pressure data using the blood_pressure_schema
    """
    print("Getting blood pressure data")
    response = client.get_blood_pressure(start_date.isoformat(), stop_date.isoformat())
    blood_pressure_data = None
    if response is None or len(response) == 0:
        print("No blood pressure data")
    else:
        blood_pressure_data = garmin_blood_pressure_to_blood_pressure_schema(response)
    return blood_pressure_data
#{data:values ....}
def get_garmin_sleep_data(client, start_date, stop_date):
    """
    Get sleep data from Garmin Connect
    
    Args:
        client: Garmin client
        start_date: datetime.date object
        stop_date: datetime.date object
    Returns:
        sleep_data: list of sleep data using the sleep_schema
    """
    print("Getting sleep data")
    sleep_data = []
    for date in tqdm(list(pd.date_range(start_date, stop_date))):
        # convert date from: 2023-11-24T00%3A00%3A00 to yyyy-mm-dd
        date = date.date()
        response = client.get_sleep_data(date.isoformat())
        # print(response)
        if response is None:
            print("No sleep data for", date.isoformat())
            continue
        else:
            sleep_data.append(garmin_sleep_to_sleep_schema(response))
    return sleep_data

def garmin_sleep_to_sleep_schema(response):
    try:
        averageSpO2Value = response["dailySleepDTO"]["averageSpO2Value"]
        lowestSpO2Value = response["dailySleepDTO"]["lowestSpO2Value"]
        highestSpO2Value = response["dailySleepDTO"]["highestSpO2Value"]
        averageSpO2HRSleep = response["dailySleepDTO"]["averageSpO2HRSleep"]
    except:
        averageSpO2Value = None
        lowestSpO2Value = None
        highestSpO2Value = None
        averageSpO2HRSleep = None
    try:
        averageRespirationValue = response["dailySleepDTO"]["averageRespirationValue"]
        lowestRespirationValue = response["dailySleepDTO"]["lowestRespirationValue"]
        highestRespirationValue = response["dailySleepDTO"]["highestRespirationValue"]
    except:
        averageRespirationValue = None
        lowestRespirationValue = None
        highestRespirationValue = None
    try:
        awakeCount = response["dailySleepDTO"]["awakeCount"]
    except:
        awakeCount = None
    try:
        avgSleepStress = response["dailySleepDTO"]["avgSleepStress"]
    except:
        avgSleepStress = None
    try:
        overallScore = response["dailySleepDTO"]["sleepScores"]["overall"]["value"]
    except:
        overallScore = None
    try:
        remPercentage = response["dailySleepDTO"]["sleepScores"]["remPercentage"]["value"]
    except:
        remPercentage = None
    try:
        lightPercentage = response["dailySleepDTO"]["sleepScores"]["lightPercentage"]["value"]
    except:
        lightPercentage = None
    try:
        deepPercentage = response["dailySleepDTO"]["sleepScores"]["deepPercentage"]["value"]
    except:
        deepPercentage = None
        
        
    return {
        "measurement": "Sleep",
        "time": response["dailySleepDTO"]["calendarDate"],
        "fields": {
            'calendarDate': response["dailySleepDTO"]["calendarDate"],
            'sleepTimeSeconds': response["dailySleepDTO"]["sleepTimeSeconds"],
            'sleepStartTimestampLocal': response["dailySleepDTO"]["sleepStartTimestampLocal"],
            'sleepEndTimestampLocal': response["dailySleepDTO"]["sleepEndTimestampLocal"],
            'deepSleepSeconds': response["dailySleepDTO"]["deepSleepSeconds"],
            'lightSleepSeconds': response["dailySleepDTO"]["lightSleepSeconds"],
            'remSleepSeconds': response["dailySleepDTO"]["remSleepSeconds"],
            'awakeSleepSeconds': response["dailySleepDTO"]["awakeSleepSeconds"],
            'averageSpO2Value': averageSpO2Value,
            'lowestSpO2Value': lowestSpO2Value,
            'highestSpO2Value': highestSpO2Value,
            'averageSpO2HRSleep': averageSpO2HRSleep,
            'averageRespirationValue': averageRespirationValue,
            'lowestRespirationValue': lowestRespirationValue,
            'highestRespirationValue': highestRespirationValue,
            'awakeCount': awakeCount,
            'avgSleepStress': avgSleepStress,
            'overallScore': overallScore,
            'remPercentage': remPercentage,  
            'lightPercentage': lightPercentage, 
            'deepPercentage': deepPercentage, 
        }
    }

def sendWeightToObsidinan(data):
    for d in data:
        # write weight to file and create it if does not exist
        with open(f"G:\\My Drive\\nean\\Health\\{d['time']}.md", "a+") as f:
            weight = float(d['fields']['weight']) / 1000
            line = f"#weight:{weight}\n"
            # check if line already exists
            weight_exists = False
            for l in f.readlines():
                print(l)
                if "weight" in l:
                    weight_exists = True
            if not weight_exists:
                f.write(line)

def sendSleepToObsidinan(data):
    for d in data:
        with open(f"G:\\My Drive\\nean\\Health\\{d['time']}.md", "a+") as f:
            sleep_score = d['fields']['overallScore']
            line = f"#sleep_score:{sleep_score}\n"
            # check if line already exists
            if "sleep_score" not in f.readlines():
                f.write(line)                
                
def get_personal_info(client):
    """
    Get personal info from Garmin Connect
    
    Args:
        client: Garmin client
    Returns:
        personal_info: list of personal info using the personal_info_schema
    """
    garmin_connect_user_settings_url = (
            "/userprofile-service/userprofile/user-settings"
        )
    response = client.connectapi(garmin_connect_user_settings_url)
    print("Getting personal info")
    if response is None or len(response) == 0:
        print("No personal info data")
    else:
        personal_info = [garmin_personal_info_to_personal_info_schema(response)]
    return personal_info                

# {'id': 109015146, 'userData': {'gender': 'MALE', 'weight': 63999.0, 'height': 170.0, 'timeFormat': 'time_twenty_four_hr', 'birthDate': '1997-07-05', 'measurementSystem': 'metric', 'activityLevel': 6, 'handedness': 'RIGHT', 'powerFormat': {'formatId': 30, 'formatKey': 'watt', 'minFraction': 0, 'maxFraction': 0, 'groupingUsed': True, 'displayFormat': None}, 'heartRateFormat': {'formatId': 21, 'formatKey': 'bpm', 'minFraction': 0, 'maxFraction': 0, 'groupingUsed': False, 'displayFormat': None}, 'firstDayOfWeek': {'dayId': 3, 'dayName': 'monday', 'sortOrder': 3, 'isPossibleFirstDay': True}, 'vo2MaxRunning': 52.0, 'vo2MaxCycling': None, 'lactateThresholdSpeed': 0.341599988937378, 'lactateThresholdHeartRate': None, 'diveNumber': None, 'intensityMinutesCalcMethod': 'AUTO', 'moderateIntensityMinutesHrZone': 3, 'vigorousIntensityMinutesHrZone': 4, 'hydrationMeasurementUnit': 'milliliter', 'hydrationContainers': [{'name': None, 'volume': 600, 'unit': 'milliliter'}, {'name': None, 'volume': 1000, 'unit': 'milliliter'}, {'name': None, 'volume': 1500, 'unit': 'milliliter'}], 'hydrationAutoGoalEnabled': True, 'firstbeatMaxStressScore': None, 'firstbeatCyclingLtTimestamp': None, 'firstbeatRunningLtTimestamp': 1069450064, 'thresholdHeartRateAutoDetected': True, 'ftpAutoDetected': None, 'trainingStatusPausedDate': None, 'weatherLocation': {'useFixedLocation': None, 'latitude': None, 'longitude': None, 'locationName': None, 'isoCountryCode': None, 'postalCode': None}, 'golfDistanceUnit': 'statute_us', 'golfElevationUnit': None, 'golfSpeedUnit': None, 'externalBottomTime': None, 'availableTrainingDays': ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'], 'preferredLongTrainingDays': []}, 'userSleep': {'sleepTime': 77400, 'defaultSleepTime': False, 'wakeTime': 19800, 'defaultWakeTime': False}, 'connectDate': None, 'sourceType': None, 'userSleepWindows': [{'sleepWindowFrequency': 'SUNDAY', 'startSleepTimeSecondsFromMidnight': 77400, 'endSleepTimeSecondsFromMidnight': 19800}, {'sleepWindowFrequency': 'MONDAY', 'startSleepTimeSecondsFromMidnight': 77400, 'endSleepTimeSecondsFromMidnight': 19800}, {'sleepWindowFrequency': 'TUESDAY', 'startSleepTimeSecondsFromMidnight': 77400, 'endSleepTimeSecondsFromMidnight': 19800}, {'sleepWindowFrequency': 'WEDNESDAY', 'startSleepTimeSecondsFromMidnight': 77400, 'endSleepTimeSecondsFromMidnight': 19800}, {'sleepWindowFrequency': 'THURSDAY', 'startSleepTimeSecondsFromMidnight': 77400, 'endSleepTimeSecondsFromMidnight': 19800}, {'sleepWindowFrequency': 'FRIDAY', 'startSleepTimeSecondsFromMidnight': 77400, 'endSleepTimeSecondsFromMidnight': 19800}, {'sleepWindowFrequency': 'SATURDAY', 'startSleepTimeSecondsFromMidnight': 77400, 'endSleepTimeSecondsFromMidnight': 19800}, {'sleepWindowFrequency': 'DAILY', 'startSleepTimeSecondsFromMidnight': 77400, 'endSleepTimeSecondsFromMidnight': 19800}]}
def garmin_personal_info_to_personal_info_schema(response):
    return {
        "measurement": "PersonalInfo",
        "fields": {
            "gender": response["userData"]["gender"],
            "weight": response["userData"]["weight"],
            "height": response["userData"]["height"],
            "birthDate": response["userData"]["birthDate"],
            "handness": response["userData"]["handedness"]
        }
    }

                
if __name__ == "__main__":
    # # # # # # # # # client = authenticate(username, password)
    # # # # # # # # # today = datetime.date.today()
    # # # # # # # # # # # 2 years ago
    # # # # # # # # # start_date = today - datetime.timedelta(days=50)
    # # # # # # # # # stop_date  = today - datetime.timedelta(days=1)
    # # data = get_hr_data(client, start_date, stop_date)
    # data = get_weight(client, start_date, stop_date)
    # # data = get_hrv_data(client, start_date, stop_date)
    # # data = get_VO2Max(client, start_date, stop_date)
    # # data = get_activities(client, start_date, stop_date)
    # data = get_blood_pressures(client, start_date, stop_date)
    # data = get_garmin_sleep_data(client, start_date, stop_date)
    # data = get_personal_info(client)
    # print(data)
    # [print(d) for d in data]
    
    # # # write to json file
    # # with open("blood_pressure.json", "w") as f:
    # #     json.dump(data, f)
    
    # read from json file
    with open("blood_pressure.json", "r") as f:
        data = json.load(f)
        
    

    # plot the blood pressure data with plotly. systolic pressure on the y axis and diastolic pressure on the x axis.
    # draw the box around the normal range, which is 120/80.
    
    systolic = [d["fields"]["systolic"] for d in data]
    diastolic = [d["fields"]["diastolic"] for d in data]
    date_time = [d["time"] for d in data]
    

    
    
    fig = go.Figure()
    
    # # draw a rounded rectangle 
    # for i in range(len(systolic)):
    #     fig.add_shape(type="rect",
    #         x0=date_time[i], y0=diastolic[i], x1=date_time[i], y1=systolic[i],
    #         line=dict(color="red", width=10),
    #         fillcolor="red",
    #         opacity=1,
    #         layer="below"
    #     )
            
        
        
    
    # fig.add_trace(go.Scatter(x=date_time, y=[0 for _ in range(len(date_time))], mode="lines", line=dict(color="white", width=0.5)))
    
        
        
    # fig.show()
    
    
    colors = ["#3498db", "#1FC253", "#ff9800", "#e74c3c"]



    # create a box around the normal range
    fig.add_shape(type="rect",
        x0=0, y0=0, x1=100, y1=200,
        line=dict(color=colors[3]),#red
        fillcolor=colors[3],
        opacity=1,
        layer="below"
    )
    fig.add_shape(type="rect",
        x0=0, y0=0, x1=90, y1=140,
        line=dict(color=colors[2]),#orange
        fillcolor=colors[2],
        opacity=1,
        layer="below"
    )
    fig.add_shape(type="rect",
        x0=0, y0=0, x1=80, y1=120,
        line=dict(color=colors[1]),#green
        fillcolor=colors[1],
        opacity=1,
        layer="below"
    )
    fig.add_shape(type="rect",
        x0=0, y0=0, x1=60, y1=90,
        line=dict(color=colors[0]),#blue
        fillcolor=colors[0],
        opacity=1,
        layer="below"
    )
    # plot the systolic and diastolic data add date_time as marker text. marker color is black, 0.5 thinkness
    fig.add_trace(go.Scatter(x=diastolic, y=systolic, mode="markers", marker=dict(color="black", size=5), text=date_time))
    # add axis labels
    fig.update_layout(
        xaxis_title="Diastolic",
        yaxis_title="Systolic",
        font=dict(
            family="Courier New, monospace",
            size=18,
            color="RebeccaPurple"
        )
    )
    
    # fig.add_trace(go.Scatter(x=diastolic, y=systolic, mode="lines", line=dict(color="black", width=0.5)))

    # # compute average location of the data points
    # avg_systolic = np.mean(systolic)
    # avg_diastolic = np.mean(diastolic)
    
 
    # # draw circle around ellipse that contains 95% of the data
    
    # # compute covariance matrix
    # cov = np.cov(systolic, diastolic)
    # # compute eigenvalues and eigenvectors
    # eigenvalues, eigenvectors = np.linalg.eig(cov)
    # # compute the angle of the ellipse
    # angle = np.arctan(eigenvectors[1][0]/eigenvectors[0][0])
    # # compute the length of the major and minor axis
    # major_axis = np.sqrt(eigenvalues[0])
    # minor_axis = np.sqrt(eigenvalues[1])
    # # compute the ellipse
    # t = np.linspace(0, 2*np.pi, 100)
    # x = major_axis * np.cos(t)
    # y = minor_axis * np.sin(t)
    # # rotate the ellipse
    # x_rotated = x*np.cos(angle) - y*np.sin(angle)
    # y_rotated = x*np.sin(angle) + y*np.cos(angle)
    # # compute the center of the ellipse
    # center = np.array([avg_diastolic, avg_systolic])
    # # compute the ellipse
    # ellipse = np.array([x_rotated, y_rotated]).T + center
    # # plot the ellipse
    # # fig.add_trace(go.Scatter(x=ellipse[:,0], y=ellipse[:,1], mode="lines", line=dict(color="red", width=1)))
    # fig.add_shape(type="path", 
    #               path="M " + " L ".join([str(x) + " " + str(y) for x, y in ellipse]), 
    #               line=dict(color="grey", width=1),
    #                       fillcolor="grey",
    #                       opacity=0.2)
    
    # set axis range
    fig.update_xaxes(range=[0, 100])
    fig.update_yaxes(range=[0, 200])
    fig.update_yaxes(dtick=20)
    fig.update_xaxes(dtick=20)
    # square the axis
    fig.update_layout(width=800, height=800)
    # grid off
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.show()
    