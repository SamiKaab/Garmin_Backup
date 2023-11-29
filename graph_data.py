# use dash plotly

# Path: graph_data.py
# from a dictionarry such as :{'BloodPressure': ['diastolic', 'pulse', 'systolic'], 'HeartRateMetrics': ['lastSevenDaysAvgRestingHeartRate', 'restingHeartRate'], 'RealTimeHeartRate': ['heartRateValue'], 'Sleep': ['averageRespirationValue', 'averageSpO2HRSleep', 'averageSpO2Value', 'avgSleepStress', 'awakeCount', 'awakeSleepSeconds', 'calendarDate', 'deepPercentage', 'deepSleepSeconds', 'highestRespirationValue', 'highestSpO2Value', 'lightPercentage', 'lightSleepSeconds', 'lowestRespirationValue', 'lowestSpO2Value', 'overallScore', 'remPercentage', 'remSleepSeconds', 'sleepEndTimestampLocal', 'sleepStartTimestampLocal', 'sleepTimeSeconds'], 'Weight': ['weight'], 'hrv': ['balancedLow', 'balancedUpper', 'lastNightAvg', 'weeklyAvg'], 'vo2max': ['vo2MaxPreciseValue']}
#allow th user to select one or more measurements and one or more fields and plot them

from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd
import influxBackup as influxBackup
from datetime import datetime, timedelta


app = Dash(__name__)

client = influxBackup.getInfuxClient()
measurements = influxBackup.getListOfMeasurements(client)
print(measurements)
# create checkboxes for fields grouped by measurement on the left side of the page
# create a graph on the right side of the page
# when a checkbox is clicked, update the graph
dfs = []


    
app = Dash(__name__)

# create a multi select dropdown for measurements
# createa a multi select dropdown for fields which is populated based on the measurements selected
app.layout = html.Div([
    html.Div([
        dcc.Dropdown(
            id='measurement-dropdown',
            options=[{'label': measurement, 'value': measurement} for measurement in measurements],
            multi=True,
            # set style to make the dropdown fill the entire width of the page
            style={'width': '100%'}
        ), 
        dcc.Dropdown(
            id='field-dropdown',
            multi=True,
            # set style to make the dropdown fill the entire width of the page
            style={'width': '100%'}
        ),
        dcc.DatePickerRange(
            id='date-picker-range',
            start_date=datetime.today().date() - timedelta(days=364),
            end_date=datetime.today().date() - timedelta(days=1)

        )], # center elements and move them next to each other
             style={'display': 'flex', 'align-items': 'center', 'justify-content': 'center', 'width': '100%'}),
    dcc.Graph(id='graph'),
])
# convert dtatetime to date

# set_field_options should be called when the measurements dropdown is changed
@app.callback(
    Output('field-dropdown', 'options'),
    Input('measurement-dropdown', 'value')
)
def set_field_options(selected_measurements):
    fields = []
    for measurement in selected_measurements:
        fields.extend(measurements[measurement])
    
    
    return [{'label': field, 'value': field} for field in fields]


def populate_df(client, selected_measurements, selected_fields,start_date, stop_date):
    
    start = start_date.isoformat("T") + "Z"
    stop = stop_date.isoformat("T") + "Z"
    tables =  influxBackup.get(client, selected_measurements, selected_fields, start, stop)
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

@app.callback(
    Output('graph', 'figure'),
    Input('measurement-dropdown', 'value'),
    Input('field-dropdown', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date')
)
def update_graph(selected_measurements, selected_fields, start_date, stop_date):
    #convert 2023-11-29T14:48:32.833413 to datetime object datetime(2023, 11, 29, 14, 48, 32, 833413)
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    stop_date = datetime.strptime(stop_date, "%Y-%m-%d")
    dfs = populate_df(client, selected_measurements, selected_fields, start_date, stop_date)
    fig = px.line()
    
    
    for df in dfs:
        fig.add_scatter(x=df.index, y=df[df.columns[0]], name=df.columns[0])
        
    # add a range slider
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1d",
                         step="day",
                         stepmode="backward"),
                    dict(count=7,
                         label="1w",
                         step="day",
                         stepmode="backward"),
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=6,
                         label="6m",
                         step="month",
                         stepmode="backward"),
                    dict(count=1,
                         label="1y",
                         step="year",
                         stepmode="backward"),
                    dict(count=3,
                         label="3y",
                         step="year",
                         stepmode="backward"),
                    dict(count=5,
                         label="5y",
                         step="year",
                         stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="date"
        )
    )
    return fig
    




if __name__ == '__main__':
    app.run(debug=True)
