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
    channel_id text not null unique,
    topic_channel_id text not null,
    description text,
    name text not null,
    singles integer not null
);
create table if not exists album (
    alid integer primary key,
    title text not null,
    aid integer not null references artist,
    year integer not null,
    track_count integer not null,
    duration integer not null
);
create table if not exists track (
    tid integer primary key,
    title text not null,
    alid integer not null references album,
    video_id text not null,
    duration integer not null,
    track_id integer not null
);
        """)


def insert_artist(artist: types.Artist, no_singles: bool) -> int:
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute('select aid from artist where channel_id = ?', (artist['channelId'],))
        aid = cur.fetchone()
        if not aid:
            cur.execute('''
            insert into artist (channel_id, topic_channel_id, description, name, singles)
            values (?, ?, ?, ?, ?)
            returning aid
            ''', (artist['channelId'], artist['topic_channel_id'], artist['description'], artist['name'], int(not no_singles)))
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


def insert_album(album: types.Album, artist: types.Artist) -> int:
    conn = get_connection()
    with conn:
        aid = get_artist(artist['channelId'])
        cur = conn.cursor()
        cur.execute('select alid from album where aid = ? and title = ?', (aid, album['title']))
        alid = cur.fetchone()
        if not alid:
            cur.execute('''
            insert into album (title, aid, year, track_count, duration)
            values (?, ?, ?, ?, ?)
            returning alid
            ''', (album['title'], aid, int(album['year']), album['trackCount'], album['duration_seconds']))
            alid = cur.fetchone()
    return alid[0]


def check_album_exists(album: types.AlbumResult, artist: types.Artist) -> bool:
    conn = get_connection()
    with conn:
        aid = get_artist(artist['channelId'])
        cur = conn.cursor()
        cur.execute('select alid from album where aid = ? and title = ?', (aid, album['title']))
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
