from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import jsonify
import tensorflow as tf
import json
import requests as r
import base64

app = Flask(__name__)

@app.route('/')
def index():
    url = 'https://accounts.spotify.com/authorize'
    url += '?client_id=fef838e843a9476fa2c5c874476662fc'
    url += '&response_type=code'
    url += '&redirect_uri=http://127.0.0.1:5000/callback'
    url += '&scope=user-top-read'
    #add state parameter here to prevent CSRF

    return render_template('index.html', url=url)


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


@app.route('/callback')
def callback():
    ################### GET AUTHORIZATION TOKEN ###################
    auth_code = request.args.get('code')

    payload1 = {'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': 'http://127.0.0.1:5000/callback', 'client_id': 'fef838e843a9476fa2c5c874476662fc', 'client_secret': 'ab99799453f94d5eba887d7c4a35189e'}

    headers1 = {'content-type': 'application/x-www-form-urlencoded'}

    req = r.post('https://accounts.spotify.com/api/token', params=payload1, headers=headers1)

    token_data = req.json()
    access_token = token_data.get('access_token')

    ################### GET ACTUAL SONG DATA ###################

    payload2 = {'limit': '100', 'offset': '0', 'time_range': 'short_term'}
    headers2 = {'Authorization': 'Bearer ' + str(access_token)}

    tracks_base_url = 'https://api.spotify.com/v1/me/top/tracks'

    song_data = r.get(tracks_base_url, params=payload2, headers=headers2)
    song_data = song_data.json()

    track_names = []
    only_names = []

    for track in song_data['items']:
        track_names.append([track.get('name'), track.get('id'), track.get('artists')[0]])
        only_names.append(track.get('name'))

    return render_template('song_data.html', data=only_names)

    full_data = getInfo(track_names, access_token)

    genre_map = createGenreMap(full_data)

    print(genre_map)
    
    ### If you end up wanting to use features like danceability, etc.
    #track_features = getFeatures(track_names, access_token)

    return jsonify(full_data)