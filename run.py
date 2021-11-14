from src import fetch_data
from src import format_data

import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('player', help='the name of the player at chess.com')
    parser.add_argument('local_tz', help="the players' local time zone (optional)")
    args = parser.parse_args()
    fetch_data.main(player=args.player)
    format_data.main(local_tz=args.local_tz)
