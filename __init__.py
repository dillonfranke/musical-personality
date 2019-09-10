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

def create_app():
    app = Flask(__name__)

    db.init_app(app)

    return app