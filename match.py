import functools
import requests as r
import json
import pdb

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from musical_personality.auth import login_required
from musical_personality.db import get_db

bp = Blueprint('match', __name__, url_prefix='/match')

@bp.route('/')
@login_required
def index():
    if (g.user['songs']):
        return render_template('match/match.html', data=json.loads(g.user['songs']))
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
        return render_template('match/match.html', data=json.loads(g.user['songs']))
    else:
        return render_template('match/match.html')


def getSpotifyId(access_token):
    headers = {'Authorization': 'Bearer ' + str(access_token)}
    user = r.get("https://api.spotify.com/v1/me", headers=headers)
    user = user.json()
    return user['id']


def getAuthCode():
    return request.args.get('code')


def getAccessToken(auth_code):
    payload = {'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': 'http://127.0.0.1:5000/match/callback', 'client_id': 'fef838e843a9476fa2c5c874476662fc', 'client_secret': 'ab99799453f94d5eba887d7c4a35189e'}
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    req = r.post('https://accounts.spotify.com/api/token', params=payload, headers=headers)

    token_data = req.json()
    return token_data.get('access_token')


@bp.route('/link')
@login_required
def link():
    url = 'https://accounts.spotify.com/authorize'
    url += '?client_id=fef838e843a9476fa2c5c874476662fc'
    url += '&response_type=code'
    url += '&redirect_uri=http://127.0.0.1:5000/match/callback'
    url += '&scope=user-top-read'
    #add state parameter here to prevent CSRF

    return redirect(url)


# In the future return a tuple of song name and ID, since ID is better for searching
def getUserData(access_token):
    # Currently a hard cap of 50 top songs that you can fetch
    payload1 = {'limit': '100', 'offset': '0', 'time_range': 'short_term'}
    headers1 = {'Authorization': 'Bearer ' + str(access_token)}

    tracks_base_url = 'https://api.spotify.com/v1/me/top/tracks'

    song_data1 =  r.get(tracks_base_url, params=payload1, headers=headers1)
    payload1 = {'limit': '100', 'offset': '0', 'time_range': 'medium_term'}

    song_data2 = r.get(tracks_base_url, params=payload1, headers=headers1)
    payload1 = {'limit': '100', 'offset': '0', 'time_range': 'long_term'}

    song_data3 = r.get(tracks_base_url, params=payload1, headers=headers1)

    song_data1 = song_data1.json()
    song_data2 = song_data2.json()
    song_data3 = song_data3.json()

    track_names = []
    only_names = []

    for track in song_data1['items']:
        track_names.append([track.get('name'), track.get('id'), track.get('artists')[0]])
        only_names.append(track.get('name'))

    for track in song_data2['items']:
        track_names.append([track.get('name'), track.get('id'), track.get('artists')[0]])
        only_names.append(track.get('name'))

    for track in song_data3['items']:
        track_names.append([track.get('name'), track.get('id'), track.get('artists')[0]])
        only_names.append(track.get('name'))

    ################## GET PLAYLIST DATA ####################
    # Get User ID
    user = r.get("https://api.spotify.com/v1/me", headers=headers1)
    user = user.json()
    userID = user['id']

    userPlaylists = r.get("https://api.spotify.com/v1/users/" + userID + "/playlists", headers=headers1)

    userPlaylists = userPlaylists.json()

    # Still need to specify the offset to get the entire playlist
    for playlistObj in userPlaylists['items']:
        playlist = r.get(playlistObj['tracks']['href'], headers=headers1)
        playlist = playlist.json()
        for item in playlist['items']:
            track_names.append([item.get('track').get('name'), item.get('track').get('id'), item.get('track').get('artists')[0]])
            only_names.append(item.get('track').get('name'))

    return only_names


@bp.route('/callback')
@login_required
def callback():
    ################### GET AUTHORIZATION CODE ####################
    auth_code = getAuthCode()
    
    ##################### GET ACCESS TOKEN ########################
    access_token = getAccessToken(auth_code)

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