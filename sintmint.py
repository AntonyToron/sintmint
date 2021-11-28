#!/usr/bin/env python3
# Author: Antony Toron

from google.cloud import language_v1

class SintMint():

    def __init__(self):
        self.client = language_v1.LanguageServiceClient()

    def analyze_text(self, text):
        document = language_v1.Document(
            content=text,
            type_=language_v1.Document.Type.PLAIN_TEXT
        )

        sentiment = self.client.analyze_sentiment(
            request={"document": document}
        ).document_sentiment

        print("Text: {}".format(text))
        print("Sentiment: {}, {}".format(sentiment.score, sentiment.magnitude))
