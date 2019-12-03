import os
from packages import db
from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import jsonify
from flask import url_for
from flask import g
from flask import send_from_directory
from flask import current_app
import logging
import json
import requests as r
import base64
import pdb
from packages import auth
from packages import match
from packages.db import dump_db

app = Flask(__name__)
app.config.from_envvar('SETTINGS', silent=True)
app.register_blueprint(auth.bp)
app.register_blueprint(match.bp)

# gunicorn_logger = logging.getLogger('gunicorn.error')
# app.logger.handlers = gunicorn_logger.handlers
# app.logger.setLevel(gunicorn_logger.level)

db.init_app(app)

@app.route('/')
def index():
    if (g.user != None):
        return redirect(url_for('match.index'))

    return render_template('index.html')


@app.route('/db/dump')
def dump():
    dump_db()
    tmp = os.path.join(current_app.root_path, 'tmp')
    return send_from_directory(directory=tmp, filename='/tmp/db_dump.sql')
    
    