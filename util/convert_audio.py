from pathlib import Path
from subprocess import Popen, PIPE
from util import types
from mutagen.flac import Picture
from mutagen.id3 import PictureType
from base64 import b64encode
from json import loads
from ffmpeg import probe

intended_i = -16.0
intended_tp = -1.0
intended_lra = 20.0
nice_cmd = ['nice', '-n', '19']

class Metadata:
    def __init__(self, track: types.Track, track_id: int, album: types.Album, artist: types.Artist, cover_path: Path):
        self.title: str = track['title']
        self.artist: str = artist['name']
        self.album: str = album['title']
        self.year: str = album['year']
        self.track: str = str(track_id)
        thumbnail: types.Thumbnail = album['thumbnails'][-1]
        picture = Picture()
        with open(cover_path, 'rb') as f:
            picture.data = f.read()
        picture.type = PictureType().COVER_FRONT
        picture.mime = u'image/jpeg'
        picture.width = thumbnail['width']
        picture.height = thumbnail['height']
        self.cover: str = b64encode(picture.write()).decode()

    def for_ffmpeg(self) -> list[str]:
        all_attributes: dict[str, str] = {
            'TITLE': self.title,
            'ARTIST': self.artist,
            'ALBUM': self.album,
            'DATE': self.year,
            'TRACKNUMBER': self.track,
            #'METADATA_BLOCK_PICTURE': self.cover
        }
        if types.Options.mp3:
            new_attributes: dict[str, str] = {}
            for key, value in all_attributes.items():
                name: str = key.lower().replace('tracknumber', 'track')
                new_attributes[name] = value
            all_attributes = new_attributes
        result = []
        for (name, value) in all_attributes.items():
            result.append('-metadata')
            result.append(f'{name}={value}')
        return result

def level_and_combine_audio(tmp_file: str, track_path: Path, metadata: Metadata) -> bool:
    audio_level_command = [*nice_cmd, 'ffmpeg', '-hide_banner', '-i', tmp_file, '-af',
                f'loudnorm=I={intended_i}:TP={intended_tp}:LRA={intended_lra}:print_format=json', '-f', 'null', '-']
    input_metadata = probe(tmp_file)
    stream = input_metadata['streams'][0]
    sample_rate = stream['sample_rate']
    bit_rate = input_metadata['format']['bit_rate']
    output_lines = Popen(audio_level_command, universal_newlines=True, stdout=PIPE, stderr=PIPE)
    output_lines = output_lines.communicate()[1].split('\n')
    json = loads('\n'.join(output_lines[-13:-1]))
    loudnorm = (f'loudnorm=I={intended_i}:TP={intended_tp}:LRA={intended_lra}:'
                f'measured_I={json["input_i"]}:measured_LRA={json["input_lra"]}:'
                f'measured_TP={json["input_tp"]}:measured_thresh={json["input_thresh"]}:'
                f'offset={json["target_offset"]}:linear=true,'
                f'aresample=resampler=soxr:out_sample_rate={sample_rate}:precision=28,'
                'aformat=channel_layouts=stereo')
    codec = 'libmp3lame' if types.Options.mp3 else 'libopus'
    audio_extract_command = [*nice_cmd, 'ffmpeg', '-y', '-v', 'warning', '-i',  tmp_file, '-af', loudnorm,
                '-c:a', codec, '-b:a', bit_rate, '-vn', *metadata.for_ffmpeg(), str(track_path)]
    extract = Popen(audio_extract_command)
    extract.wait()
    return extract.returncode == 0
