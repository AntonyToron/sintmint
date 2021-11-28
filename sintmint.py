#!/usr/bin/env python3
# Author: Antony Toron

# most based on https://googleapis.dev/python/language/latest/usage.html

from google.cloud import language_v1
import urllib.parse, urllib.request
from html.parser import HTMLParser
import time

DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " \
                     "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
DEFAULT_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9," \
                 "*/*;q=0.8"

class BasicHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.links = []

    def handle_starttag(self, tag, attrs):
        # we only really care about links
        if tag != 'a':
            return

        for attr, value in attrs:
            if attr != 'href':
                continue

            # seems to come after most links that are not back to another
            # google page within the webpage
            STANDARD_LINK_PREFIX = "/url?q="
            if not value.startswith(STANDARD_LINK_PREFIX):
                continue

            # sometimes there are ad-related links for google that we can skip
            # (this might not always be a good heuristic)
            # some really hacky heuristics for links we don't want to follow:
            # - google ad-based links
            if "google" in value:
                continue

            link = value[len(STANDARD_LINK_PREFIX):].split("&")[0]
            self.links.append(link)

class SintMint():

    def __init__(self):
        self.client = language_v1.LanguageServiceClient()
        self.parser = BasicHTMLParser()

    # internal, should really only be used on an actual piece of text and not
    # the input text from the user
    def get_text_sentiment(self, html_text):
        # language field left blank will make the API auto-detect the language
        # content type can be 'HTML' as well, so can provide the raw format
        # TODO getting 0.0s for all of the HTML stuff
        document = language_v1.Document(
            content=html_text,
            type_=language_v1.Document.Type.HTML)

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

        self.parser.feed(page_contents.read().decode())

        # follow the links on the main page, and then those will collectively
        # construct our info on the initial input text
        # limit to some finite number (e.g. 10) links so that we don't have to
        # request too many times
        # TODO need to cap it somewhere or can we just do all links?
        NUM_LINKS_TO_CHECK = 1
        top_links = set(self.parser.links[:NUM_LINKS_TO_CHECK])
        all_contents = []
        for link in top_links:
            print(link)
            request = urllib.request.Request(
                link,
                headers={"User-Agent": DEFAULT_USER_AGENT,
                         "Accept": DEFAULT_ACCEPT})
            page_contents = urllib.request.urlopen(request)
            all_contents.append(page_contents.read().decode())

            # so that we don't HTTP Error 429 for too many requests
            # TODO: can catch that error and try again later
            DEFAULT_TIMEOUT = 0.1
            time.sleep(DEFAULT_TIMEOUT)


        # tested empirically
        MAX_GOOGLE_REQUEST_SIZE = 1000000
        SIZE_CAP = MAX_GOOGLE_REQUEST_SIZE - int(MAX_GOOGLE_REQUEST_SIZE / 10)

        all_contents = "\n".join(all_contents)[:SIZE_CAP]

        # to minimize requests to google, bundle up all of the text into one
        # (does this work well even when providing type of data = HTML?)
        sentiment = self.get_text_sentiment(all_contents)
        print(sentiment)
