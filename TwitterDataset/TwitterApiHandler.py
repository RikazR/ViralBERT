from datetime import datetime, timedelta
from searchtweets import collect_results, load_credentials, gen_request_parameters
import requests
import os

USER_ENDPOINT = "https://api.twitter.com/2/users"
TWEET_ENDPOINT = "https://api.twitter.com/2/tweets"
# DATASET_FIELDS = ["text", "id", "author_id", "created_at", "retweets", "likes", "replies", "hashtags", "mentions", "isRT", "followers", "following", "verified"]
TWEET_FIELDS = ["id", "text", "author_id", "created_at", "hashtags", "mentions", "source", "followers", "following", "verified"]
VIRALITY_FIELDS = ["id", "retweets", "likes", "replies", "quotes"]
MEDIA_FIELDS = ["id", "media_key", "type", "url", "preview_image_url"]

# Class for handling Twitter API calls
class TwitterApiHandler:
    def __init__(self, topicLabel, topicQuery, credentials, dataset_dir="./dataset"):
        self.credentials = credentials
        self.label = topicLabel
        self.query = topicQuery
        self.tweets = []
        self.media = []
        self._time = datetime.today() #- timedelta(days=6)
        self.req_headers = {
            "Authorization": f"Bearer {self.credentials.get('bearer_token')}"
        }
        self.dataset_dir = dataset_dir
        
    # get user info given a list of user ids
    def get_user_info(self, user_ids):
        users = []
        for i in range(0, len(user_ids), 100):
            params = {
                "ids": ",".join(user_ids[i: i+100]),
                "user.fields": "public_metrics,verified"
            }
            r = requests.get(USER_ENDPOINT, headers=self.req_headers, params=params)
            users.extend(r.json()["data"])
        return users

    # update tweets for topic with new virality data
    def update_data(self, timedelt=timedelta(hours=1)):
        self._time += timedelt
        print("Updating data for topic:", self.label)
        tweet_ids = [tweet["id"] for tweet in self.tweets]
        for i in range(0, len(tweet_ids), 100):
            params = {
                "ids": ",".join(tweet_ids[i: i+100]),
                "tweet.fields": "public_metrics",
            }
            r = requests.get(TWEET_ENDPOINT, headers=self.req_headers, params=params)
            tweet_list = r.json()["data"]
            for i in range(len(tweet_list)):
                self.tweets[i]["public_metrics"] = tweet_list[i]["public_metrics"]
        self.write_virality()

    def write_virality(self):
        with open(f"{self.dataset_dir}/{self.label}/{self._time.isoformat(timespec='seconds').replace(':', '_')}.csv", "w+", encoding="utf-8") as f:
            # f.write(self._time.isoformat() + "\n")
            f.write(",".join(VIRALITY_FIELDS) + "\n")
            for tweet in self.tweets:
                pub_met = tweet.get("public_metrics")
                data = f"{tweet.get('id')},{pub_met['retweet_count']},{pub_met['like_count']},{pub_met['reply_count']},{pub_met['quote_count']}"
                f.write(data + "\n")

    # remove unnecessary fields from tweet list
    def clean_tweets(self):
        for tweet in self.tweets:
            for field in TWEET_FIELDS:
                if field != "id" and field in tweet:
                    del tweet[field]
        del self.media

    # get tweets + user data for a given topic and save them to a file
    def fetch_data(self, results_per_call=100, max_tweets=1000, tweet_no=1000):
        # total no of tweets will round up to nearest multiple of max_tweets
        self._time = datetime.today() 
        os.makedirs(f"{self.dataset_dir}/{self.label}", exist_ok=True)
        print(f"Getting tweets for topic {self.label}")
        end_time = self._time - timedelta(seconds=10)
        if max_tweets > tweet_no:
            max_tweets = tweet_no
        for _ in range(0, tweet_no, max_tweets):
            end_time = end_time.strftime("%Y%m%d%H%M")
            query = gen_request_parameters(
                f"{self.query} lang:en -is:retweet",
                granularity=None,
                results_per_call=results_per_call,
                end_time=end_time,
                # [attachments,author_id,context_annotations,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,non_public_metrics,organic_metrics,possibly_sensitive,promoted_metrics,public_metrics,referenced_tweets,reply_settings,source,text,withheld]
                tweet_fields="id,created_at,text,public_metrics,author_id,entities,possibly_sensitive,source",
                expansions="attachments.media_keys",
                media_fields="type,url,preview_image_url",
            )
            result = collect_results(query, max_tweets=max_tweets, result_stream_args=self.credentials)

            for data_dict in result:
                if "data" in data_dict:
                    # remove sensitive tweets in data and append to tweets
                    for tweet in data_dict["data"]:
                        if not tweet.get("possibly_sensitive"):
                            self.tweets.append(tweet)
                # check for media
                if "includes" in data_dict:
                    self.media.extend(data_dict["includes"]["media"])
            # end_time = datetime.fromisoformat(self.tweets[-1]["created_at"][:-1])
            end_time = datetime.strptime(self.tweets[-1]["created_at"][:-1], "%Y-%m-%dT%H:%M:%S.%f")
            print(self.label, end_time)

        # get user info
        print(f"{self.label} - Getting user info")
        user_ids = [tweet.get("author_id") for tweet in self.tweets]
        try:
            users = self.get_user_info(user_ids)
            for i in range(len(self.tweets)):
                user_info = {
                    "verified": users[i].get("verified"),
                    "followers": users[i].get("public_metrics").get("followers_count"),
                    "following": users[i].get("public_metrics").get("following_count"),
                }
                self.tweets[i].update(user_info)
        except:
            print(f"{self.label} - Failed to get user info")

        # add media fields 
        print(f"{self.label} - Adding media fields")
        try:
            if self.media:
                media_keys = {self.media[i].get("media_key"): i for i in range(len(self.media))}
                for tweet in self.tweets:
                    if "attachments" in tweet:
                        for key in tweet.get("attachments").get("media_keys"):
                            self.media[media_keys.get(key)].update({"id": tweet.get("id")})
                with open(f"{self.dataset_dir}/{self.label}/media.csv", "w+", encoding="utf-8") as f:
                    f.write(",".join(MEDIA_FIELDS) + "\n")
                    for media_item in self.media:
                        if "id" in media_item:
                            f.write(",".join([str(media_item.get(field, "")) for field in MEDIA_FIELDS]) + "\n")
        except:
            print(f"{self.label} - Failed to get media fields")


        with open(f"{self.dataset_dir}/{self.label}/tweets.csv", "w+", encoding="utf-8") as f:
            f.write(",".join(TWEET_FIELDS) + "\n")
            for tweet in self.tweets:
                if "entities" in tweet:
                    tweet["hashtags"] = len(tweet.get("entities").get("hashtags",[]))
                    tweet["mentions"] = len(tweet.get("entities").get("mentions",[]))
                data = ",".join([str(tweet.get(field, 0)).replace("\n", " ").replace("\r", " ").replace(",", "").replace("\"", "") for field in TWEET_FIELDS]) + "\n"
                f.write(data)
        print(self.label, len(self.tweets))
        self.write_virality()
        self.clean_tweets()
    