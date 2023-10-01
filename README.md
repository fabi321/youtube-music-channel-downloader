# youtube-music-channel-downloader
Download music from youtube music by artist, in the highest available quality.

This project aims to provide a simple way of downloading tracks for an artist, and also enables to regularly update the music library with new albums in an automated fashion.

## Quick start

```commandline
git clone https://github.com/fabi321/youtube-music-channel-downloader.git
cd youtube-music-channel-downloader
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Afterward, you can use it as following:
### Add new artist using search
```commandline
python main.py <path to library> <artist name>
```
It will probably prompt you, to select an artist from the list of matching artists, and will download all songs and
albums afterward.

### Add new artist using channel id
```commandline
python main.py <path to library> -c <channel id>
```

### Update all existing artists in a library, downloading new albums
```commandline
python main.py <path to library> -a
```
This will only check for new albums.

### Update all existing artists in a library, downloading new songs
```commandline
python main.py <path to library>
```
This will check every album, even already discovered ones, and check all songs.
Has the side effect of retrying all previously failed songs.

### Add an "album video"
There are some videos, that include an entire album. There is a utility to download, split and normalize such videos
```commandline
python process_album_video.py <path to library> <video id>
```
It will ask to add artist and album info, tell you the inferred list of songs, and finally process them.
This utility won't add songs to the libraries database, as the database is reserved for automatic fetching.
If there are issues with the inferred title list, feel free to open an issue.

## Usage:
```
usage: main.py [-h] [--threads THREADS] [--background] [--album-only] [--channel-id [CHANNEL_ID ...]] [--mp3] [--no-singles] D [N ...]

Download all music videos from a "* - Topic" channel. It will check all existing channels if neither names nor ChannelIds are supplied

positional arguments:
  D                     The directory of the music collection
  N                     The name of the channel

options:
  -h, --help            show this help message and exit
  --threads THREADS, -t THREADS
                        The number of processing threads, default: 6
  --background, -b      Run in Background mode, only returning a final json
  --album-only, -a      Only investigate unknown albums, do not check all individual tracks
  --channel-id [CHANNEL_ID ...], -c [CHANNEL_ID ...]
                        Specify ChannelIds to check
  --mp3                 produce mp3 files instead of ogg files
  --no-singles          Do not download singles for the supplied artists
```

## Background mode

If one adds `-b` to any command, there won't be any progress bar, but instead a final json object, describing all new
songs and albums, structured as follows:
```json
{
  "tracks": [
    {
      "id": "<youtube video id>",
      "title": "<title>",
      "album": "<album>",
      "artist": "<artist>"
    }
  ],
  "albums": {
    "<album playlist id>": {
      "title": "<album title>",
      "artist": "<artist>"
    }
  },
  "errors": [
    {
      "title": "<title>",
      "album": "<album>",
      "artist": "<artist>",
      "traceback": "<traceback or short description>",
      "id": "<video id, might be null>"
    }
  ]
}
```

there are short descriptions for known issues, currently the following issues exist:
 - Did not find any matching video at all
   - Usually means that there are actually no videos on YouTube
   - If you have this issue, and there is a valid video that should have been picked, open an issue
 - Age restricted
