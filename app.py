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
@limiter.limit("3 per day")
def sentiment():
    target_entity = request.form["entity"]
    print(target_entity)

    sentiment_score, entity_category = \
        sintmint.get_sentiment_score(target_entity)

    # generally, articles will not have extremely polarizing words about
    # people throughout, to make the score reach the [-1.0, 1.0] bounds
    # to make the range a bit more realistic, we should go from ~[-0.3, 0.3]
    # and clamp at that
    RANGE_RADIUS = 0.3
    sign = -1 if sentiment_score < 0 else 1
    sentiment_score = sign * min(abs(sentiment_score), RANGE_RADIUS)
    sentiment_percent = (sentiment_score + RANGE_RADIUS) / (RANGE_RADIUS * 2) * 100

    abs_score = abs(sentiment_score)
    verbal_sentiment_prefix = ""
    if abs_score < (RANGE_RADIUS / 3):
        verbal_sentiment_prefix = "slightly "
    elif abs_score > ((RANGE_RADIUS / 3) * 2):
        verbal_sentiment_prefix = "very "

    verbal_sentiment_suffix = "positive" if sentiment_score >= 0 else "negative"
    verbal_sentiment = verbal_sentiment_prefix + verbal_sentiment_suffix

    displayed_percent = round(abs_score / RANGE_RADIUS * 100, 2)

    return render_template("sentiment.html",
                           sentiment_score=sentiment_score,
                           sentiment_percent=sentiment_percent,
                           entity_category=entity_category,
                           target_entity=target_entity,
                           displayed_percent=displayed_percent,
                           verbal_sentiment_suffix=verbal_sentiment_suffix,
                           verbal_sentiment=verbal_sentiment)
