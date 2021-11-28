#!/usr/bin/env python3
# Author: Antony Toron

# most based on https://googleapis.dev/python/language/latest/usage.html

from google.cloud import language_v1
import urllib.parse, urllib.request

class SintMint():

    def __init__(self):
        self.client = language_v1.LanguageServiceClient()

    # internal, should really only be used on an actual piece of text and not
    # the input text from the user
    def get_text_sentiment(self, text):
        # language field left blank will make the API auto-detect the language
        # content type can be 'HTML' as well, so can provide the raw format
        document = language_v1.Document(
            content=text,
            type_=language_v1.Document.Type.PLAIN_TEXT)

        # also have analyze_entities, which provides proper names or entities
        # in the text, like a person or place, along with a salience (how
        # important it might be)
        response = self.client.analyze_sentiment(
            request={"document": document})

        # magnitude is the overall score from (0, inf) for the whole document
        # or sentence (each sentence also gets analyzed individually) so
        # longer documents are bound to get higher magnitudes.
        return response.document_sentiment.score

    def get_sentiment_score(self, input_text):
        GOOGLE_SEARCH_PAGE = "https://google.com/search?q={}"

        # urllib uses python urllib/3.3.0 as the user agent on the request
        # by default, so we need to go through with using Mozilla or Chrome
        # or something well known to indicate that this isn't a bot with
        # intents to spam
        url = GOOGLE_SEARCH_PAGE.format(urllib.parse.quote(input_text))
        request = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'})
        page_contents = urllib.request.urlopen(request)

        

        print(page_contents.read())

