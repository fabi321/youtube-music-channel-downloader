#! /usr/bin/env python

import argparse

from process.combined import process_artists
from process.util import ytmusic
from util.io import join_and_create
from util.multiselect import multiselect
from util import types, database
from pathlib import Path
import json
import os


def get_channel_id(name: str) -> str:
    artists = ytmusic.search(name, filter="artists")
    if len(artists) > 1:
        selections = [f'{artist["artist"]}' for artist in artists]
        selected = multiselect(
            f'The query for "{name}" returned multiple artists',
            "Please pick an artist-> ",
            selections,
        )
        artists = [artists[selected]]
    elif len(artists) == 0:
        raise RuntimeError("No channel found")
    return artists[0]["browseId"]


def init(destination: Path):
    join_and_create(destination, ".")
    database.init(destination.joinpath("music-channel-downloader.db"))


def maintenance(destination: Path, results: types.ResultTuple):
    init(destination)
    channels = database.get_artists()
    return process_artists(channels, destination, results)


def add_channels_from_names(
    destination: Path, names: list[str], results: types.ResultTuple
):
    init(destination)
    channels = [(get_channel_id(name), types.Options.no_singles) for name in names]
    return process_artists(channels, destination, results)


def add_channels_from_channel_ids(
    destination: Path, channel_ids: list[str], results: types.ResultTuple
):
    init(destination)
    channels = [(channel_id, types.Options.no_singles) for channel_id in channel_ids]
    return process_artists(channels, destination, results)


def parse_args() -> types.Arguments:
    parser = argparse.ArgumentParser(
        description='Download all music videos from a "* - Topic" channel.\n'
        "It will check all existing channels if neither names nor"
        " ChannelIds are supplied"
    )
    default_thread_count: int = os.cpu_count() // 2 or 5
    parser.add_argument(
        "--threads",
        "-t",
        default=default_thread_count,
        type=int,
        help=f"The number of processing threads, default: {default_thread_count}",
    )
    parser.add_argument(
        "--background",
        "-b",
        action="store_true",
        help="Run in Background mode, only returning a final json",
    )
    parser.add_argument(
        "--album-only",
        "-a",
        action="store_true",
        help="Only investigate unknown albums, do not check all individual tracks",
    )
    parser.add_argument(
        "--channel-id", "-c", type=str, nargs="*", help="Specify ChannelIds to check"
    )
    parser.add_argument(
        "--mp3", action="store_true", help="produce mp3 files instead of ogg files"
    )
    parser.add_argument(
        "--no-singles",
        action="store_true",
        help="Do not download singles for the supplied artists",
    )
    parser.add_argument(
        "destination",
        metavar="D",
        type=Path,
        help="The directory of the music collection",
    )
    parser.add_argument(
        "name", metavar="N", type=str, nargs="*", help="The name of the channel"
    )
    args = parser.parse_args(namespace=types.Arguments())
    types.Options.processing_threads = args.threads
    types.Options.background = args.background
    types.Options.album_only = args.album_only
    types.Options.no_singles = args.no_singles
    types.Options.mp3 = args.mp3
    return args


def process_args(args: types.Arguments):
    results: types.ResultTuple = ([], {}, [])
    check_library: bool = True
    if args.name:
        add_channels_from_names(args.destination, args.name, results)
        check_library = False
    if args.channel_id:
        add_channels_from_channel_ids(args.destination, args.channel_id, results)
        check_library = False
    if check_library:
        maintenance(args.destination, results)
    tracks, albums, errors = results
    output: types.Result = {"tracks": tracks, "albums": albums, "errors": errors}
    if args.background and (tracks or albums or errors):
        print(json.dumps(output))


if __name__ == "__main__":
    input_args: types.Arguments = parse_args()
    process_args(input_args)
