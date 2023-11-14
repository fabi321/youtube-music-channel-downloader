#! /usr/bin/env python

import argparse
import re
from pathlib import Path
from typing import Optional
from json import loads

from pathvalidate import sanitize_filename
from pytube import YouTube, Stream
from tqdm import tqdm

from util import types, convert_audio, database
from util.io import eprint, join_and_create


ROW_REGEX: re.Pattern = re.compile(r"^\s*((?:\d?\d:)?\d?\d:\d\d)\s*[:-]?(.*)$")


class Arguments:
    artist: Optional[str]
    album: Optional[str]
    year: Optional[str]
    mp3: bool
    destination: Path
    video_id: str


def init(destination: Path):
    join_and_create(destination, ".")


def parse_args() -> Arguments:
    parser = argparse.ArgumentParser(
        description="Download all titles from a video containing an album.\n"
        "WARNING: This utility does not interact with the database"
    )
    parser.add_argument("--artist", "-a", type=str, nargs="?", help="The artist")
    parser.add_argument("--album", "-b", type=str, nargs="?", help="The album")
    parser.add_argument(
        "--year", "-y", type=str, nargs="?", help="The year of publishing"
    )
    parser.add_argument(
        "--mp3", action="store_true", help="produce mp3 files instead of ogg files"
    )
    parser.add_argument(
        "destination",
        metavar="D",
        type=Path,
        help="The directory of the music collection",
    )
    parser.add_argument(
        "video_id", metavar="V", type=str, help="The video url or video id"
    )
    args: Arguments = parser.parse_args(namespace=Arguments())
    types.Options.mp3 = args.mp3
    return args


def get_description(video: YouTube) -> str:
    # inspired by https://github.com/pytube/pytube/issues/1626#issuecomment-1581334598
    i: int = video.watch_html.find('"shortDescription":"')
    desc: str = '"'
    i += 20  # excluding the `shortDescription":"`
    while True:
        letter = video.watch_html[i]
        desc += letter  # letter can be added in any case
        i += 1
        if letter == "\\":
            desc += video.watch_html[i]
            i += 1
        elif letter == '"':
            break
    return loads(desc)


def download_video(video: YouTube, folder: Path) -> str:
    stream: Stream
    if types.Options.mp3:
        stream = video.streams.get_audio_only(subtype="mp4")
    else:
        stream = video.streams.get_audio_only(subtype="webm")
    if not stream:
        stream = video.streams.get_audio_only()
    track_tmp_path: str = stream.download(output_path=str(folder))
    return track_tmp_path


def find_track_information(description: str) -> list[tuple[str, str]]:
    longest_list: list[tuple[str, str]] = []
    current_list: list[tuple[str, str]] = []
    for row in description.split("\n"):
        row = row.strip()
        if match := ROW_REGEX.match(row):
            timestamp: str = match.group(1)
            name: str = match.group(2).strip()
            current_list.append((timestamp, name))
        elif row:  # skip empty rows
            if len(current_list) > len(longest_list):
                longest_list = current_list
            current_list = []
    if len(current_list) > len(longest_list):
        longest_list = current_list
    return longest_list


def process_args(args: Arguments):
    init(args.destination)
    artist: str = args.artist or input("Please enter the artist name ->")
    album: str = args.album or input("Please enter the album name ->")
    year: str = args.year or input(
        "Please enter the year the album has been published ->"
    )
    video_id: str = args.video_id
    if "youtube" not in video_id:
        video_id = f"https://youtube.com/watch?v={video_id}"
    video: YouTube = YouTube(video_id)
    timestamps: list[tuple[str, str]] = find_track_information(get_description(video))
    print("Found the following timestamps:")
    for timestamp, name in timestamps:
        print(f"{timestamp}: {name}")
    tmp_path = download_video(video, args.destination)
    extended_timestamps: list[tuple[int, str, str, Optional[str]]] = [
        (
            i + 1,
            timestamps[i][0],
            timestamps[i][1],
            timestamps[i + 1][0] if i + 1 < len(timestamps) else None,
        )
        for i in range(len(timestamps))
    ]
    album_path = args.destination / artist / album
    album_path.mkdir(parents=True, exist_ok=True)
    for track_id, timestamp, name, next_timestamp in tqdm(extended_timestamps):
        metadata: convert_audio.Metadata = convert_audio.Metadata(
            name, artist, album, year, track_id, []
        )
        extension = "mp3" if types.Options.mp3 else "opus"
        track_path: Path = (
            album_path / f"{track_id:02} - {sanitize_filename(name)}.{extension}"
        )
        convert_audio.level_and_combine_audio(
            tmp_path, track_path, metadata, timestamp, next_timestamp
        )
    Path(tmp_path).unlink()


if __name__ == "__main__":
    input_args: types.Arguments = parse_args()
    process_args(input_args)
