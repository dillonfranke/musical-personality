from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
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
    
    params = {'ids': ids}
    headers = {'Authorization': 'Bearer ' + str(access_token)}
    url = 'https://api.spotify.com/v1/audio-features/'

    features = r.get(url, params=params, headers=headers)
    features = features.json()

    return features


@app.route('/callback')
def callback():
    ################### GET AUTHORIZATION TOKEN ###################
    auth_code = request.args.get('code')

    payload1 = {'grant_type': 'authorization_code', 'code': auth_code, 'redirect_uri': 'http://127.0.0.1:5000/callback', 'client_id': 'fef838e843a9476fa2c5c874476662fc', 'client_secret': 'ab99799453f94d5eba887d7c4a35189e'}

    headers1 = {'content-type': 'application/x-www-form-urlencoded'}

    req = r.post('https://accounts.spotify.com/api/token', params=payload1, headers=headers1)

    token_data = req.json()
    access_token = token_data.get('access_token')

    print("ACCESS TOKEN: " + str(access_token))

    ################### GET ACTUAL SONG DATA ###################

    payload2 = {'limit': '50', 'offset': '0', 'time_range': 'long_term'}
    headers2 = {'Authorization': 'Bearer ' + str(access_token)}

    tracks_base_url = 'https://api.spotify.com/v1/me/top/tracks'

    song_data = r.get(tracks_base_url, params=payload2, headers=headers2)
    song_data = song_data.json()

    track_names = []

    for track in song_data['items']:
        track_names.append([track.get('name'), track.get('id')])

    print(track_names)

    track_features = getFeatures(track_names, access_token)
        

    return jsonify(track_features)