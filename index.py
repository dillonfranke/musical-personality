from . import db
from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import jsonify
from flask import url_for
from flask import g
import json
import requests as r
import base64
import pdb
from . import auth
from . import match

app = Flask(__name__)
app.config.from_envvar('SETTINGS', silent=True)
app.register_blueprint(auth.bp)
app.register_blueprint(match.bp)

db.init_app(app)

@app.route('/')
def index():
    if (g.user != None):
        return redirect(url_for('match.index'))

    return render_template('index.html')


def getFeatures(track_names, access_token):
    ids = ""

    for entry in track_names:
        ids += entry[1]
        ids += ","
    
    params = {'ids': ids}
    headers = {'Authorization': 'Bearer ' + str(access_token)}
    url = 'https://api.spotify.com/v1/audio-features/'

    features = r.get(url, params=params, headers=headers)
    features = features.json()

    return features


def getGenres(track_names, response):
    full_data = []
    response = response.json()

    count = 0
    for entry in response['artists']:
        a = {'track_name': track_names[count][0], 'track_id': track_names[count][1], 'artist_name': entry.get('name'), 'genres': entry.get('genres')}
        full_data.append(a)
        count += 1

    return full_data


def getInfo(track_names, access_token):
    ids = ""

    for entry in track_names:
        ids += entry[2].get('id')
        ids += ","

    ids = ids[:-1]
    
    params = {'ids': ids}
    headers = {'Authorization': 'Bearer ' + str(access_token)}
    url = 'https://api.spotify.com/v1/artists'

    response = r.get(url, params=params, headers=headers)

    return getGenres(track_names, response)


def createGenreMap(full_data):
    genreMap = dict()
    for entry in full_data:
        for genre in entry.get('genres'):
            if (genreMap.get(genre) == None):
                genreMap[genre] = 1
            else:
                genreMap[genre] += 1
    
    return genreMap


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if (request.method == 'POST'):
        one = request.form.get('one')

    url = 'https://accounts.spotify.com/authorize'
    url += '?client_id=fef838e843a9476fa2c5c874476662fc'
    url += '&response_type=code'
    url += '&redirect_uri=http://127.0.0.1:5000/callback'
    url += '&scope=user-top-read'
    #add state parameter here to prevent CSRF

    return redirect(url)


def crossExamine(user1Data, user2Data):
    ret = []
    for item in user1Data:
        if (item in user2Data and item not in ret):
            ret.append(item)

    return ret


def getAuthCode():
    return request.args.get('code')


def getAccessToken(auth_code):
    payload = {'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': 'http://127.0.0.1:5000/callback', 'client_id': 'fef838e843a9476fa2c5c874476662fc', 'client_secret': 'ab99799453f94d5eba887d7c4a35189e'}
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    req = r.post('https://accounts.spotify.com/api/token', params=payload, headers=headers)

    token_data = req.json()
    return token_data.get('access_token')


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


@app.route('/callback')
def callback():
    global user1Data, user2Data
    # return crossExamine(user1Data, user2Data)

    ################### GET AUTHORIZATION CODE ####################
    auth_code = getAuthCode()
    
    ##################### GET ACCESS TOKEN ########################
    access_token = getAccessToken(auth_code)

    ################### GET ACTUAL SONG DATA ######################
    user1Data = getUserData(access_token)

    return render_template('song_data.html', data=user1Data)

    # url = 'https://accounts.spotify.com/authorize'
    # url += '?client_id=fef838e843a9476fa2c5c874476662fc'
    # url += '&response_type=code'
    # url += '&redirect_uri=http://127.0.0.1:5000/callback2'
    # url += '&show_dialog=true'
    # url += '&scope=user-top-read'
    # #add state parameter here to prevent CSRF

    # return redirect(url)






    # full_data = getInfo(track_names, access_token)

    # genre_map = createGenreMap(full_data)

    # print(genre_map)
    
    # ### If you end up wanting to use features like danceability, etc.
    # #track_features = getFeatures(track_names, access_token)

    # return jsonify(full_data)


@app.route('/callback2')
def callback2():
    global user1Data, user2Data
    # return crossExamine(user1Data, user2Data)

    pdb.set_trace()

    ################### GET AUTHORIZATION CODE ####################
    auth_code = getAuthCode()
    
    ##################### GET ACCESS TOKEN ########################

    payload = {'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': 'http://127.0.0.1:5000/callback2', 'client_id': 'fef838e843a9476fa2c5c874476662fc', 'client_secret': 'ab99799453f94d5eba887d7c4a35189e'}
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    req = r.post('https://accounts.spotify.com/api/token', params=payload, headers=headers)

    token_data = req.json()
    access_token = token_data.get('access_token')

    ################### GET ACTUAL SONG DATA ######################
    user2Data = getUserData(access_token)

    data = crossExamine(user1Data, user2Data)

    return render_template('song_data.html', data=data)