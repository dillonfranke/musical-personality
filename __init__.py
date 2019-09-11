from . import db
from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import jsonify
import json
import requests as r
import base64
import pdb
#from . import auth

def create_app():
    app = Flask(__name__)

    app.config.from_envvar('SETTINGS', silent=True)
    #app.register_blueprint(auth.bp)

    db.init_app(app)

    return app