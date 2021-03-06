import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as graph
from dash.dependencies import Input, Output
import numpy as np
import pandas as pd
from os.path import isfile
from datetime import date
import plotly.express as px
from datetime import datetime as dt

GlobalURL = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/"
fileNamePickle = "allData.pkl"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
usaURL = "https://github.com/nytimes/covid-19-data/blob/master/us-counties.csv/"
ImportPolicy = pd.read_csv("Covid19-Imp.csv")
print(ImportPolicy)

tickFont = {'size': 12, 'color': "rgb(30,30,30)", 'family': "Apple Chancery, cursive"}
today = date.today()

def __loadData_GLOB(fileName, columnName):
    agg_dict = {columnName: sum, 'Lat': np.median, 'Long': np.median}
    data = pd.read_csv(GlobalURL + fileName, engine="c") \
        .rename(columns={'Country/Region': 'Country'}) \
        .melt(id_vars=['Country', 'Province/State', 'Lat', 'Long'], var_name='date', value_name=columnName) \
        .astype({'date': 'datetime64[ns]', columnName: 'Int64'}, errors='ignore')
    data = data.groupby(['Country', 'date']).agg(agg_dict).reset_index()
    data['Province/State'] = '<all>'
    return pd.concat([data])


def __loadData_US(fileName, columnName):
    id_vars = ['Country', 'Province/State', 'Lat', 'Long']
    agg_dict = {columnName: sum, 'Lat': np.median, 'Long': np.median}
    data = pd.read_csv(GlobalURL + fileName, engine="c", low_memory=False, sep=",", encoding="utf-8").iloc[:, 6:]
    if 'Population' in data.columns:
        data = data.drop('Population', axis=1)
    data = data \
        .drop('Combined_Key', axis=1) \
        .rename(columns={'Country_Region': 'Country', 'Province_State': 'Province/State', 'Long_': 'Long'}) \
        .melt(id_vars=id_vars, var_name='date', value_name=columnName) \
        .astype({'date': 'datetime64[ns]', columnName: 'Int64'}, errors='ignore') \
        .groupby(['Country', 'Province/State', 'date']).agg(agg_dict).reset_index()
    return data



def refreshData():
    data_GLOB = __loadData_GLOB("time_series_covid19_confirmed_global.csv", "CumConfirmed") \
        .merge(__loadData_GLOB("time_series_covid19_deaths_global.csv", "CumDeaths"))
    data_US = __loadData_US("time_series_covid19_confirmed_US.csv", "CumConfirmed") \
        .merge(__loadData_US("time_series_covid19_deaths_US.csv", "CumDeaths"))

    data = pd.concat([data_GLOB, data_US])
    data.to_pickle(fileNamePickle)
    return data


def allData():
    if not isfile(fileNamePickle):
        refreshData()
    allData = pd.read_pickle(fileNamePickle)
    return allData


countries = allData()['Country'].unique()
countries.sort()

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(
    style={'font-family': "Apple Chancery, cursive"},
    children=[
        html.H1('Case history of Covid19 at Earth'),
        html.Div(className="row", children=[
            html.Div(className="three columns", children=[
                html.H5('Country'),
                dcc.Dropdown(
                    id='country',
                    options=[{'label': c, 'value': c} for c in countries],
                    value='US'
                )
            ]),
            html.Div(className="three columns", children=[
                html.H5('State / Province'),
                dcc.Dropdown(
                    id='state'
                )
            ]),
            html.Div(className="three columns", children=[
                html.H5('County'),
                dcc.Dropdown(
                    id='county',
                )
            ]),
        ]),
        html.Div(className="row", children=[
            html.Div(className="nine columns", children=[
                dcc.Graph(
                    id="plot_new_metrics",
                    config={'displayModeBar': False}
                ),
            ]),

            html.Div(className="three columns", children=[
                html.A(html.Button('Reset'), href='/', style={'text-align': 'right'}),
                html.Br(),
                html.Br(),
                html.H5('Selected Metrics'),
                dcc.Checklist(
                    id='metrics',
                    options=[{'label': m, 'value': m} for m in ['Confirmed', 'Deaths']],
                    value=['Confirmed', 'Deaths']
                ),
                html.H5('Selected Date'),
                dcc.Checklist(
                    id='important date',
                    options=[{'label': m, 'value': m} for m in ['Policy Action date', 'Holiday']],
                    value=['State Policy Action date', 'Holiday']
                ),

                html.Br(),
                html.Br(),
                html.H5("Calender"),
                dcc.DatePickerRange(
                    id='my-date-picker-range',
                    end_date_placeholder_text="Enter Date",
                    with_portal=False,
                    first_day_of_week=0,
                    reopen_calendar_on_clear=True,
                    min_date_allowed=date(2020, 1, 22),
                    max_date_allowed=today,
                    initial_visible_month=date(2020, 1, 22),
                    minimum_nights=2,
                    persistence=True,
                    start_date=date(2020, 1, 22),
                    end_date=date(2021, 9, 9),
                    persisted_props=['start_date'],
                    persistence_type='session',
                    updatemode="singledate"
                ),
            ]),
        ]),

        dcc.Interval(
            id='interval-component',
            interval=3600 * 1000,  # Refresh data each hour.
            n_intervals=0
        ),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.H5("Given credit to Frank and Yeyun for this web, and Yeyun is so cute!", style={'text-align': 'center'})

    ]
)


@app.callback(
    [Output('state', 'options'), Output('state', 'value')],
    [Input('country', 'value')]
)
def update_states(country):
    d = allData()
    states = list(d.loc[d['Country'] == country]['Province/State'].unique())
    states.insert(0, '<all>')
    states.sort()
    state_options = [{'label': s, 'value': s} for s in states]
    state_value = state_options[0]['value']
    return state_options, state_value

ImportDate = []
def filtered_data(country, state):
    global ImportDate
    d = allData()
    data = d.loc[d['Country'] == country].drop('Country', axis=1)
    if state == '<all>' or state is None:
        data = data.drop('Province/State', axis=1).groupby("date").sum().reset_index()
        ImportDate = ["None", "2020-12-09", "2021-01-08", "2020-04-04", "2020-05-15"]
    else:
        data = data.loc[data['Province/State'] == state]
        states = str(state)
        row = ImportPolicy.loc[ImportPolicy["States"].str.match(states)]
        vars = row.values.tolist()
        i = range(5)
        for n in i:
            ImportDate.append(vars[0][n])
    newCases = data.select_dtypes(include='Int64').diff().fillna(0)
    newCases.columns = [column.replace('Cum', 'New') for column in newCases.columns]
    data = data.join(newCases)
    data['dateStr'] = data['date'].dt.strftime('%b %d, %Y')
    return data



def barchart(data, metrics, start_date, end_date, prefix="", yaxisTitle=""):
    global ImportDate
    start_date = dt.strptime(start_date, '%Y-%m-%d')
    end_date = dt.strptime(end_date, '%Y-%m-%d')
    Mask = dt.strptime(ImportDate[1], '%Y-%m-%d')
    Vaccine = dt.strptime(ImportDate[2], '%Y-%m-%d')
    StayHome = dt.strptime(ImportDate[3], '%Y-%m-%d')
    ReOpen = dt.strptime(ImportDate[4], '%Y-%m-%d')
    fil_data = data[(data['date'] >= start_date) & (data['date'] <= end_date)]
    mean = fil_data["NewConfirmed"].mean()
    HighBound = fil_data["NewConfirmed"].max()
    LowBound = fil_data["NewConfirmed"].min()
    figure = graph.Figure(data=[
        graph.Bar(
            name=metric, x=data.date, y=data[prefix + metric],
            # marker_line_color='rgb(0,0,0)', marker_line_width=1,
            marker_color={'Deaths': 'rgb(0,128,0)', 'Confirmed': 'rgb(100,140,240)'}[metric]
        ) for metric in metrics
    ]
    )
    figure.update_layout(
        barmode='group',
        legend=dict(x=.05, y=0.95, font={'size': 15}, bgcolor='rgba(240,240,240,0.5)'),
        plot_bgcolor='#FFFFFF', font=tickFont) \
        .add_vrect(x0=start_date, x1=end_date, y0=0, y1=10000, fillcolor="LightSalmon", opacity=0.3)\
        .update_xaxes(
        title="mean = {mean:.0f} Highbound = {H:.0f} LowBound = {L:0f}".format(mean = mean, H=HighBound, L=LowBound), tickangle=-90, type='category', showgrid=False, gridcolor='#DDDDDD',
        tickfont=tickFont) \
        .update_yaxes(
        title=yaxisTitle, showgrid=True, gridcolor='#DDDDDD') \
        .add_annotation(x=dt(2020, 7, 4), y=10001,
                    text="Independent Day",
                    showarrow=True,
                    arrowhead=1) \
        .add_shape(type="line", x0=dt(2021, 11, 5), x1=dt(2021, 11, 5), y0=10000, y1=0, line=dict(color="Blue", width=1)) \
        .add_annotation(x=dt(2021, 11, 5), y=10001,
                    text="Labor Day",
                    showarrow=True,
                    arrowhead=1) \
        .add_shape(type="line", x0=Mask, x1=Mask, y0=10000, y1=0,
                   line=dict(color="Purple", width=1)) \
        .add_annotation(x=Mask, y=10001,
                        text="Mask Start",
                        showarrow=True,
                        arrowhead=1) \
        .add_shape(type="line", x0=Vaccine, x1=Vaccine, y0=10000, y1=0,
                   line=dict(color="Green", width=1)) \
        .add_annotation(x=Vaccine, y=10001,
                        text="Vaccine Start",
                        showarrow=True,
                        arrowhead=1) \
        .add_shape(type="line", x0=StayHome, x1=StayHome, y0=10000, y1=0,
                   line=dict(color="Yellow", width=1)) \
        .add_annotation(x=StayHome, y=10001,
                        text="Stay Home",
                        showarrow=True,
                        arrowhead=1) \
        .add_shape(type="line", x0=ReOpen, x1=ReOpen, y0=10000, y1=0,
               line=dict(color="Blue", width=1)) \
        .add_annotation(x=ReOpen, y=10001,
                        text="ReOpen",
                        showarrow=True,
                        arrowhead=1)

    return figure


@app.callback(
    [Output('plot_new_metrics', 'figure'), Output('plot_cum_metrics', 'figure')],
    [Input('country', 'value'), Input('state', 'value'), Input('metrics', 'value'),
     Input('interval-component', 'n_intervals'), Input("my-date-picker-range", "start_date"),
     Input("my-date-picker-range", "end_date")]
)
def update_plots(country, state, metrics, n, start_date, end_date):
    refreshData()
    data = filtered_data(country, state)
    barchart_new = barchart(data, metrics, start_date, end_date, prefix="New", yaxisTitle="New Cases per new day (Thousand)")
    barchart_cum = barchart(data, metrics, start_date, end_date, prefix="Cum", yaxisTitle="Cumulated Cases")
    return barchart_new, barchart_cum

server = app.server

if __name__ == '__main__':
    app.run_server(host="0.0.0.0")