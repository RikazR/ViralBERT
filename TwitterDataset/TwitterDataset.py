from datetime import timedelta
import time
from searchtweets import load_credentials
import logging
import os
import concurrent.futures
from TwitterApiHandler import TwitterApiHandler
import json
from math import ceil, floor

TOPIC_COUNTRY_ID = "23424977" # United States
TOPIC_ENDPOINT = "https://api.twitter.com/1.1/trends/place.json"
DEFAULT_TOPICS = {
    # label: search_term
    # can use context annotations - https://developer.twitter.com/en/docs/twitter-api/annotations/overview
    "crypto": "context:66.913142676819648512",
    "tv_movie": "context:46.781974597105094656",
    "pets": "context:65.852262932607926273",
    "video_games": "context:46.781974597218340864",
    "cell_phones": "context:66.848920700073123840",
    # "marvel": "context:130.1002576732971384832",
    "covid": "context:123.1220701888179359745",
    "football": "context:11.733756536430809088",
    "kpop": "context:55.888105153038958593",
}

REQUEST_LIMIT = 200 * 100 # max number of tweets per 15 minutes

# Class for using the Twitter API handler
class TwitterDataset:
    def __init__(self, timedelt=timedelta(hours=1), threads=10, dataset_dir="./dataset"):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Twitter Dataset")
        self.credentials = load_credentials("./.twitter_keys.yaml", yaml_key="search_tweets_v2", env_overwrite=False)
        self.req_headers = {
            "Authorization": f"Bearer {self.credentials.get('bearer_token')}"
        }
        os.makedirs(dataset_dir, exist_ok=True)
        logging.basicConfig(
            handlers=[logging.FileHandler(filename="./events.log", encoding='utf-8', mode='a+')],
            level=logging.DEBUG
        )
        self.topics = {}
        self.api_handlers = []
        self.timedelt=timedelt
        # if timedelt < timedelta(minutes=15):
        #     self.logger.warning("Timedelta is less than 15 minutes, setting to 15 minutes")
        #     self.timedelt = timedelta(minutes=15)
        self.threads=threads
        self.topics_per_15 = 0
        self.tweets_per_topic = 1000
        self.dataset_dir = dataset_dir

    def set_threads(self, threads):
        self.threads = threads

    # load topics from file, if no file is given, use default topics
    def load_topics(self, topicFile=None):
        if topicFile is None:
            self.topics = DEFAULT_TOPICS
        else:
            with open(topicFile, "r", encoding="utf-8") as f:
                self.topics = json.load(f)
        self.logger.debug(f"Topics: {self.topics.keys()}")
        return self.topics

    # initialise api handler object for each topic
    def init_api_handlers(self):
        self.logger.debug("Initializing api handlers")
        # create api handler objects for each topic
        for label, query in self.topics.items():
            self.api_handlers.append(TwitterApiHandler(label, query, self.credentials, self.dataset_dir))

    def _get_tweets_from_handler(self, apiHandler):
        self.logger.info(f"Getting tweets for topic: {apiHandler.label}")
        return apiHandler.fetch_data(tweet_no=self.tweets_per_topic)
        # print(self.api_handlers.index(apiHandler))
    
    def _update_tweets_from_handler(self, apiHandler):
        self.logger.info(f"Updating tweets for topic: {apiHandler.label}")
        return apiHandler.update_data(self.timedelt)

    # get tweets for each topic using threads
    def get_tweets(self):
        # maximise tweet count per 15 minutes
        no_of_fetches = self.timedelt // timedelta(minutes=15)
        self.topics_per_15 = ceil(len(self.topics) / no_of_fetches)
        self.tweets_per_topic = floor(REQUEST_LIMIT // self.topics_per_15 / 1000) * 1000
        
        self.logger.debug(f"No of fetches: {no_of_fetches}")
        self.logger.debug(f"Topics per fetch: {self.topics_per_15}")
        self.logger.debug(f"Requests per topic: {self.tweets_per_topic}")
        
        self.logger.debug("Getting tweets")
        self.tweet_handler(self._get_tweets_from_handler)
        # self.api_handlers[0].fetch_data(tweet_no=100)
    
    # update tweets for each topic using threads
    def update_tweets(self):
        self.logger.debug("Updating tweets")
        self.tweet_handler(self._update_tweets_from_handler)
        # self.api_handlers[0].update_data(self.timedelt)

    # helper function for fetch tweets and update tweets that uses threads
    def tweet_handler(self, func):
        time_left = self.timedelt
        for i in range(0, len(self.api_handlers), self.topics_per_15):
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
                executor.map(func, self.api_handlers[i:i+self.topics_per_15])
            self.logger.info(f"Got tweets for topics {i} to {i+self.topics_per_15}")
            print("sleeping")
            time.sleep(15*60) # sleep for 15 minutes
            time_left -= timedelta(minutes=15)
        time.sleep(time_left.total_seconds())

