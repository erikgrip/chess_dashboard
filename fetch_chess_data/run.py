from .src import fetch_data
from .src import format_data

import argparse


def run(player, local_tz):
    fetch_data.main(player)
    format_data.main(local_tz)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('player', help='the name of the player at chess.com')
    parser.add_argument('local_tz', help="the players' local time zone (optional)")
    args = parser.parse_args()
    run(player=args.player, local_tz=args.local_tz)
