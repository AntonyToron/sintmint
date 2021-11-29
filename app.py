# Author: Antony Toron

from flask import Flask, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/sentiment", methods=["POST"])
@limiter.limit("100 per day")
def sentiment():
    target_entity = request.form["entity"]
    return render_template("sentiment.html")
