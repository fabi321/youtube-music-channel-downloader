from pathlib import Path
from time import sleep
from typing import Optional

from pathvalidate import sanitize_filename
from pytubefix import YouTube, Stream, exceptions

from util import types, convert_audio, database
from util.io import eprint
from .util import video_search

from fuzzywuzzy import fuzz


def merge_description(description: list[types.YoutubeSearchDescriptionSnippet]) -> str:
    result = ""
    for snippet in description:
        result += snippet["text"]
    return result


def score_result(
    result: types.YoutubeSearchVideoResult,
    track: types.Track,
    album: types.Album,
) -> tuple[float, str]:
    score = 0.0
    track_title: str = track["title"].lower()
    album_title: str = album["title"].lower()
    result_title: str = result["title"].lower()
    if result["title"] == track["title"]:
        # exact title match
        score += 5
    else:
        # is exactly 4 in case it's a perfect match
        score += fuzz.ratio(result_title, track_title) / 100 * 4
    # track might not have a duration. In that case, this will always be false
    if result["duration"] == track.get("duration"):
        # exact duration match
        score += 3
    description: str = merge_description(result["descriptionSnippet"]).lower()
    # the description usually contains both track and album title
    if track_title == album_title:
        # if both are the same, it should be contained twice (usually singles)
        if description.count(track_title) == 2:
            score += 2
    else:
        # if they are different, and the album is present
        if album_title in description:
            score += 2
    # the year is usually included as copyright, might be wrong
    # The null character is definitely not present in the description, in case a year is missing
    if album.get("year", "\0") in description:
        score += 1
    return score, result["id"]


def search_and_pick(
    search_query: str, track: types.Track, album: types.Album
) -> Optional[str]:
    search = video_search(search_query)
    # score all results
    scored = [score_result(result, track, album) for result in search]
    # sort by score in reverse order (biggest score first)
    scored.sort(key=lambda x: -x[0])
    if scored and scored[0][0] > 1:
        return scored[0][1]


def get_alternative_track_id(
    track: types.Track, album: types.Album, artist: types.Artist
) -> Optional[str]:
    short_title: str = track["title"].split("(")[0].split('"')[0]
    short_album: str = album["title"].split("(")[0].split('"')[0]
    result = search_and_pick(
        f'{artist["name"]} - topic "provided to youtube by" {album["title"]} {track["title"]} "{short_album}" "{short_title}"',
        track,
        album,
    )
    return result


def get_stream(video_url: str) -> Stream:
    video: Optional[YouTube] = YouTube(video_url)
    video.visitor_data
    stream: Optional[Stream]
    if types.Options.mp3:
        stream = video.streams.get_audio_only(subtype="mp4")
    else:
        stream = video.streams.get_audio_only(subtype="webm")
    if not stream:
        stream = video.streams.get_audio_only()
    if not stream:
        stream = video.streams.get_highest_resolution()
    return stream


def process_track(
    track: types.Track,
    artist: types.Artist,
    track_path: Path,
    cover_path: Path,
    track_id: int,
    album: types.Album,
    video_url: Optional[str],
) -> bool:
    if not video_url:
        raise RuntimeError("Did not find any matching video at all")
    try:
        stream = get_stream(video_url)
    except exceptions.AgeRestrictedError:
        raise RuntimeError("Age restricted")
    except exceptions.BotDetection:
        print("Waiting 30min due to bot detection")
        sleep(30*60) # 30min sleep
        stream = get_stream(video_url)

    track_tmp_path = stream.download(
        output_path=str(track_path.parent), filename_prefix=str(track_id)
    )
    metadata: convert_audio.Metadata = convert_audio.Metadata.from_ytmusic(
        track, track_id, album, artist, cover_path
    )
    convert_success: bool = convert_audio.level_and_combine_audio(
        track_tmp_path, track_path, metadata
    )
    if convert_success:
        Path(track_tmp_path).unlink()
    return convert_success


def process_album_track(
    track_id: int,
    album: types.Album,
    artist: types.Artist,
    album_destination: Path,
    cover_path: Path,
    alid: int,
    video_url: Optional[str],
):
    track: types.Track = album["tracks"][track_id]
    track_id += 1
    extension = "mp3" if types.Options.mp3 else "opus"
    track_path: Path = album_destination.joinpath(
        f'{track_id:02} - {sanitize_filename(track["title"])}.{extension}'
    )
    convert_success: bool = process_track(
        track, artist, track_path, cover_path, track_id, album, video_url
    )
    if convert_success:
        database.insert_track(alid, track, track_id)
    else:
        eprint(
            f'Warning: could not process track {track["title"]} from album {album["title"]}'
        )
