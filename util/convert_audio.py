from pathlib import Path
from subprocess import Popen, PIPE
from util import types
from mutagen.flac import Picture
from mutagen.id3 import PictureType
from base64 import b64encode
from json import loads
from ffmpeg import probe
from typing import List, Optional

from .types import AlbumArtist

INTENDED_I: float = -16.0
INTENDED_TP: float = -1.0
INTENDED_LRA: float = 20.0
NICE_CMD: List[str] = ["nice", "-n", "19"]


class Metadata:
    def __init__(
        self,
        track: str,
        artist: str,
        album: str,
        year: str,
        track_id: int,
        artists: List[AlbumArtist],
    ):
        self.title: str = track
        self.artist: str = artist
        self.album: str = album
        self.year: str = year
        self.track: str = str(track_id)
        self.artists: List[AlbumArtist] = artists

    @staticmethod
    def from_ytmusic(
        track: types.Track,
        track_id: int,
        album: types.Album,
        artist: types.Artist,
    ):
        thumbnail: types.Thumbnail = album["thumbnails"][-1]
        return Metadata(
            track["title"],
            artist["name"],
            album["title"],
            album.get("year", "0"),
            track_id,
            track["artists"],
            thumbnail["width"],
            thumbnail["height"],
        )

    def for_ffmpeg(self) -> list[str]:
        all_attributes: dict[str, str] = {
            "TITLE": self.title,
            "ALBUM": self.album,
            "DATE": self.year,
            "TRACKNUMBER": self.track,
        }
        if types.Options.mp3:
            new_attributes: dict[str, str] = {}
            for key, value in all_attributes.items():
                name: str = key.lower().replace("tracknumber", "track")
                new_attributes[name] = value
            all_attributes = new_attributes
        result = []
        for name, value in all_attributes.items():
            result.append("-metadata")
            result.append(f"{name}={value}")
        if not types.Options.mp3:
            unhandled: List[AlbumArtist] = [
                artist for artist in self.artists if artist["name"] != self.artist
            ]
            for artist in unhandled:
                result.append("-metadata")
                result.append(f'ARTIST={artist["name"]}')
        return result


def level_and_combine_audio(
    tmp_file: str,
    track_path: Path,
    metadata: Metadata,
    seek: Optional[str] = None,
    end: Optional[str] = None,
) -> bool:
    input_modifiers: List[str] = []
    if seek:
        input_modifiers.extend(("-ss", seek))
    if end:
        input_modifiers.extend(("-to", end))
    audio_level_command = [
        *NICE_CMD,
        "ffmpeg",
        "-hide_banner",
        *input_modifiers,
        "-i",
        tmp_file,
        "-af",
        f"loudnorm=I={INTENDED_I}:TP={INTENDED_TP}:LRA={INTENDED_LRA}:print_format=json",
        "-f",
        "null",
        "-",
    ]
    input_metadata = probe(tmp_file)
    stream = input_metadata["streams"][0]
    sample_rate = stream["sample_rate"]
    bit_rate = input_metadata["format"]["bit_rate"]
    output_lines = Popen(
        audio_level_command, universal_newlines=True, stdout=PIPE, stderr=PIPE
    )
    output_lines = output_lines.communicate()[1].split("\n")
    json = loads("\n".join(output_lines[-13:-1]))
    assert -99 <= float(json["input_i"]) <= 0, "measured I out of range"
    assert 0 <= float(json["input_lra"]) <= 99, "measured LRA out of range"
    assert -99 <= float(json["input_tp"]) <= 99, "measured TP out of range"
    assert -99 <= float(json["input_thresh"]) <= 0, "measured thresh out of range"
    assert -99 <= float(json["target_offset"]) <= 99, "target offset out of range"
    loudnorm = (
        f"loudnorm=I={INTENDED_I}:TP={INTENDED_TP}:LRA={INTENDED_LRA}:"
        f'measured_I={json["input_i"]}:measured_LRA={json["input_lra"]}:'
        f'measured_TP={json["input_tp"]}:measured_thresh={json["input_thresh"]}:'
        f'offset={json["target_offset"]}:linear=true,'
        f"aresample=resampler=soxr:out_sample_rate={sample_rate}:precision=33,"
        "aformat=channel_layouts=stereo"
    )
    codec = "libmp3lame" if types.Options.mp3 else "libopus"
    audio_extract_command = [
        *NICE_CMD,
        "ffmpeg",
        "-y",
        "-v",
        "warning",
        *input_modifiers,
        "-i",
        tmp_file,
        "-af",
        loudnorm,
        "-c:a",
        codec,
        "-b:a",
        bit_rate,
        "-vn",
        *metadata.for_ffmpeg(),
        str(track_path),
    ]
    extract = Popen(audio_extract_command)
    extract.wait()
    return extract.returncode == 0
