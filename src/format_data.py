import re
import pandas as pd
import numpy as np
import json
import argparse
import pyarrow as pa
import pyarrow.parquet as pq

OUTPUT_COLS = [
    'game_id',
    'start_date_local',
    'start_time_local',
    'end_date_local',
    'end_time_local',
    'event',
    'site',
    'time_class',
    'time_control',
    'result',
    'result_str',
    'termination',
    'eco',
    'name',
    'color',
    'is_white',
    'is_black',
    'rating',
    'is_win',
    'is_loss',
    'is_draw',
    'won_points',
    'opp_name',
    'opp_rating'
    ]


def game_metadata_from_pgn(pgn_string) -> dict:
    ''' Read a PGN and return a dictionary version of the part up to the the moves list.
    [Event \"Live Chess\"] --> {'Event': 'Live Chess', ...} '''

    # Moves list separated by 2 blank rows
    pgn_meta = pgn_string.split("\n\n")[0]
    game_dict = {}
    for line in pgn_meta.splitlines():
        k = re.findall(r'\[(.*?)\s', line)[0]  # All between "[" and " "
        v = re.findall(r'"(.*?)"', line)[0]  # All between quotation marks
        game_dict[k] = v
    return game_dict


def game_id_from_url(url):
    ''' Urls look like 'https://www.chess.com/live/game/6071303142'
    '''
    return int(url.split('/')[-1])


def format_game_data(game):
    pgn_meta = game_metadata_from_pgn(game['pgn'])
    format_dict = {
        'game_id': game_id_from_url(game['url']),
        'event': pgn_meta['Event'],
        'site': pgn_meta['Site'],
        'start_date_utc': pgn_meta['UTCDate'],  # No entry called StartDate
        'start_time_utc': pgn_meta['StartTime'],
        'end_date_utc': pgn_meta['EndDate'],
        'end_time_utc': pgn_meta['EndTime'],
        'white_name': pgn_meta['White'],
        'white_rating': int(pgn_meta['WhiteElo']),
        'black_name': pgn_meta['Black'],
        'black_rating': int(pgn_meta['BlackElo']),
        'time_control': pgn_meta['TimeControl'],
        'time_class': game['time_class'],
        'result': pgn_meta['Result'],
        'termination': pgn_meta['Termination'].split(' ')[-1],  # Keep last word only
        'eco': pgn_meta['ECO'] if 'ECO' in pgn_meta.keys() else np.nan,  # ECO missing if no moves
        'pgn': game['pgn']
    }
    return format_dict


def localize_utc_time(utc_date_series, utc_time_series, local_tz):
    utc_timestamps = pd.to_datetime(utc_date_series + " " +
                                    utc_time_series).dt.tz_localize('UTC')
    local_timestamps = utc_timestamps.dt.tz_convert(local_tz)
    local_dates = local_timestamps.dt.date
    local_times = local_timestamps.dt.time
    return local_dates, local_times


def add_player_perspective_cols(df, player):
    df['name'] = player
    df['color'] = np.where(df['white_name'] == player, 'White', 'Black')
    df['is_white'] = np.where((df['color'] == 'White'), 1, 0)
    df['is_black'] = np.where((df['color'] == 'Black'), 1, 0)
    df['rating'] = np.where(df['color'] == 'White', df['white_rating'], df['black_rating'])
    df['is_win'] = np.where(((df['color'] == 'White') & (df['result'] == '1-0')) |
                                ((df['color'] == 'Black') & (df['result'] == '0-1')), 1, 0)
    df['is_loss'] = np.where(((df['color'] == 'White') & (df['result'] == '0-1')) |
                                 ((df['color'] == 'Black') & (df['result'] == '1-0')), 1, 0)
    df['is_draw'] = (df['result'] == '1/2-1/2').astype('int')
    df['result_str'] = np.where(df['is_win'] == 1, 'Win',
                                       np.where(df['is_loss'] == 1, 'Loss', 'Draw'))
    df['won_points'] = np.where(df['is_win'] == 1, 1, np.where(df['is_loss'] == 1, 0, 0.5))
    df['opp_name'] = np.where(df['color'] == 'White', df['black_name'], df['white_name'])
    df['opp_rating'] = np.where(df['color'] == 'White', df['black_rating'], df['white_rating'])
    return df


def update_arrow_metadata(current_metadata, new_metadata : dict):
    new_metadata = json.dumps(new_metadata)
    custom_meta_key = 'fetch_metadata'
    combined_metadata = {
        custom_meta_key.encode() : new_metadata.encode(),
        **current_metadata
    }
    return combined_metadata


def main(local_tz):
    # Read input data
    with open('data/raw_data.json') as json_file:
        input_file = json.load(json_file)
    formatted_games = [format_game_data(game) for _, game in input_file['data'].items()]

    # Read and update fetch metadata
    raw_file_metadata = input_file['metadata']
    raw_file_metadata['timestamps_localized_to'] = local_tz
    player = raw_file_metadata['player_name']

    df = pd.DataFrame(formatted_games)

    # Add columns
    df = add_player_perspective_cols(df, player)
    df['start_date_local'], df['start_time_local'] = localize_utc_time(
        df['start_date_utc'], df['start_time_utc'], local_tz)
    df['end_date_local'], df['end_time_local'] = localize_utc_time(
        df['end_date_utc'], df['end_time_utc'], local_tz)

    # Filter columns and transform to Arrow table in order to attach metadata
    df = df[OUTPUT_COLS]
    table = pa.Table.from_pandas(df)

    # Update metadata with info from fetching
    updated_metadata = update_arrow_metadata(table.schema.metadata, raw_file_metadata)
    table = table.replace_schema_metadata(updated_metadata)

    # Write to parquet
    pq.write_table(table, 'data/data.parquet', compression='GZIP')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('local_tz', nargs='?', default='UTC',
                        help='the timezone which to convert the timestamps to (optional)')
    args = parser.parse_args()
    main(local_tz=args.local_tz)
