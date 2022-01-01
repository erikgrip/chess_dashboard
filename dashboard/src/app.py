import pyarrow.parquet as pq
import json
import plotly.express as px
import dash
import dash_bootstrap_components as dbc
from dash import html
from dash import dcc
from dash.dependencies import Input
from dash.dependencies import Output


data_path = '../data/data.parquet'
filter_pane_width = 2


def read_parquet_data(path):
    try:
        pq_table = pq.read_table(path)
        meta = json.loads(pq_table.schema.metadata[b'fetch_metadata'])
        df = pq_table.to_pandas().sort_values(['end_date_local', 'end_time_local'])
        return df, meta
    except FileNotFoundError as e:
        print("No data file found at ", path)
    except ValueError as e:
        print("Error loading parquet table", path)


def define_layout(filter_pane_width, player_name, fetch_timestamp):
    layout =  dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1(f"Player: {player_name}",
                        style={'fontSize': 48})
            ], width={'size': 9, 'offset': filter_pane_width}),
        ], class_name='mb-2', style={'padding-top': '2vh'}),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Time Class")
                    ])
                ], color='light', outline=True)
            ], width=filter_pane_width, align='end'),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Rating"),
                        html.H1(id='content-rating', children='0000')
                    ], style={'text-align': 'center', 'height': '10vh'})
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Number of Games"),
                        html.H1(id='content-num-games', children='0000')
                    ], style={'text-align': 'center', 'height': '10vh'})
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Latest Game Date"),
                        html.H1(id='content-latest-date', children='2021/12/27')
                    ], style={'text-align': 'center', 'height': '10vh'})
                ])
            ], width=3),
        ], class_name='mb-2'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.RadioItems(
                            id='select-time-class',
                            options=[
                                {'label': ' Bullet', 'value': 'bullet'},
                                {'label': ' Blitz', 'value': 'blitz'},
                                {'label': ' Rapid', 'value': 'rapid'},
                                {'label': ' Daily', 'value': 'daily'}],
                            value='blitz',
                            labelStyle={'display': 'block'})
                    ])
                ], color='light', outline=True)
            ], width=filter_pane_width),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(id='line-chart', figure={})
                    ])
                ])
            ], width=9),
        ], class_name='mb-2'),
        dbc.Row([
            dbc.Col([
                html.Div("Data up to:"),
                html.Div(fetch_timestamp)
            ], width=filter_pane_width, align='end'),
            dbc.Col([
                dbc.Card([
                        dcc.Graph(id='bar-chart',
                                figure={},
                                config={'displayModeBar': False}
                        )
                    ], style={'text-align': 'center', 'height': '10vh'})
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Best Win"),
                        html.H1(id='content-best-win', children='0000')
                    ], style={'text-align': 'center', 'height': '10vh'})
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Best Win Streak"),
                        html.H1(id='content-win-streak', children='00')
                    ], style={'text-align': 'center', 'height': '10vh'})
                ])
            ], width=3),
        ], style = {'padding-bottom': '2vh'})
    ], style={'background-color': '#EAF2F8'})
    return layout


def main():
    df, meta = read_parquet_data(data_path)
    player_name = meta['player_name']
    tz = meta['timestamps_localized_to']
    fetch_timestamp = meta['fetch_timestamp']

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
    app.layout = define_layout(filter_pane_width, player_name, fetch_timestamp)

    # Define callbacks to update dashboard
    @app.callback(
        [Output(component_id='content-rating',
                component_property='children'),
        Output(component_id='content-num-games',
                component_property='children'),
        Output(component_id='content-latest-date',
                component_property='children'),
        Output(component_id='content-best-win',
                component_property='children'),
        Output(component_id='content-win-streak',
                component_property='children')],
        [Input(component_id='select-time-class', component_property='value')]
        )
    def update_cards(selected_tc):
        dff = (
            df[df['time_class'] == selected_tc]
            .sort_values(['end_date_local', 'end_time_local'])
            .copy())
        rating = dff.iloc[-1, :]['rating']
        num_games = dff['game_id'].nunique()
        latest_date = dff.iloc[-1, :]['end_date_local']
        best_win = dff[dff['is_win'] == True]['opp_rating'].max()
        grouper = (dff['is_win'] != dff['is_win'].shift()).cumsum()
        best_streak = dff.groupby(grouper)['is_win'].cumsum().max()
        return rating, num_games, latest_date, best_win, best_streak


    @app.callback(
        Output(component_id='bar-chart', component_property='figure'),
        [Input(component_id='select-time-class', component_property='value')]
        )
    def update_result_bar_chart(selected_tc):
        plot_df = (
            df[df['time_class'] == selected_tc]['result_str']
            .value_counts(normalize=True)
            .round(2)
            .mul(100)
            .astype('int')
            .reset_index()
            .rename(columns={'index': 'Result', 'result_str': 'Pct'})
        )
        fig = px.bar(
            data_frame=plot_df,
            x='Result',
            y='Pct',
            text='Pct',
            color='Result',
            color_discrete_map={'Win': 'steelblue', 'Draw': 'gray', 'Loss': 'orange'},
            category_orders={'Result': ['Win', 'Draw', 'Loss']},
            height=100
        )
        fig.update_layout(
            title='Result',
            title_x=0.5,
            xaxis={'title': '',
                'visible': True,
                'showticklabels': True},
            yaxis={'title': 'Percent',
                'visible': False},
            margin=dict(l=20, r=10, t=60, b=0),
            showlegend=False,
            plot_bgcolor= 'rgba(0, 0, 0, 0)',
            paper_bgcolor= 'rgba(0, 0, 0, 0)'
        )
        fig.update_traces(
            textfont_size=14,
            texttemplate="%{text:.2%f}%",
            cliponaxis=False)
        return fig


    @app.callback(
        Output(component_id='line-chart', component_property='figure'),
        [Input(component_id='select-time-class', component_property='value')]
        )
    def update_rating_chart(selected_tc):
        plot_df = (
            df[df['time_class'] == selected_tc]
            .sort_values(['end_date_local', 'end_time_local'])
            # Keep last game by day
            .drop_duplicates(subset='end_date_local', keep='last')
            .rename(columns={'end_date_local': 'Date',
                            'rating': 'Rating'})
        )
        fig = px.line(
            plot_df,
            x="Date",
            y="Rating"
        )
        fig.update_layout(
            title='Rating Time Line',
            title_x=0.5,
            xaxis={'title': '',
                'visible': True,
                'showticklabels': True},
            yaxis={'visible': True},
            margin=dict(l=20, r=10, t=60, b=0),
            showlegend=False,
            plot_bgcolor= '#EAF2F8'
        )
        fig.update_traces(line_color='#0E6655', line_width=2)
        return fig

    app.run_server(host='0.0.0.0', port=8050, debug=True)
