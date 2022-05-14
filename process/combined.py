import traceback
from pathlib import Path
from typing import Optional

from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map

from process.album import process_album, TrackInput
from process.artist import process_artist, AlbumInput

from process.track import process_track
from util import types
from util.io import eprint, get_output_pipe, always_gen


def process_track_interop(args: TrackInput, results: types.ResultTuple):
    tracks, albums, errors = results
    error_result: Optional[str] = None
    for i in range(2):
        try:
            process_track(*args)
            error_result = None
            break
        except:
            error_result = traceback.format_exc()
    album: types.Album = args[1]
    track: types.Track = album['tracks'][args[0]]
    artist: types.Artist = args[2]
    if error_result:
        result_error: types.ResultError = {
            'title': track['title'],
            'album': album['title'],
            'artist': artist['name'],
            'traceback': error_result,
            'id': track['videoId'],
        }
        errors.append(result_error)
        eprint(f'Warning: could not process track {track["title"]} from album {album["title"]}')
    else:
        result_track: types.ResultTrack = {
            'title': track['title'],
            'album': album['title'],
            'artist': artist['name'],
        }
        tracks.append(result_track)
        result_album: types.ResultAlbum = {
            'title': album['title'],
            'artist': artist['name'],
        }
        albums[album['audioPlaylistId']] = result_album


def process_artists(channel_ids: list[str], destination: Path, results: types.ResultTuple):
    progress_output = get_output_pipe()
    albums: list[AlbumInput] = []
    for channel_id in tqdm(channel_ids, desc='Processing artists', unit='artist', file=progress_output):
        process_artist(channel_id, destination, albums)
    if not albums:
        return
    tracks: list[TrackInput] = []
    for album in tqdm(albums, desc='Processing albums', unit='album', file=progress_output):
        process_album(album[0], album[1], album[2], tracks)
    if not tracks:
        return
    threads = types.Options.processing_threads
    output_gen = always_gen(len(tracks), results)
    thread_map(process_track_interop, tracks, output_gen, max_workers=threads, desc='Processing tracks', unit='track', file=progress_output)
