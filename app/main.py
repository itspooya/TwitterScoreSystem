from datetime import datetime, timezone
from os import getenv

import psycopg2 as pg
import tweepy
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Union
from dotenv import load_dotenv

app = FastAPI()


class TwitterUser(BaseModel):
    screen_name: Union[str]


# Formula for calculating score
# score 5 = account age > 3650 days and tweets < 10000 and followers < 2000 and ratio of followers to following > 1.2
# and ratio of tweets / retweets in last 1000 tweets > 0.75
# score 4 = account age > 365 * 5 days and tweets < 15000 and followers < 2000 and ratio of followers to following > 1.2
# and ratio of tweets / retweets in last 1000 tweets > 0.75
# score 3 = account age > 365 * 3 days and tweets < 30000 and followers < 3000 and ratio of followers to following > 1
# and ratio of tweets / retweets in last 1000 tweets > 0.75
# score 2 = account age > 365 * 2 days and tweets < 7000 and followers < 2000 and ratio of followers to following > 1
# and ratio of tweets / retweets in last 1000 tweets > 0.75
# score 1 = account age > 365 days and tweets < 3000 and followers < 2000 and ratio of followers to following > 1
# and ratio of tweets / retweets in last 1000 tweets > 0.75
# score 0 = all other cases

# score changers
# if verified account add 3 to score
# if likes / tweets > 100 decrease score by 2
# if 0.5 < followers / following < 1.5 decrease score by 2


class User:
    def __init__(self, username=None):
        load_dotenv()
        self.consumer_key = getenv("CONSUMER_KEY")
        self.consumer_secret = getenv("CONSUMER_SECRET")
        self.access_token = getenv("ACCESS_TOKEN")
        self.access_token_secret = getenv("ACCESS_TOKEN_SECRET")
        self.auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        self.auth.set_access_token(self.access_token, self.access_token_secret)
        self.api = tweepy.API(self.auth, wait_on_rate_limit=True)
        self.postgres_connection = pg.connect(
            host=getenv("POSTGRES_HOST"),
            database=getenv("POSTGRES_DB"),
            user=getenv("POSTGRES_USER"),
            password=getenv("POSTGRES_PASSWORD"),
        )
        self.username = username
        self.id = self.api.get_user(screen_name=self.username).id

    def init_user(self):
        self.tweet_count = self.get_user_tweets_count()
        self.followers_count = self.get_user_followers_count()
        self.following_count = self.get_user_following_count()
        self.likes_count = self.get_user_likes_count()
        self.account_age = self.get_user_account_age()
        self.followers_to_following_ratio = self.get_user_followers_to_following_ratio()
        self.verified_followers = self.find_verified_followers_count()
        self.create_user_table()

    def create_user_table(self):
        cursor = self.postgres_connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS users (id BIGINT PRIMARY KEY, username TEXT, score INT, "
            "created_at TIMESTAMP, updated_at TIMESTAMP)"
        )
        self.postgres_connection.commit()
        cursor.close()

    def get_user_tweets_count(self):
        return self.api.get_user(screen_name=self.username).statuses_count

    def get_user_followers_count(self):
        return self.api.get_user(screen_name=self.username).followers_count

    def get_user_following_count(self):
        return self.api.get_user(screen_name=self.username).friends_count

    def get_user_likes_count(self):
        return self.api.get_user(screen_name=self.username).favourites_count

    def get_user_account_age(self):
        return (
            datetime.now(timezone.utc)
            - self.api.get_user(screen_name=self.username).created_at
        ).days

    def get_user_followers_to_following_ratio(self):
        return self.followers_count / self.following_count

    def find_verified_followers_count(self):
        verified_followers_count = 0
        for follower in tweepy.Cursor(
            self.api.get_followers, screen_name=self.username
        ).items():
            if follower.verified:
                verified_followers_count += 1
        return verified_followers_count

    def check_if_user_verified(self):
        return self.api.get_user(screen_name=self.username).verified

    def get_tweet_to_retweet_ratio(self):
        tweets = self.api.user_timeline(screen_name=self.username, count=1000)
        tweet_count = 0
        retweet_count = 0
        for tweet in tweets:
            if not tweet.retweeted:
                tweet_count += 1
            else:
                retweet_count += 1
        if tweet_count == 0:
            return 0
        if retweet_count == 0:
            return 1
        return tweet_count / retweet_count

    def get_score_from_db(self):
        cursor = self.postgres_connection.cursor()
        cursor.execute("SELECT score FROM users WHERE id = %s", (self.id,))
        score = cursor.fetchone()
        cursor.close()
        return score[0] if score else None

    @property
    def score(self):
        # check if user has been scored before
        score = 0
        if (
            self.account_age > 3650
            and self.tweet_count < 10000
            and self.followers_count < 2000
            and self.followers_to_following_ratio > 1.2
            and self.get_tweet_to_retweet_ratio() > 0.75
        ):
            score = 5
        elif (
            self.account_age > 365 * 5
            and self.tweet_count < 15000
            and self.followers_count < 2000
            and self.followers_to_following_ratio > 1.2
            and self.get_tweet_to_retweet_ratio() > 0.75
        ):
            score = 4
        elif (
            self.account_age > 365 * 3
            and self.tweet_count < 30000
            and self.followers_count < 3000
            and self.followers_to_following_ratio > 1
            and self.get_tweet_to_retweet_ratio() > 0.75
        ):
            score = 3
        elif (
            self.account_age > 365 * 2
            and self.tweet_count < 7000
            and self.followers_count < 2000
            and self.followers_to_following_ratio > 1
            and self.get_tweet_to_retweet_ratio() > 0.75
        ):
            score = 2
        elif (
            self.account_age > 365
            and self.tweet_count < 3000
            and self.followers_count < 2000
            and self.followers_to_following_ratio > 1
            and self.get_tweet_to_retweet_ratio() > 0.75
        ):
            score = 1
        else:
            score = 0
        if self.check_if_user_verified():
            score += 3
        if self.likes_count / self.tweet_count > 100:
            score -= 2
        if 0.5 < self.followers_to_following_ratio < 1.5:
            score -= 2
        if self.verified_followers > 0:
            if self.verified_followers == 1:
                score += 1
            elif 10 > self.verified_followers > 1:
                score += 2
            elif self.verified_followers > 10:
                score += 3
        cursor = self.postgres_connection.cursor()
        cursor.execute(
            "INSERT INTO users (id, username, score, created_at, updated_at) VALUES (%s, %s, %s, %s, "
            "%s)",
            (
                self.id,
                self.username,
                self.score,
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
            ),
        )
        self.postgres_connection.commit()
        cursor.close()
        self.postgres_connection.close()
        return score


# fastapi get score api
@app.get("/score/")
async def get_score(user: TwitterUser):
    if user.screen_name == "" or user.screen_name is None:
        return {"error": "screen_name is required"}
    # check if user has been scored before
    temp_twitter_user = User(user.screen_name)
    db_score = temp_twitter_user.get_score_from_db()
    if db_score:
        return {"score": db_score}
    twitter_user = User(user.screen_name)
    twitter_user.init_user()
    return {"score": twitter_user.score}
