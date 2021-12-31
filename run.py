from fetch_chess_data import run as fetch
from dashboard import run as dashboard

import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('player', help='the name of the player at chess.com')
    parser.add_argument('local_tz', help="the players' local time zone (optional)")
    args = parser.parse_args()

    fetch.run(player=args.player, local_tz=args.local_tz)
    dashboard.run()
