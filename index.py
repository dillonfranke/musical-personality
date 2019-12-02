from packages import db
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
from packages import auth
from packages import match

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