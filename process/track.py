from pathlib import Path
from typing import Optional

from pathvalidate import sanitize_filename
from pytube import YouTube, Stream

from youtubesearchpython import SearchVideos

from util import types, convert_audio, database
from util.io import eprint


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
    extension = 'mp3' if types.Options.mp3 else 'ogg'
    track_path: Path = album_destination.joinpath(f'{track_id:02} - {sanitize_filename(track["title"])}.{extension}')
    video: Optional[YouTube] = None
    if track['videoId']:
        video = YouTube(f'https://youtube.com/watch?v={track["videoId"]}')
    if not video or video.channel_id != artist['topic_channel_id']:
        video_id = get_alternative_track_id(track, album, artist)
        if video_id:
            video = YouTube(f'https://youtube.com/watch?v={video_id}')
    if not video:
        raise RuntimeError('Did not find any matching video at all')
    stream: Optional[Stream]
    if types.Options.mp3:
        stream = video.streams.get_audio_only(subtype='mp4')
    else:
        stream = video.streams.get_audio_only(subtype='webm')
    if not stream:
        video.streams.get_audio_only()
    track_tmp_path = stream.download(output_path=str(album_destination), filename_prefix=str(track_id))
    metadata: convert_audio.Metadata = convert_audio.Metadata(track, track_id, album, artist, cover_path)
    convert_success: bool = convert_audio.level_and_combine_audio(track_tmp_path, track_path, metadata)
    if convert_success:
        Path(track_tmp_path).unlink()
        database.insert_track(alid, track, track_id)
    else:
        eprint(f'Warning: could not process track {track["title"]} from album {album["title"]}')
