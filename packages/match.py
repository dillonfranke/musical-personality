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
        cur = get_db().execute('SELECT username from user', ())
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
        return render_template('match/match.html')


@bp.route('/clear')
@login_required
def clear():
    db = get_db()
    db.execute(
        '''UPDATE user
        SET songs = NULL
        WHERE id = ?;''',
        (g.user['id'],)
    )
    db.commit()
    return redirect(url_for('match.index'))


def crossExamine(user1Data, user2Data):
    ret = []
    for item in user1Data:
        if (item in user2Data and item not in ret):
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
    playlist_name = "MusicMerge: " + g.user['username'] + " and " + user_to_compare + "'s Shared Songs"

    # Create JSON object that will be added to the POST request body
    playlist_params = json.dumps(
        {
            'name': playlist_name,
            'description': 'An intersection of liked songs, made by Musicality!',
            'public': True
        }
    )

    headers = {'Authorization': 'Bearer ' + g.user['access_token'], 'Content-Type': 'application/json'}

    resp = r.post(url=endpoint_url, data=playlist_params, headers=headers)

    if (resp.ok):
        addSongs(resp.json(), song_list)


@bp.route('/compare', methods = ['GET'])
@login_required
def compare():
    user_to_compare = str(request.query_string)
    user_to_compare = user_to_compare[user_to_compare.find('=') + 1: len(user_to_compare) - 1]

    db = get_db()
    cur = db.execute("SELECT songs from user WHERE username = ?;", (user_to_compare,))
    rv = cur.fetchall()
    cur.close()

    user_to_compare_list = json.loads(rv[0][0])

    curr_user_list = json.loads(g.user['songs'])

    ret = crossExamine(user_to_compare_list, curr_user_list)

    from operator import itemgetter
    ret = sorted(ret, key=itemgetter(1))

    createPlaylist(ret, user_to_compare)
    
    return render_template('song_data.html', data=ret)


@bp.route('/link')
@login_required
def link():
    from requests.utils import quote

    url = 'https://accounts.spotify.com/authorize'
    url += '?client_id=fef838e843a9476fa2c5c874476662fc'
    url += '&response_type=code'
    url += '&redirect_uri=http://musicality.dillonfranke.com/match/callback'
    url += quote('&scope=user-top-read user-library-read playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private', safe='&=-')
    #add state parameter here to prevent CSRF

    return redirect(url)


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
        track_names.append([track.get('name'), track.get('popularity'), track.get('id')])
        only_names.append(track.get('name'))

    for track in song_data2['items']:
        track_names.append([track.get('name'), track.get('popularity'), track.get('id')])
        only_names.append(track.get('name'))

    for track in song_data3['items']:
        track_names.append([track.get('name'), track.get('popularity'), track.get('id')])
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
                track_names.append([item.get('track').get('name'), item.get('track').get('popularity'), item.get('track').get('id')])
                only_names.append(item.get('track').get('name'))
            i += 100

    liked_songs = r.get("https://api.spotify.com/v1/me/tracks", headers=headers1).json()

    while (1):
        for item in liked_songs['items']:
            track_names.append([item.get('track').get('name'), item.get('track').get('popularity'), item.get('track').get('id')])
            only_names.append(item.get('track').get('name'))

        if (liked_songs['next'] == None): break

        liked_songs = r.get(liked_songs['next'], headers=headers1).json()


    return track_names


def getSpotifyId(access_token):
    headers = {'Authorization': 'Bearer ' + str(access_token)}
    user = r.get("https://api.spotify.com/v1/me", headers=headers)
    print(user.content)
    user = user.json()
    return user['id']


def getAuthCode():
    return request.args.get('code')


def getAccessToken(auth_code):
    payload = {'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': 'http://musicality.dillonfranke.com/match/callback', 'client_id': 'fef838e843a9476fa2c5c874476662fc', 'client_secret': 'ab99799453f94d5eba887d7c4a35189e'}
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    req = r.post('https://accounts.spotify.com/api/token', params=payload, headers=headers)

    print("req data" + str(req.content))

    token_data = req.json()
    return token_data.get('access_token')  


@bp.route('/callback')
@login_required
def callback():
    ################### GET AUTHORIZATION CODE ####################
    auth_code = getAuthCode()

    print(auth_code)
    
    ##################### GET ACCESS TOKEN ########################
    access_token = getAccessToken(auth_code)

    print(access_token)

    if not g.user['spotify_id']:
        db = get_db()
        db.execute(
            '''UPDATE user
            SET spotify_id = ?
            WHERE id = ?;''',
            (getSpotifyId(access_token), g.user['id'])
        )
        db.commit()

    db = get_db()
    db.execute(
        '''UPDATE user
        SET access_token = ?
        WHERE id = ?;''',
        (access_token, g.user['id'])
    )
    db.commit()

    return redirect(url_for('match.index'))