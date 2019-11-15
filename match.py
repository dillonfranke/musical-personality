import functools
import requests as r

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from musical_personality.auth import login_required
from musical_personality.db import get_db

bp = Blueprint('match', __name__, url_prefix='/match')

@bp.route('/')
@login_required
def index():
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

    return g.user['spotify_id']