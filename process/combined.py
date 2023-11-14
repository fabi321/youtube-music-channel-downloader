import traceback
from pathlib import Path
from typing import Optional

from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map

from process.album import process_album, TrackInput
from process.artist import process_artist, AlbumInput

from process.track import process_album_track
from util import types, database
from util.io import eprint, get_output_pipe, always_gen


def process_track_interop(args: TrackInput, results: types.ResultTuple):
    tracks, albums, errors = results
    error_result: Optional[str] = None
    for i in range(2):
        try:
            process_album_track(*args)
            error_result = None
            break
        except RuntimeError as e:
            error_result = str(e)
        except AssertionError as e:
            error_result = f"Failed assertion {e}"
        except:
            error_result = traceback.format_exc()
    album: types.Album = args[1]
    track: types.Track = album["tracks"][args[0]]
    artist: types.Artist = args[2]
    if error_result:
        result_error: types.ResultError = {
            "title": track["title"],
            "album": album["title"],
            "artist": artist["name"],
            "traceback": error_result,
            "id": track["videoId"],
        }
        errors.append(result_error)
        eprint(
            f'Warning: could not process track {track["title"]} from album {album["title"]}'
        )
    else:
        result_track: types.ResultTrack = {
            "id": track["videoId"],
            "title": track["title"],
            "album": album["title"],
            "artist": artist["name"],
        }
        tracks.append(result_track)
        result_album: types.ResultAlbum = {
            "title": album["title"],
            "artist": artist["name"],
        }
        albums[album["audioPlaylistId"]] = result_album


def process_artists(
    channels: list[tuple[str, bool]], destination: Path, results: types.ResultTuple
):
    progress_output = get_output_pipe()
    albums: list[AlbumInput] = []
    for channel in tqdm(
        channels, desc="Processing artists", unit="artist", file=progress_output
    ):
        try:
            process_artist(channel[0], destination, albums, channel[1])
        except:
            eprint(f'{channel[0]} had error\n' + traceback.format_exc())
    if not albums or database.daemon_running():
        return
    tracks: list[TrackInput] = []
    for album in tqdm(
        albums, desc="Processing albums", unit="album", file=progress_output
    ):
        try:
            process_album(album[0], album[1], album[2], tracks)
        except:
            error: types.ResultError = {
                "title": None,
                "album": album[0]["title"],
                "artist": album[1]["name"],
                "traceback": traceback.format_exc(),
                "id": album[0]["browseId"],
            }
            results[2].append(error)
            eprint(
                f'{album[0]["title"]} from {album[1]["name"]} had error\n'
                + traceback.format_exc()
            )
    if not tracks:
        return
    threads = types.Options.processing_threads
    output_gen = always_gen(len(tracks), results)
    thread_map(
        process_track_interop,
        tracks,
        output_gen,
        max_workers=threads,
        desc="Processing tracks",
        unit="track",
        file=progress_output,
    )
