from pathlib import Path

from youtubesearchpython import ChannelsSearch

from process.util import ytmusic
from process.album import get_albums_for_artist, get_singles_for_artist

from util import types, database
from util.io import join_and_create, bprint


def get_topic_channel_id(artist: types.Artist) -> str:
    target: str = f'{artist["name"]} - Topic'
    search = ChannelsSearch(target)
    for channel in search.result()['result']:
        if channel['title'].lower() == target.lower():
            return channel['id']


AlbumInput = tuple[types.AlbumResult, types.Artist, Path]


def process_artist(channel_id: str, destination: Path, global_albums: list[AlbumInput], no_singles: bool):
    artist: types.Artist = ytmusic.get_artist(channel_id)
    artist['topic_channel_id'] = get_topic_channel_id(artist)
    database.insert_artist(artist, no_singles)
    artist_destination: Path = join_and_create(destination, artist['name'])
    albums: list[types.AlbumResult] = get_albums_for_artist(artist)
    singles: list[types.SingleResult] = get_singles_for_artist(artist)
    if albums:
        for album in albums:
            if not types.Options.album_only or not database.check_album_exists(album, artist):
                global_albums.append((album, artist, artist_destination))
    if singles and not no_singles:
        for single in singles:
            if not types.Options.album_only or not database.check_album_exists(single, artist):
                global_albums.append((single, artist, artist_destination))
    else:
        bprint(f'No albums found for channel {channel_id}')
