#!/usr/bin/env python3
# Author: Antony Toron

# most based on https://googleapis.dev/python/language/latest/usage.html

from google.cloud import language_v1
import urllib.parse, urllib.request
from urllib.error import HTTPError
from html.parser import HTMLParser
import time
from helpers import *
import requests
from lxml.html.clean import Cleaner

DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " \
                     "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
DEFAULT_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9," \
                 "*/*;q=0.8"

# tested empirically
MAX_GOOGLE_REQUEST_SIZE = 1000000
SIZE_CAP = MAX_GOOGLE_REQUEST_SIZE - int(MAX_GOOGLE_REQUEST_SIZE / 10)

# actually 20 via https://cloud.google.com/natural-language/docs/basics but
# buffering a bit
MIN_GOOGLE_REQUEST_SIZE = 100

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

class TextInfo():
    def __init__(self, score, magnitude, categories, site, content_length):
        self.score = score
        self.magnitude = magnitude
        self.categories = categories
        self.site = site
        self.content_length = content_length

    def __str__(self):
        return "Sentiments for '{}':\n" \
               "Score: {}\n" \
               "Magnitude: {}\n" \
               "Categories: {}".format(
                    self.site,
                    self.score,
                    self.magnitude,
                    self.categories)

class Sentiment():
    def __init__(self, score, magnitude, name):
        self.score = score
        self.magnitude = magnitude
        self.name = name

    def __str__(self):
        return "Sentiment '{}': {} score, {} magnitude".format(
            self.name,
            self.score,
            self.magnitude)

class SintMint():

    def __init__(self):
        self.client = language_v1.LanguageServiceClient()
        self.parser = BasicHTMLParser()
        self.cleaner = Cleaner(page_structure=True,
                               scripts=True,
                               javascript=True,
                               comments=True,
                               style=True,
                               inline_style=True,
                               links=True,
                               meta=True,
                               processing_instructions=True,
                               embedded=True,
                               frames=True,
                               forms=True,
                               annoying_tags=True)

    # internal, should really only be used on an actual piece of text and not
    # the input text from the user
    def get_text_annotations(self, html_text):
        #return language_v1.types.AnnotateTextResponse()

        # language field left blank will make the API auto-detect the language
        document = language_v1.Document(
            content=html_text,
            type_=language_v1.Document.Type.HTML)

        # also have analyze_entities, which provides proper names or entities
        # in the text, like a person or place, along with a salience (how
        # important it might be)
        # magnitude is the overall score from (0, inf) for the whole document
        # or sentence (each sentence also gets analyzed individually) so
        # longer documents are bound to get higher magnitudes.
        features = {
            "extract_syntax": False,
            "extract_entities": True,
            "extract_document_sentiment": True,
            "extract_entity_sentiment": True,
            "classify_text": True
        }

        # TODO catch errors here
        response = self.client.annotate_text(
            document=document,
            features=features)

        return response

    def normalize_magnitudes(self, magnitudes):
        if len(magnitudes) == 0:
            return magnitudes

        # magnitudes can range from [0, inf), so we need to take the sum of the
        # magnitudes we find in the list and use that to bound our magnitudes
        # so we can get actual weights
        total_magnitude = sum(magnitudes)
        if equal_with_tolerance(total_magnitude, 0.0):
            return magnitudes

        magnitudes = [magnitude / total_magnitude for magnitude in magnitudes]
        return magnitudes

    def get_mention_weight(self, mention_text, target_entity):
        # gives a higher score for how many words in the target entity
        # appear in the mention text
        words_appeared = 0
        words = target_entity.split(" ")
        for word in words:
            if word in mention_text:
                words_appeared += 1

        return float(words_appeared) / len(words)

    def get_entity_sentiment(self, google_response, target_entity):
        entity_scores = []
        entity_magnitudes = []

        for entity in google_response.entities:
            # these seem to get sorted by salience roughly, so we can break
            # when we start hitting really low salience numbers
            LOW_SALIENCE = 0.001
            if entity.salience < LOW_SALIENCE:
                break

            # sometimes, google can consider wrong words as part of the entity
            # so we need to examine the mentions of the entities. usually, the
            # entities at the top of the list of entities are important, so
            # we should look at the mentions and see the overall sentiment there
            score = entity.sentiment.score
            magnitude = entity.sentiment.magnitude
            if equal_with_tolerance(score, 0):
                # we're going to need to look at the mentions to get a good
                # idea of the sentiment
                mention_scores = []
                mention_magnitudes = []
                for mention in entity.mentions:
                    if equal_with_tolerance(mention.sentiment.score, 0):
                        continue

                    mention_weight = self.get_mention_weight(
                        mention.text.content,
                        target_entity)

                    mention_scores.append(
                        mention.sentiment.score * mention_weight)
                    mention_magnitudes.append(mention.sentiment.magnitude)

                mention_weights = \
                    self.normalize_magnitudes(mention_magnitudes)
                score = get_weighted_average(mention_scores, mention_weights)

            entity_scores.append(score)
            entity_magnitudes.append(magnitude)

        entity_weights = self.normalize_magnitudes(entity_magnitudes)
        entity_score = get_weighted_average(entity_scores, entity_weights)

        return Sentiment(entity_score, sum(entity_magnitudes), 'entity')

    def get_sentence_sentiment(self, google_response, target_entity):
        sentence_scores = []
        sentence_magnitudes = []
        for sentence in google_response.sentences:
            if equal_with_tolerance(sentence.sentiment.score, 0):
                continue

            mention_weight = self.get_mention_weight(sentence.text.content,
                                                     target_entity)

            # we still want to count sentences in general, but give a bit
            # more weight to those that actually include the target entity
            mention_weight += 1

            sentence_scores.append(sentence.sentiment.score)
            sentence_magnitudes.append(
                sentence.sentiment.magnitude * mention_weight)
        
        sentence_weights = self.normalize_magnitudes(sentence_magnitudes)
        sentence_score = get_weighted_average(sentence_scores,
                                              sentence_weights)

        return Sentiment(sentence_score, sum(sentence_magnitudes), 'sentence')

    def analyze_text_annotations(self,
                                 google_response,
                                 target_entity,
                                 site,
                                 content_length):
        # we will determine the overall sentiment of the person/phrase as
        # follows:
        # - hopefully find the person as an entity in the list of entities
        #   (note that they can occur as a substring of an entity, if there
        #   exists a museum, etc.)
        # - combine the sentiments for all of the entities that match the
        #   criteria in the previous bullet point, and taking their weighted
        #   average (with weights corresponding to their saliency)
        # - then, fetch the document overall score as well, if it is valid
        # - additionally factor in each sentence score within the document.
        #   each sentence gets a sentiment score, so based on the score of
        #   each sentence, assuming it has a score that is nonzero (via
        #   some threshold e.g. 0.001), then take that and the magnitude and
        #   compute an overall score for that sentence. then factor that
        #   into the overal document score
        # - then, we will combine the document score and the entity score and
        #   the sentence score determine the overall score/sentiment
        # TODO determine which combination of which scores seems to give better
        # results. maybe different combinations will give better scores for
        # different content types?

        entity_sentiment = self.get_entity_sentiment(google_response,
                                                     target_entity)

        document_sentiment = Sentiment(
            google_response.document_sentiment.score,
            google_response.document_sentiment.magnitude,
            'document')


        sentence_sentiment = self.get_sentence_sentiment(google_response,
                                                         target_entity)

        # combine results
        all_sentiments = [
            entity_sentiment,
            document_sentiment,
            sentence_sentiment
        ]
        total_scores = []
        total_magnitudes = []
        for sentiment in all_sentiments:
            print(sentiment)

            if equal_with_tolerance(sentiment.score, 0) or \
               equal_with_tolerance(sentiment.magnitude, 0):
                continue

            total_scores.append(sentiment.score)
            total_magnitudes.append(sentiment.magnitude)

        total_weights = self.normalize_magnitudes(total_magnitudes)
        total_score = get_weighted_average(total_scores, total_weights)

        categories = []
        for category in google_response.categories:
            splits = category.name.split("/")
            categories.append((splits[-1], category.confidence))

        return TextInfo(total_score,
                        sum(total_magnitudes),
                        categories,
                        site,
                        content_length)

    def decode_page(self, page_contents):
        try:
            return page_contents.decode(encoding="utf-8")
        except:
            try:
                return page_contents.decode(encoding="latin-1")
            except:
                return page_contents.decode(encoding="utf-8", errors="replace")

    def get_sentiment_score(self, target_entity):
        GOOGLE_SEARCH_PAGE = "https://google.com/search?q={}"

        # urllib uses python urllib/3.3.0 as the user agent on the request
        # by default, so we need to go through with using Mozilla or Chrome
        # or something well known to indicate that this isn't a bot with
        # intents to spam
        # TODO: empirically, it seems like better results come up when
        # prefixing searches to include "opinion" in them
        google_search = "opinion of {}".format(target_entity)
        url = GOOGLE_SEARCH_PAGE.format(urllib.parse.quote(google_search))
        request = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'})
        page_contents = urllib.request.urlopen(request)

        self.parser.feed(page_contents.read().decode())

        # follow the links on the main page, and then those will collectively
        # construct our info on the initial input text
        # limit to some finite number (e.g. 3) links so that we don't have to
        # request too many times
        seen_links = set()
        unique_links = [link for link in self.parser.links if not \
                        (link in seen_links or seen_links.add(link))]
        text_infos = []
        links_fetched = 0
        NUM_LINKS_TO_CHECK = 3
        for link in unique_links:
            print(link)
            request = urllib.request.Request(
                link,
                headers={"User-Agent": DEFAULT_USER_AGENT,
                         "Accept": DEFAULT_ACCEPT})

            try:
                page_contents = urllib.request.urlopen(request)

                # skip over non-html pages (e.g. PDFs) for now to avoid having
                # to deal with downloads etc. (maybe PDFs will be good at some
                # point for scholarly articles)
                header = page_contents.info()
                if "text/html" not in header["content-type"]:
                    continue

            except HTTPError as err:
                # TODO catch only 404 and https cert errors?
                continue

            page_contents = self.cleaner.clean_html(
                self.decode_page(page_contents.read()))

            # can't use it in this case
            if len(page_contents) > MAX_GOOGLE_REQUEST_SIZE or \
               len(page_contents) < MIN_GOOGLE_REQUEST_SIZE:
                continue

            # we can alternatively bundle up all of the text into one pile and
            # sent that in one request, but it might be better to get sentiment
            # analysis from different texts separately, and weight the documents
            # that have higher saliency for the target more
            text_annotations = self.get_text_annotations(page_contents)
            text_info = self.analyze_text_annotations(text_annotations,
                                                      target_entity,
                                                      link,
                                                      len(page_contents))
            text_infos.append(text_info)

            links_fetched += 1
            if links_fetched == NUM_LINKS_TO_CHECK:
                break

            # so that we don't HTTP Error 429 for too many requests
            # TODO: can catch that error and try again later
            GOOGLE_REQUEST_TIMEOUT = 1
            time.sleep(GOOGLE_REQUEST_TIMEOUT)

        # across the text infos, add up the scores, computing a weight or
        # salience as the magnitude relative to the total magnitude we saw
        # across all of the texts
        text_scores = []
        text_magnitudes = []
        text_lengths = []
        for text_info in text_infos:
            print(text_info)

            # TODO should we factor in texts that have scores close to 0?
            # that will probably reflect in the magnitude anyway?
            text_scores.append(text_info.score)
            text_magnitudes.append(text_info.magnitude)
            text_lengths.append(text_info.content_length)

        # we don't want to get overly biased by one long article (e.g.
        # a wikipedia page), so lets normalize magnitudes by the article
        # lengths (since magnitude inevitably gets larger for longer articles)
        # TODO check if this calculation needs any tweaks to make it better
        text_length_weights = self.normalize_magnitudes(text_lengths)
        text_magnitudes = [a * (1 - b) for a, b in \
                           zip(text_magnitudes, text_length_weights)]

        text_weights = self.normalize_magnitudes(text_magnitudes)
        total_score = get_weighted_average(text_scores, text_magnitudes)

        print("Overall sentiment score for {}: {}".format(target_entity,
                                                          total_score))
