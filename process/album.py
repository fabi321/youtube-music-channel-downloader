from pathlib import Path
from typing import Optional
from urllib.request import urlretrieve

from process.util import ytmusic
from util import types, database
from util.io import join_and_create
from .util import match_playlist_and_album


def get_albums_for_artist(artist: types.Artist) -> Optional[list[types.AlbumResult]]:
    if 'albums' in artist:
        params: str = artist['albums'].get('params')
        if params:
            param_result = ytmusic.get_artist_albums(artist['albums']['browseId'], params)
            if param_result:
                return param_result
        return artist['albums']['results']


def get_singles_for_artist(artist: types.Artist) -> Optional[list[types.SingleResult]]:
    if 'singles' in artist:
        params: str = artist['singles'].get('params')
        if params:
            param_result = ytmusic.get_artist_albums(artist['singles']['browseId'], params)
            if param_result:
                return param_result
        return artist['singles']['results']


def process_thumbnail(album: types.Album, album_destination: Path):
    cover_path: Path = album_destination.joinpath('cover.jpg')
    urlretrieve(album['thumbnails'][-1]['url'], cover_path)
    return cover_path


TrackInput = tuple[int, types.Album, types.Artist, Path, Path, int, Optional[str]]


def process_album(album: types.AlbumResult, artist: types.Artist, artist_destination: Path, tracks: list[TrackInput]):
    browse_id: str = album['browseId']
    album: types.Album = ytmusic.get_album(browse_id)
    album['browseId'] = browse_id
    album['path'] = database.get_unique_album_path(album, artist)
    alid: int = database.insert_album(album, artist)
    db_tracks: list[str] = database.get_tracks_for_album(alid)
    album_destination: Path = join_and_create(artist_destination, album['path'])
    cover_path = process_thumbnail(album, album_destination)
    video_urls = match_playlist_and_album(album)
    for i in range(len(album['tracks'])):
        track: types.Track = album['tracks'][i]
        video_id: str = database.get_video_id_for_track(track)
        if video_id not in db_tracks:
            tracks.append((i, album, artist, album_destination, cover_path, alid, video_urls[i]))
