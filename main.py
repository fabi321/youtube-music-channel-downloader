#! /usr/bin/env python

from youtubesearchpython import ChannelsSearch, SearchVideos
import argparse

from util.io import bprint, eprint, get_output_pipe, always_gen, join_and_create
from util.multiselect import multiselect
from util import convert_audio, types, database
from pathlib import Path
from typing import Optional
from ytmusicapi import YTMusic
from pytube import YouTube
import json
from urllib.request import urlretrieve
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map
import os
from pathvalidate import sanitize_filename
import traceback

ytmusic: YTMusic = YTMusic()


def get_channel_id(name: str) -> str:
    artists = ytmusic.search(name, filter='artists')
    if len(artists) > 1:
        selections = [f'{artist["artist"]}' for artist in artists]
        selected = multiselect(f'The query for "{name}" returned multiple artists', 'Please pick an artist-> ', selections)
        artists = [artists[selected]]
    elif len(artists) == 0:
        raise RuntimeError('No channel found')
    return artists[0]['browseId']


def get_topic_channel_id(artist: types.Artist) -> str:
    target: str = f'{artist["name"]} - Topic'
    search = ChannelsSearch(target)
    for channel in search.result()['result']:
        if channel['title'].lower() == target.lower():
            return channel['id']


def get_albums_for_artist(artist: types.Artist) -> Optional[list[types.AlbumResult]]:
    if 'albums' in artist:
        params: str = artist['albums'].get('params')
        if params:
            param_result = ytmusic.get_artist_albums(artist['channelId'], artist['albums']['params'])
            if param_result:
                return param_result
        return artist['albums']['results']


def get_alternative_track_id(track: types.Track, album: types.Album, artist: types.Artist) -> Optional[str]:
    from fuzzywuzzy import fuzz
    search = SearchVideos(f'"{artist["name"]} - topic" "{album["title"]}" "{track["title"]}"')
    for result in search.resultComponents:
        if result['title'].lower() == track['title'].lower():
            return result['id']
    search = SearchVideos(f'"{artist["name"]} - topic" "{track["title"]}"')
    for result in search.resultComponents:
        if result['title'].lower() == track['title'].lower():
            return result['id']
    title = track['title'].split('(')[0].strip()
    search = SearchVideos(f'"{artist["name"]} - topic" "{title}"')
    for result in search.resultComponents:
        if result['title'].lower() == title.lower():
            return result['id']
    best_score: int = 0
    best_result: Optional[str] = None
    for result in search.resultComponents:
        score: int = fuzz.ratio(result['title'].lower(), title.lower())
        if score > best_score:
            best_result = result['id']
            best_score = score
    return best_result


def process_track(track_id: int, album: types.Album, artist: types.Artist, album_destination: Path, cover_path: Path, alid: int):
    track: types.Track = album['tracks'][track_id]
    track_id += 1
    track_path: Path = album_destination.joinpath(f'{track_id:02} - {sanitize_filename(track["title"])}.ogg')
    video: Optional[YouTube] = None
    if track['videoId']:
        video = YouTube(f'https://youtube.com/watch?v={track["videoId"]}')
    if not video or video.channel_id != artist['topic_channel_id']:
        video_id = get_alternative_track_id(track, album, artist)
        if video_id:
            video = YouTube(f'https://youtube.com/watch?v={video_id}')
    if not video:
        raise RuntimeError('Did not find any matching video at all')
    stream = video.streams.get_audio_only(subtype='webm') or video.streams.get_audio_only()
    track_tmp_path = stream.download(output_path=str(album_destination), filename_prefix=str(track_id))
    metadata: convert_audio.Metadata = convert_audio.Metadata(track, track_id, album, artist, cover_path)
    convert_success: bool = convert_audio.level_and_combine_audio(track_tmp_path, track_path, metadata)
    if convert_success:
        Path(track_tmp_path).unlink()
        database.insert_track(alid, track, track_id)
    else:
        eprint(f'Warning: could not process track {track["title"]} from album {album["title"]}')


def process_thumbnail(album: types.Album, album_destination: Path):
    cover_path: Path = album_destination.joinpath('cover.jpg')
    urlretrieve(album['thumbnails'][-1]['url'], cover_path)
    return cover_path


TrackInput = tuple[int, types.Album, types.Artist, Path, Path, int]
AlbumInput = tuple[types.AlbumResult, types.Artist, Path]


def process_album(album: types.AlbumResult, artist: types.Artist, artist_destination: Path, tracks: list[TrackInput]):
    album: types.Album = ytmusic.get_album(album['browseId'])
    alid: int = database.insert_album(album, artist)
    db_tracks: list[str] = database.get_tracks_for_album(alid)
    album_destination: Path = join_and_create(artist_destination, album['title'])
    cover_path = process_thumbnail(album, album_destination)
    for i in range(len(album['tracks'])):
        track: types.Track = album['tracks'][i]
        video_id: str = database.get_video_id_for_track(track)
        if video_id not in db_tracks:
            tracks.append((i, album, artist, album_destination, cover_path, alid))


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


def process_artist(channel_id: str, destination: Path, global_albums: list[AlbumInput]):
    artist: types.Artist = ytmusic.get_artist(channel_id)
    artist['topic_channel_id'] = get_topic_channel_id(artist)
    database.insert_artist(artist)
    artist_destination: Path = join_and_create(destination, artist['name'])
    albums: list[types.AlbumResult] = get_albums_for_artist(artist)
    if albums:
        for album in albums:
            if not types.Options.album_only or not database.check_album_exists(album, artist):
                global_albums.append((album, artist, artist_destination))
    else:
        bprint(f'No albums found for channel {channel_id}')


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


def init(destination: Path):
    join_and_create(destination, '.')
    database.init(destination.joinpath('music-channel-downloader.db'))


def maintenance(destination: Path, results: types.ResultTuple):
    init(destination)
    channels = database.get_artists()
    return process_artists(channels, destination, results)


def add_channels_from_names(destination: Path, names: list[str], results: types.ResultTuple):
    init(destination)
    channels = []
    for name in names:
        channels.append(get_channel_id(name))
    return process_artists(channels, destination, results)


def add_channels_from_channel_ids(destination: Path, channel_ids: list[str], results: types.ResultTuple):
    init(destination)
    return process_artists(channel_ids, destination, results)


def parse_args() -> types.Arguments:
    parser = argparse.ArgumentParser(description='Download all music videos from a "* - Topic" channel\n'
                                                 'It will check all existing channels if neither names nor'
                                                 ' ChannelIds are supplied')
    default_thread_count: int = os.cpu_count()//2 or 5
    parser.add_argument('--threads', '-t', default=default_thread_count, type=int, help=f'The number of processing threads, default: {default_thread_count}')
    parser.add_argument('--background', '-b', action='store_true', help='Run in Background mode, only returning a final json')
    parser.add_argument('--album-only', '-a', action='store_true', help='Only investigate unknown albums, do not check all individual tracks')
    parser.add_argument('--channel-id', '-c', type=str, nargs='*', help='Specify ChannelIds to check')
    parser.add_argument('destination', metavar='D', type=Path, help='The directory of the music collection')
    parser.add_argument('name', metavar='N', type=str, nargs='*', help='The name of the channel')
    args = parser.parse_args(namespace=types.Arguments())
    types.Options.processing_threads = args.threads
    types.Options.background = args.background
    types.Options.album_only = args.album_only
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
    output: types.Result = {'tracks': tracks, 'albums': albums, 'errors': errors}
    if args.background and (tracks or albums or errors):
        print(json.dumps(output))


if __name__ == "__main__":
    input_args: types.Arguments = parse_args()
    process_args(input_args)
