import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

import requests as r

from packages.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/loading')
def loading():
    return render_template('auth/loading.html', code=getAuthCode())


@bp.route('/link')
def link():
    from requests.utils import quote

    url = 'https://accounts.spotify.com/authorize'
    url += '?client_id=fef838e843a9476fa2c5c874476662fc'
    url += '&response_type=code'
    url += '&redirect_uri=http://127.0.0.1:5000/auth/loading'
    # url += '&redirect_uri=http://musicmerge.dillonfranke.com/auth/loading'
    url += quote('&scope=user-top-read user-library-read playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private', safe='&=-')
    #add state parameter here to prevent CSRF
    return redirect(url)


def getAuthCode():
    # TODO: Add error-handling here
    print("Auth code: " + request.args.get('code'))
    return request.args.get('code')

def getAccessToken(auth_code):
    payload = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': 'http://127.0.0.1:5000/auth/loading',
        # 'redirect_uri': 'http://musicmerge.dillonfranke.com/auth/loading',
        'client_id': 'fef838e843a9476fa2c5c874476662fc',
        'client_secret': 'ab99799453f94d5eba887d7c4a35189e'
    }
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    resp = r.post('https://accounts.spotify.com/api/token', params=payload, headers=headers)

    print(resp)

    print(resp.content)

    token_data = resp.json()

    return token_data.get('access_token')

def getSpotifyId(access_token):
    headers = {'Authorization': 'Bearer ' + str(access_token)}
    user = r.get("https://api.spotify.com/v1/me", headers=headers)
    print(user)
    user = user.json()
    return user['id']

def getDisplayName(spotify_id, access_token):
    headers = {'Authorization': 'Bearer ' + str(access_token)}
    user = r.get("https://api.spotify.com/v1/users/" + str(spotify_id), headers=headers)
    user = user.json()
    # TODO: check if no display name is set
    return user['display_name']


@bp.route('/login')
def login():

    ################### GET AUTHORIZATION CODE ####################
    auth_code = getAuthCode()
    
    ##################### GET ACCESS TOKEN ########################
    access_token = getAccessToken(auth_code)

    spotify_id = getSpotifyId(access_token)

    display_name = getDisplayName(spotify_id, access_token)

    db = get_db()
    user = db.execute(
            'SELECT * FROM user WHERE spotify_id = ?', (spotify_id,)
        ).fetchone()

    if user is None:
        # Add user to the database
        db.execute(
            'INSERT INTO user (spotify_id, display_name, auth_code, access_token) VALUES (?, ?, ?, ?)',
            (spotify_id, display_name, auth_code, access_token)
        )
        db.commit()
        session.clear()
        user = db.execute(
            'SELECT * FROM user WHERE spotify_id = ?', (spotify_id,)
            ).fetchone()
        session['user_id'] = user['id']

    else:
        # User already exists, fetch them
        session.clear()
        session['user_id'] = user['id']
        db = get_db()
        db.execute(
            '''UPDATE user
            SET access_token = ?, auth_code = ?
            WHERE id = ?;''',
            (access_token, auth_code, g.user['id'])
        )
        db.commit()

    return redirect(url_for('match.index'))


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('index'))

        return view(**kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()