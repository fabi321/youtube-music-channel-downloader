import sqlite3
import pathlib
import threading
from util import types

db_path: pathlib.Path
thread_local = threading.local()


def get_connection() -> sqlite3.Connection:
    conn = getattr(thread_local, 'connection', None)
    if conn is None:
        conn = sqlite3.Connection(db_path, timeout=1.0)
        thread_local.connection = conn
    return conn


def init(path: pathlib.Path):
    global db_path
    db_path = path
    conn = get_connection()
    with conn:
        conn.executescript("""
create table if not exists artist (
    aid integer primary key,
    name text not null,
    channel_id text not null unique,
    topic_channel_id text not null,
    description text,
    singles integer not null,
    path text not null unique
);
create table if not exists album (
    alid integer primary key,
    browse_id text not null unique,
    title text not null,
    aid integer not null references artist on delete cascade,
    year integer not null,
    track_count integer not null,
    duration integer not null,
    path text not null,
    unique (path, aid)
);
create table if not exists track (
    tid integer primary key,
    title text not null,
    alid integer not null references album on delete cascade,
    video_id text not null,
    duration integer not null,
    track_id integer not null
);
        """)


def get_unique_artist_path(artist: types.Artist) -> str:
    conn = get_connection()
    if result := conn.execute('select path from artist where channel_id = ?', (artist['channelId'],)).fetchone():
        return result[0]
    result: str = artist['name']
    iteration: int = 0
    while conn.execute('select * from artist where path = ?', (result,)).fetchone():
        iteration += 1
        result = f'{artist["name"]}-{iteration}'
    return result


def insert_artist(artist: types.Artist, no_singles: bool) -> int:
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute('select aid from artist where channel_id = ?', (artist['channelId'],))
        aid = cur.fetchone()
        if not aid:
            cur.execute('''
            insert into artist (name, channel_id, topic_channel_id, description, singles, path)
            values (?, ?, ?, ?, ?, ?)
            returning aid
            ''', (artist['name'], artist['channelId'], artist['topic_channel_id'], artist['description'], int(not no_singles), artist['path']))
            aid = cur.fetchone()
        else:
            cur.execute('''
                update artist
                    set singles = ?
                where aid = ?
            ''', (int(not no_singles), aid[0]))
    return aid[0]


def get_artists() -> list[tuple[str, bool]]:
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute('select channel_id, singles from artist')
        res = cur.fetchall()
    return [(i[0], not bool(i[1])) for i in res]


def get_artist(channel_id: str) -> int:
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute('select aid from artist where channel_id = ?', (channel_id,))
        aid = cur.fetchone()
    return aid[0]


def get_unique_album_path(album: types.Album, artist: types.Artist) -> str:
    conn = get_connection()
    if result := conn.execute('select path from album where browse_id = ?', (album['browseId'],)).fetchone():
        return result[0]
    result: str = album['title']
    iteration: int = 0
    aid: int = get_artist(artist['channelId'])
    while conn.execute('select path from album where path = ? and aid = ?', (result, aid)).fetchone():
        iteration += 1
        result = f'{album["title"]}-{iteration}'
    return result


def insert_album(album: types.Album, artist: types.Artist) -> int:
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute('select alid from album where browse_id = ?', (album['browseId'],))
        alid = cur.fetchone()
        if not alid:
            aid = get_artist(artist['channelId'])
            cur.execute('''
            insert into album (browse_id, title, aid, year, track_count, duration, path)
            values (?, ?, ?, ?, ?, ?, ?)
            returning alid
            ''', (album['browseId'], album['title'], aid, int(album.get('year', '0')), album['trackCount'], album['duration_seconds'], album['path']))
            alid = cur.fetchone()
    return alid[0]


def check_album_exists(album: types.AlbumResult) -> bool:
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute('select alid from album where browse_id = ?', (album['browseId'],))
        alid = cur.fetchone()
    return alid is not None


def get_tracks_for_album(alid: int) -> list[str]:
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute('select video_id from track where alid = ?', (alid,))
        res = cur.fetchall()
    return [i[0] for i in res]


def get_video_id_for_track(track: types.Track) -> str:
    video_id: str = track['videoId']
    if not video_id:
        # for whatever stupid reason, this keeps happening from time to time
        video_id = track['title']
    return video_id


def insert_track(alid: int, track: types.Track, track_id: int) -> int:
    conn = get_connection()
    with conn:
        video_id: str = get_video_id_for_track(track)
        cur = conn.cursor()
        cur.execute('select tid from track where video_id = ? and alid = ?', (video_id, alid))
        tid = cur.fetchone()
        if not tid:
            cur.execute('''
            insert into track (title, alid, video_id, duration, track_id)
            values (?, ?, ?, ? ,?)
            returning tid
            ''', (track['title'], alid, video_id, track.get('duration_seconds', -1), track_id))
            tid = cur.fetchone()
    return tid[0]
