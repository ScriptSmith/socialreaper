from os import environ
from time import time, sleep

import requests
import requests.auth
from requests_oauthlib import OAuth1

from .exceptions import *


class API:
    def __init__(self):
        self.log_function = print
        self.retry_rate = 5
        self.num_retries = 5
        self.failed_last = False
        self.common_errors = (requests.exceptions.ConnectionError,
                              requests.exceptions.Timeout,
                              requests.exceptions.HTTPError)

    def log_error(self, e):
        """
        Print errors. Stop travis-ci from leaking api keys

        :param e: The error
        :return: None
        """

        if not environ.get('CI'):
            self.log_function(e)

    def get(self, *args, **kwargs):

        """
        An interface for get requests that handles errors more gracefully to
        prevent data loss
        """

        try:
            req = requests.get(*args, **kwargs)
            req.raise_for_status()
            self.failed_last = False
            return req

        except self.common_errors as e:
            self.log_error(e)
            for i in range(1, self.num_retries):
                sleep_time = self.retry_rate * i
                self.log_function("Retrying in %s seconds" % sleep_time)
                sleep(sleep_time)
                try:
                    req = requests.get(*args, **kwargs)
                    req.raise_for_status()
                    self.log_function("New request successful")
                    return req
                except self.common_errors:
                    self.log_function("New request failed")

            # Allows for the api to ignore one potentially bad request
            if not self.failed_last:
                self.failed_last = True
                raise ApiError(e)
            else:
                raise FatalApiError(e)

        except requests.exceptions.RequestException as e:
            raise FatalApiError(e)


class Youtube(API):
    def __init__(self, api_key):
        super().__init__()

        self.key = api_key
        self.url = "https://www.googleapis.com/youtube/v3"
        self.request_rate = 2
        self.last_request = time()

    def api_call(self, edge, parameters, return_results=True):
        req = self.get("%s/%s" % (self.url, edge), params=parameters)

        time_diff = time() - self.last_request
        if time_diff < self.request_rate:
            sleep(time_diff)

        self.last_request = time()

        if return_results:
            return req.json()

    def search(self, query, count=50, order="relevance", page='',
               result_type="video", channel_id=None, channel_type=None,
               event_type=None, location=None, location_radius=None,
               published_after=None, published_before=None, region_code=None,
               relevance_language=None, safe_search=None, topic_id=None,
               video_caption=None, video_category_id=None,
               video_definition=None, video_dimension=None,
               video_duration=None, video_embeddable=None,
               video_license=None, video_syndicated=None, video_type=None,
               params=None):

        count = 50 if count > 50 else count
        parameters = {"part": "snippet",
                      "q": query,
                      "maxResults": count,
                      "order": order,
                      "type": result_type,
                      "channelId": channel_id,
                      "channelType": channel_type,
                      "eventType": event_type,
                      "location": location,
                      "locationRadius": location_radius,
                      "publishedAfter": published_after,
                      "publishedBefore": published_before,
                      "regionCode": region_code,
                      "relevanceLanguage": relevance_language,
                      "safeSearch": safe_search,
                      "topicId": topic_id,
                      "videoCaption": video_caption,
                      "videoCategoryId": video_category_id,
                      "videoDefinition": video_definition,
                      "videoDimension": video_dimension,
                      "videoDuration": video_duration,
                      "videoEmbeddable": video_embeddable,
                      "videoLicense": video_license,
                      "videoSyndicated": video_syndicated,
                      "videoType": video_type,
                      "pageToken": page,
                      "key": self.key}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('search', parameters)

    def guess_channel_id(self, username, count=5):
        parameters = {
            "forUsername": username,
            "part": "id",
            "maxResults": count,
            "key": self.key
        }
        return self.api_call('channels', parameters)['items']

    def channel(self, channel_id, count=50, order="date", page='',
                result_type="video", params=None):

        count = 50 if count > 50 else count
        parameters = {"part": "snippet,id",
                      "channelId": channel_id,
                      "maxResults": count,
                      "order": order,
                      "type": result_type,
                      "pageToken": page,
                      "key": self.key}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('search', parameters)

    def videos(self, video_ids, count=50, page='', params=None):
        parts = ["contentDetails", "id", "liveStreamingDetails",
                 "localizations", "player", "recordingDetails", "snippet",
                 "statistics", "status", "topicDetails"]
        parameters = {
            "part": ",".join(parts),
            "id": ",".join(video_ids),
            "maxResults": count,
            "pageToken": page,
            "key": self.key
        }
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('videos', parameters)

    def video_comments(self, video_id, count=100, order="time", page='',
                       search_terms=None, text_format="html", params=None):

        count = 50 if count > 50 else count
        if type(search_terms) is list:
            search_terms = ",".join(search_terms)

        parts = ["id", "replies", "snippet"]
        parameters = {
            "part": ",".join(parts),
            "videoId": video_id,
            "maxResults": count,
            "order": order,
            "searchTerms": search_terms,
            "textFormat": text_format,
            "pageToken": page,
            "key": self.key
        }
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('commentThreads', parameters)

    def channel_comments(self, channel_id, count=100, order="time", page='',
                         search_term="", text_format="html", params=None):

        count = 100 if count > 100 else count
        parts = ["id", "replies", "snippet"]
        parameters = {
            "part": ",".join(parts),
            "allThreadsRelatedToChannelId": channel_id,
            "maxResults": count,
            "order": order,
            "search_term": search_term,
            "text_format": text_format,
            "pageToken": page,
            "key": self.key
        }
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('commentThreads', parameters)


class Reddit(API):
    def __init__(self, application_id, application_secret):
        super().__init__()
        self.retry_rate /= 2  # Because it will try reauthorise if failure

        self.application_id = application_id
        self.application_secret = application_secret

        self.url = "https://oauth.reddit.com"
        self.request_rate = 5
        self.user_agent = "SocialReaper/0.1"
        self.headers = {}
        self.token_expiry = 0
        self.requires_reauth = True

        self.auth()
        self.last_request = time()

    def auth(self):
        client_auth = requests.auth.HTTPBasicAuth('%s' % self.application_id,
                                                  '%s' % self.application_secret)
        post_data = {"grant_type": "client_credentials"}
        headers = {"User-Agent": self.user_agent}

        try:
            response = requests.post("https://www.reddit.com/api/v1/access_token",
                                     auth=client_auth, data=post_data,
                                     headers=headers)
        except requests.exceptions.RequestException as e:
            raise ApiError(e)

        rj = response.json()

        self.headers = {"Authorization": "bearer %s" % rj['access_token'],
                        "User-Agent": self.user_agent}
        self.token_expiry = time() + rj['expires_in']

    def api_call(self, edge, parameters, return_results=True):

        if time() > self.token_expiry + 30:
            self.auth()

        time_diff = time() - self.last_request
        if time_diff < self.request_rate:
            sleep(time_diff)

        self.last_request = time()

        try:
            req = self.get("%s/%s" % (self.url, edge), params=parameters,
                           headers=self.headers)
        except (ApiError, FatalApiError):
            try:
                self.auth()
            except ApiError:
                pass
            req = self.get("%s/%s" % (self.url, edge), params=parameters,
                           headers=self.headers)

        if return_results:
            return req.json()

    def search(self, query, count=100, order="new", page='',
               result_type="link", time_period="all", params=None):

        parameters = {"show": "all",
                      "q": query,
                      "limit": count,
                      "sort": order,
                      "type": result_type,
                      "t": time_period,
                      "after": page}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('search.json', parameters)

    def subreddit(self, subreddit, count=100, category="new", page='',
                  params=None, time_period='all'):

        parameters = {"limit": count,
                      "t": time_period,
                      "after": page}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('r/%s/%s.json' % (subreddit, category), parameters)

    def user(self, user, count=100, order="new", page='',
             result_type="overview", params=None, time_period='all'):

        parameters = {"show": "all",
                      "limit": count,
                      "sort": order,
                      "type": result_type,
                      "t": time_period,
                      "after": page}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('user/%s/%s.json' % (user, result_type),
                             parameters)

    def thread_comments(self, thread_id, subreddit, count=1000, order="top",
                        params=None):

        parameters = {"limit": count,
                      "depth": 50,
                      "showmore": True,
                      "sort": order}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('r/%s/comments/%s.json' % (subreddit, thread_id),
                             parameters)

    def more_children(self, children, link_id, sort="new",
                      params=None):
        parameters = {"api_type": "json",
                      "children": ",".join(children),
                      "link_id": link_id,
                      "sort": sort
                      }
        if params:
            for key, value in params.items():
                parameters[key] = value

        return self.api_call('api/morechildren', parameters)


class Facebook(API):
    def __init__(self, api_key):
        super().__init__()

        self.key = api_key
        self.url = "https://graph.facebook.com/v2.8"
        self.request_rate = 2
        self.last_request = time()

    def api_call(self, edge, parameters, return_results=True):
        req = self.get("%s/%s" % (self.url, edge), params=parameters)

        time_diff = time() - self.last_request
        if time_diff < self.request_rate:
            sleep(time_diff)

        self.last_request = time()

        if return_results:
            return req.json()

    def post(self, post_id, params=None):

        """

        :param post_id:
        :param params:
        :return:
        """

        parameters = {"access_token": self.key}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('%s' % post_id, parameters)

    def page_posts(self, page_id, after='', post_type="posts",
                   include_hidden=False, params=None):

        """

        :param page_id:
        :param after:
        :param post_type: Can be 'posts', 'feed', 'tagged', 'promotable_posts'
        :param include_hidden:
        :param params:
        :return:
        """
        parameters = {"access_token": self.key,
                      "after": after,
                      "include_hidden": include_hidden}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('%s/%s' % (page_id, post_type), parameters)

    def post_comments(self, post_id, after='', order="chronological",
                      filter="stream", params=None):

        """

        :param post_id:
        :param after:
        :param order: Can be 'ranked', 'chronological', 'reverse_chronological'
        :param filter: Can be 'stream', 'toplevel'
        :param params:
        :return:
        """
        parameters = {"access_token": self.key,
                      "after": after,
                      "order": order,
                      "filter": filter}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call('%s/comments' % post_id, parameters)


class Twitter(API):
    def __init__(self, app_key, app_secret, oauth_token, oauth_token_secret):
        super().__init__()

        self.app_key = app_key
        self.app_secret = app_secret
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret

        self.url = "https://api.twitter.com/1.1"
        self.request_rate = 5

        self.auth = OAuth1(self.app_key, self.app_secret, self.oauth_token,
                           self.oauth_token_secret)
        self.last_request = time()

    def api_call(self, edge, parameters, return_results=True):
        req = self.get("%s/%s" % (self.url, edge), params=parameters,
                       auth=self.auth)

        time_diff = time() - self.last_request
        if time_diff < self.request_rate:
            sleep(time_diff)

        self.last_request = time()

        if return_results:
            return req.json()

    def search(self, query, count=100, max_id='',
               result_type="mixed", include_entities=True, params=None):

        count = 100 if count < 100 else count
        parameters = {"q": query,
                      "count": count,
                      "max_id": max_id,
                      "result_type": result_type,
                      "include_entities": include_entities}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call("search/tweets.json", parameters)

    def user(self, username, count=200, max_id=None, exclude_replies=False,
             include_retweets=False, params=None):
        parameters = {"screen_name": username,
                      "count": count,
                      "max_id": max_id,
                      "exclude_replies": exclude_replies,
                      "include_rts": include_retweets}
        if params:
            for key, value in params.items():
                parameters[key] = value
        return self.api_call("statuses/user_timeline.json", parameters)
