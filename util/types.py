from typing import TypedDict, Optional
from pathlib import Path


class Thumbnail(TypedDict):
    url: str
    width: int
    height: int


class AlbumResult(TypedDict):
    title: str
    year: str
    browseId: str
    thumbnails: list[Thumbnail]


class SingleResult(TypedDict):
    title: str
    year: str
    browseId: str
    thumbnails: list[Thumbnail]


class AlbumResults(TypedDict):
    browseId: Optional[str]
    results: list[AlbumResult]
    params: Optional[str]


class SingleResults(TypedDict):
    browseId: Optional[str]
    results: list[SingleResult]
    params: Optional[str]


class Artist(TypedDict):
    topic_channel_id: str
    description: str
    views: str
    name: str
    channelId: str
    thumbnails: list[Thumbnail]
    albums: AlbumResults
    singles: SingleResults


class AlbumArtist(TypedDict):
    name: str
    id: str


class Track(TypedDict):
    videoId: str
    title: str
    artists: list[AlbumArtist]
    album: str
    duration: str
    duration_seconds: int
    thumbnails: Optional[list[Thumbnail]]
    isAvailable: bool
    isExplicit: bool


class Album(TypedDict):
    title: str
    thumbnails: list[Thumbnail]
    artists: list[AlbumArtist]
    year: str
    trackCount: int
    duration: str
    duration_seconds: int
    tracks: list[Track]
    audioPlaylistId: str


class Options:
    processing_threads: int
    background: bool
    album_only: bool


class ResultTrack(TypedDict):
    title: str
    album: str
    artist: str
    id: str


class ResultAlbum(TypedDict):
    title: str
    artist: str


class ResultError(TypedDict):
    title: str
    album: str
    artist: str
    id: str
    traceback: str


class Result(TypedDict):
    tracks: list[ResultTrack]
    albums: dict[str, ResultAlbum]
    errors: list[ResultError]


ResultTuple = tuple[list[ResultTrack], dict[str, ResultAlbum], list[ResultError]]


class Arguments:
    threads: int
    background: bool
    album_only: bool
    name: list[str]
    destination: Path
    channel_id: list[str]
