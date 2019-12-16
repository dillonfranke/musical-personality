import functools
import requests as r
import json
import pdb

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from packages.auth import login_required
from packages.db import get_db

bp = Blueprint('match', __name__, url_prefix='/match')

@bp.route('/')
@login_required
def index():
    if (g.user['songs']):
        cur = get_db().execute('SELECT * from user', ())
        rv = cur.fetchall()
        cur.close()
        user_list = rv
        return render_template('match/match.html', users=user_list, data=json.loads(g.user['songs']))
    elif (g.user['access_token']):
        user1_data = getUserData(g.user['access_token'])
        db = get_db()
        db.execute(
            '''UPDATE user
            SET songs = ?
            WHERE id = ?;''',
            (str(json.dumps(user1_data)), g.user['id'])
        )
        db.commit()
        return redirect(url_for('match.index'))
    else:
        return render_template('index.html')


@bp.route('/clear')
def clear():
    if g.user:
        db = get_db()
        db.execute(
            '''UPDATE user
            SET songs = NULL
            WHERE id = ?;''',
            (g.user['id'],)
        )
        db.commit()
        return redirect(url_for('auth.link'))
    else:
        return redirect(url_for('index.html'))


def crossExamine(user1_data, user2_data):
    ret = []
    user2_data_artists = [row[3] for row in user2_data]
    user2_data_names = [row[0] for row in user2_data]
    for item in user1_data:
        if ((item[0] in user2_data_names and item[3] in user2_data_artists) and item not in ret):
            ret.append(item)

    user1_data_artists = [row[3] for row in user1_data]
    user1_data_names = [row[0] for row in user1_data]
    for item in user2_data:
        if ((item[0] in user1_data_names and item[3] in user1_data_artists) and item not in ret):
            ret.append(item)

    return ret


def addSongs(playlist, song_list):
    endpoint_url = playlist['tracks']['href']

    song_list = ['spotify:track:' + str(row[2]) for row in song_list]

    while (1):
        i = 100
        done = False
        if (len(song_list) < 100):
            done = True
            i = len(song_list)

        track_params = json.dumps(
            {
                'uris': song_list[:i]
            }
        )

        song_list = song_list[i:]

        headers = {'Authorization': 'Bearer ' + g.user['access_token'], 'Content-Type': 'application/json'}

        resp = r.post(url=endpoint_url, data=track_params, headers=headers)

        if (not resp.ok):
            print("ERROR" + str(i))

        if (done): break



def createPlaylist(song_list, user_to_compare):
    endpoint_url = "https://api.spotify.com/v1/users/" + g.user['spotify_id'] + "/playlists"
    playlist_name = "musicmerge.dillonfranke.com: " + user_to_compare + " and " + g.user['display_name'] + "'s Perfect Playlist"

    # Create JSON object that will be added to the POST request body
    playlist_params = json.dumps(
        {
            'name': playlist_name,
            'description': 'An intersection of liked songs, made by MusicMerge! Check out http://musicmerge.dillonfranke.com to create the perfect playlist of your own!',
            'public': True
        }
    )

    print(playlist_params)

    headers = {'Authorization': 'Bearer ' + g.user['access_token'], 'Content-Type': 'application/json'}

    resp = r.post(url=endpoint_url, data=playlist_params, headers=headers)

    if (resp.ok):
        addSongs(resp.json(), song_list)


@bp.route('/compare', methods = ['GET'])
@login_required
def compare():
    id_to_compare = str(request.query_string)
    id_to_compare = id_to_compare[id_to_compare.find('=') + 1: len(id_to_compare) - 1]

    db = get_db()
    cur = db.execute("SELECT songs from user WHERE spotify_id = ?;", (id_to_compare,))
    rv = cur.fetchall()
    cur.close()

    user_to_compare_list = json.loads(rv[0][0])

    curr_user_list = json.loads(g.user['songs'])

    ret = crossExamine(user_to_compare_list, curr_user_list)

    from operator import itemgetter
    ret = sorted(ret, key=itemgetter(1))

    cur = db.execute("SELECT display_name from user WHERE spotify_id = ?;", (id_to_compare,))
    user_to_compare = cur.fetchone()[0]
    cur.close()

    createPlaylist(ret, user_to_compare)
    
    return render_template('song_data.html', data=ret)


# In the future return a tuple of song name and ID, since ID is better for searching
def getUserData(access_token):
    # Currently a hard cap of 50 top songs that you can fetch
    payload1 = {'limit': '100', 'offset': '0', 'time_range': 'long_term'}
    headers1 = {'Authorization': 'Bearer ' + str(access_token)}

    tracks_base_url = 'https://api.spotify.com/v1/me/top/tracks'

    song_data1 =  r.get(tracks_base_url, params=payload1, headers=headers1)
    payload1 = {'limit': '100', 'offset': '0', 'time_range': 'medium_term'}

    song_data2 = r.get(tracks_base_url, params=payload1, headers=headers1)
    payload1 = {'limit': '100', 'offset': '0', 'time_range': 'short_term'}

    song_data3 = r.get(tracks_base_url, params=payload1, headers=headers1)

    song_data1 = song_data1.json()
    song_data2 = song_data2.json()
    song_data3 = song_data3.json()

    track_names = []
    only_names = []

    for track in song_data1['items']:
        track_names.append([track.get('name'), track.get('popularity'), track.get('id'), track.get('artists')[0].get('name')])
        only_names.append(track.get('name'))

    for track in song_data2['items']:
        track_names.append([track.get('name'), track.get('popularity'), track.get('id'), track.get('artists')[0].get('name')])
        only_names.append(track.get('name'))

    for track in song_data3['items']:
        track_names.append([track.get('name'), track.get('popularity'), track.get('id'), track.get('artists')[0].get('name')])
        only_names.append(track.get('name'))

    ################## GET PLAYLIST DATA ####################
    # Get User ID
    user = r.get("https://api.spotify.com/v1/me", headers=headers1)
    user = user.json()
    userID = user['id']

    userPlaylists = r.get("https://api.spotify.com/v1/users/" + userID + "/playlists", headers=headers1)

    userPlaylists = userPlaylists.json()

    for playlistObj in userPlaylists['items']:
        i = 0
        # We only want to get playlists that the user has created
        if (playlistObj['owner']['id'] != userID): continue

        # Loop through all the tracks of the playlist, (multiple requests w/ offset param req'd)
        while (i < int(playlistObj['tracks']['total'])):
            params1 = {'limit': '100', 'offset': str(i)}
            playlist = r.get(playlistObj['tracks']['href'], params=params1, headers=headers1)
            playlist = playlist.json()
            for item in playlist['items']:
                track_names.append([item.get('track').get('name'), item.get('track').get('popularity'), item.get('track').get('id'), item.get('track').get('artists')[0].get('name')])
                only_names.append(item.get('track').get('name'))
            i += 100

    liked_songs = r.get("https://api.spotify.com/v1/me/tracks", headers=headers1).json()

    while (1):
        for item in liked_songs['items']:
            track_names.append([item.get('track').get('name'), item.get('track').get('popularity'), item.get('track').get('id'), item.get('track').get('artists')[0].get('name')])
            only_names.append(item.get('track').get('name'))

        if (liked_songs['next'] == None): break

        liked_songs = r.get(liked_songs['next'], headers=headers1).json()

    return track_names