import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as graph
from dash.dependencies import Input, Output
import numpy as np
import pandas as pd
from os.path import isfile
from datetime import datetime as dt
from datetime import date

GlobalURL = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/"
fileNamePickle = "allData.pkl"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
usaURL = "https://github.com/nytimes/covid-19-data/blob/master/us-counties.csv/"

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


def simple_moving_average(df, len=7):
    return df.rolling(len).mean()


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
                    min_date_allowed=date(2020, 1, 23),
                    max_date_allowed=today,
                    initial_visible_month=date(2020, 1, 23),
                    end_date=today,
                    minimum_nights=2,
                    persistence=True,
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
        html.H5("Given credit to Frank and Yeyun for this web", style={'text-align': 'center'})

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


def filtered_data(country, state):
    d = allData()
    data = d.loc[d['Country'] == country].drop('Country', axis=1)
    if state == '<all>':
        data = data.drop('Province/State', axis=1).groupby("date").sum().reset_index()
    else:
        data = data.loc[data['Province/State'] == state]
    newCases = data.select_dtypes(include='Int64').diff().fillna(0)
    newCases.columns = [column.replace('Cum', 'New') for column in newCases.columns]
    data = data.join(newCases)
    data['dateStr'] = data['date'].dt.strftime('%b %d, %Y')
    data['NewDeathsSMA7'] = simple_moving_average(data.NewDeaths, len=7)
    data['NewConfirmedSMA7'] = simple_moving_average(data.NewConfirmed, len=7)
    return data

def add_trend_lines(figure, data, metrics, prefix):
    if prefix == 'New':
        for metric in metrics:
            figure.add_trace(
                graph.Scatter(
                    x=data.date, y=data[prefix + metric + 'SMA7'],
                    mode='lines',
                    line=dict(width=3, color='rgb(0,128,0)' if metric == 'Deaths' else 'rgb(100,140,240)'),
                    name='Rolling 7-Day Average of Death' if metric == 'Deaths' \
                        else 'Rolling 7-Day Average of Confirm'
                )

            )


def barchart(data, metrics, prefix="", yaxisTitle="", axisTitle=""):
    figure = graph.Figure(data=[
        graph.Bar(
            name=metric, x=data.date, y=data[prefix + metric],
            # marker_line_color='rgb(0,0,0)', marker_line_width=1,
            marker_color={'Deaths': 'rgb(0,128,0)', 'Confirmed': 'rgb(100,140,240)'}[metric]
        ) for metric in metrics
    ])
    add_trend_lines(figure, data, metrics, prefix)
    figure.update_layout(
        barmode='group',
        legend=dict(x=.05, y=0.95, font={'size': 15}, bgcolor='rgba(240,240,240,0.5)'),
        plot_bgcolor='#FFFFFF', font=tickFont) \
        .update_xaxes(
        title="Date from 2020 to 2021", tickangle=-90, type='category', showgrid=False, gridcolor='#DDDDDD',
        tickfont=tickFont) \
        .update_yaxes(
        title=yaxisTitle, showgrid=True, gridcolor='#DDDDDD')
    return figure


@app.callback(
    [Output('plot_new_metrics', 'figure'), Output('plot_cum_metrics', 'figure')],
    [Input('country', 'value'), Input('state', 'value'), Input('metrics', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_plots(country, state, metrics, n):
    refreshData()
    data = filtered_data(country, state)
    barchart_new = barchart(data, metrics, prefix="New", yaxisTitle="New Cases per new day (Thousand)",
                            axisTitle="Date")
    barchart_cum = barchart(data, metrics, prefix="Cum", yaxisTitle="Cumulated Cases")
    return barchart_new, barchart_cum


@app.callback(
    Output('plot_new_metrics', 'figure'),
    [dash.dependencies.Input('my-date-picker-range', 'start_date'),
     dash.dependencies.Input('my-date-picker-range', 'end_date')])
def update_output(start_date, end_date):
    string_prefix = 'You have selected: '
    if start_date is not None:
        start_date_object = date.fromisoformat(start_date)
        start_date_string = start_date_object.strftime('%B %d, %Y')
        string_prefix = string_prefix + 'Start Date: ' + start_date_string + ' | '
    if end_date is not None:
        end_date_object = date.fromisoformat(end_date)
        end_date_string = end_date_object.strftime('%B %d, %Y')
        string_prefix = string_prefix + 'End Date: ' + end_date_string
    if len(string_prefix) == len('You have selected: '):
        return 'Select a date to see it displayed here'
    else:
        return string_prefix

server = app.server

if __name__ == '__main__':
    app.run_server(host="0.0.0.0")