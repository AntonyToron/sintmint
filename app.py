# Author: Antony Toron

from flask import Flask, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from sintmint import *

app = Flask(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

sintmint = SintMint()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/sentiment", methods=["POST"])
@limiter.limit("100 per day")
def sentiment():
    target_entity = request.form["entity"]
    print(target_entity)

    sentiment_score, entity_category = \
        sintmint.get_sentiment_score(target_entity)

    RANGE_RADIUS = 0.3
    sign = -1 if sentiment_score < 0 else 1
    sentiment_score = sign * min(abs(sentiment_score), RANGE_RADIUS)
    sentiment_percent = (abs(sentiment_score) + RANGE_RADIUS) / (RANGE_RADIUS * 2) * 100

    return render_template("sentiment.html",
                           sentiment_score=sentiment_score,
                           sentiment_percent=sentiment_percent,
                           entity_category=entity_category)
