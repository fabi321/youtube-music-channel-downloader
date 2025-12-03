import argparse
from util import types, database
import os
from pathlib import Path
from typing import Optional
from util.io import join_and_create
import json
import threading
import time
from process import artist, album, combined
from util.io import always_gen
from concurrent.futures import ThreadPoolExecutor
import traceback


class Arguments:
    threads: int
    destination: Path
    log_file: Optional[Path]
    mp3: bool
    no_singles: bool
    artist_iteration_time: int
    album_iteration_time: int


class UpdateArtist(threading.Thread):
    def __init__(self, arguments: Arguments):
        super().__init__()
        self.iteration_time: int = arguments.artist_iteration_time
        self.destination: Path = arguments.destination
        self.is_running: bool = True

    def do_update(self, channel_id: str):
        print(f"Updating {channel_id}")
        albums: list[artist.AlbumInput] = []
        artist.process_artist(channel_id, self.destination, albums, False)
        for current_album in albums:
            album.insert_album(current_album[0], current_album[1])

    def run(self):
        while self.is_running:
            try:
                start_time: float = time.time()
                if aid := database.get_least_recently_updated_artist():
                    try:
                        self.do_update(aid[1])
                    except:
                        print(traceback.format_exc())
                    database.update_artist(aid[0])
                time.sleep(max(0.0, self.iteration_time + start_time - time.time()))
            except:
                print(traceback.format_exc())
                time.sleep(1)


class UpdateAlbum(threading.Thread):
    def __init__(self, arguments: Arguments):
        super().__init__()
        self.iteration_time: int = arguments.album_iteration_time
        self.destination: Path = arguments.destination
        self.log_file: Path = arguments.log_file
        self.is_running: bool = True

    def do_update(self, alid: int, results: types.ResultTuple):
        tracks: list[album.TrackInput] = []
        current_artist, current_album = album.get_from_alid(alid)
        print(f"Updating {current_album}")
        artist_destination: Path = join_and_create(self.destination, current_artist["path"])
        album.process_album(current_album, current_artist, artist_destination, tracks)
        if not tracks:
            return
        output_gen = always_gen(len(tracks), results)
        ex = ThreadPoolExecutor(types.Options.processing_threads)
        items = ex.map(
            combined.process_track_interop,
            tracks,
            output_gen,
        )
        for _ in items:
            ...  # wait for it to execute

    def log_result(self, results: types.ResultTuple, last_update: int):
        tracks, albums, errors = results
        output: types.Result = {"tracks": tracks, "albums": albums, "errors": errors}
        if tracks or albums or errors and int(last_update) == 0 or errors and errors[0]['traceback'] == 'Not found':
            for album in albums.values():
                album['title'] = album['title'] + (' (New)' if int(last_update) == 0 else ' (Update)')
            with open(self.log_file, 'a') as f:
                json.dump(output, f)
                f.write("\n")

    def not_found_error(self, alid: int, results: types.ResultTuple):
        album_info = database.get_album_info(alid)
        print(f"{album_info[0]} from {album_info[2]} not found, postponing to infinity.")
        error: types.ResultError = {
            'title': None,
            'album': album_info[0],
            'artist': album_info[2],
            'id': album_info[1],
            'traceback': 'Not found',
        }
        results[2].append(error)

    def run(self):
        while self.is_running:
            try:
                start_time: float = time.time()
                if alid := database.get_least_recently_updated_album():
                    infinite = False
                    results: types.ResultTuple = ([], {}, [])
                    try:
                        self.do_update(alid[0], results)
                    except Exception as e:
                        if str(e).startswith('Server returned HTTP 404: Not Found.'):
                            self.not_found_error(alid[0], results)
                            infinite = True
                        else:
                            print(traceback.format_exc())
                    self.log_result(results, alid[1])
                    database.update_album(alid[0], infinite)
                time.sleep(max(0.0, self.iteration_time + start_time - time.time()))
            except:
                print(traceback.format_exc())
                time.sleep(1)


def parse_args() -> Arguments:
    parser = argparse.ArgumentParser(
        description='Synchronize channels and albums in background'
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
        "--mp3", action="store_true", help="produce mp3 files instead of ogg files"
    )
    parser.add_argument(
        "--no-singles",
        action="store_true",
        help="Do not download singles for the supplied artists",
    )
    parser.add_argument(
        "--artist-iteration-time",
        "-a",
        default=30,
        type=int,
        help=f"Every how many seconds should artists be iterated over",
    )
    parser.add_argument(
        "--album-iteration-time",
        "-b",
        default=30,
        type=int,
        help=f"Every how many seconds should albums be iterated over",
    )
    parser.add_argument(
        "--log-file",
        "-l",
        type=Path,
        help="Optional log file path for updates",
    )
    parser.add_argument(
        "destination",
        metavar="D",
        type=Path,
        help="The directory of the music collection",
    )
    args: Arguments = parser.parse_args(namespace=Arguments())
    types.Options.processing_threads = args.threads
    types.Options.no_singles = args.no_singles
    types.Options.mp3 = args.mp3
    types.Options.album_only = False
    return args


def init(destination: Path):
    join_and_create(destination, ".")
    database.init(destination.joinpath("music-channel-downloader.db"))
    database.register_daemon()


def process_args(args: types.Arguments):
    init(args.destination)
    artists = UpdateArtist(args)
    albums = UpdateAlbum(args)
    artists.start()
    albums.start()
    try:
        artists.join()
        albums.join()
    except KeyboardInterrupt:
        database.unregister_daemon()
        artists.is_running = False
        albums.is_running = False


if __name__ == "__main__":
    input_args: types.Arguments = parse_args()
    try:
        process_args(input_args)
    except KeyboardInterrupt:
        database.unregister_daemon()
