from urllib.parse import urlparse, parse_qs
from os import environ

from . import apis
from .apis import ApiError, FatalApiError


class Source:
    # TODO: Pickle generator state to continue when connection lost etc.
    def __init__(self, log_function=print):
        self.log_function = log_function
        pass

    def log_error(self, e):
        """
        Print errors. Stop travis-ci from leaking api keys

        :param e: The error
        :return: None
        """

        if not environ.get('CI'):
            self.log_function(e)


class Facebook(Source):
    def __init__(self, api_key, log_function=print):
        super().__init__(log_function=log_function)
        self.api = apis.Facebook(api_key)
        self.api.log_function = log_function

    def posts(self, post_ids, **kwargs):
        """
        Posts

        :param post_ids: List of post ids
        :return: List of posts
        """

        if not isinstance(post_ids, list):
            post_ids = [post_ids]

        for post_id in post_ids:
            try:
                post = self.api.post(post_id, params=kwargs)
                yield post
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

    def post_comments(self, post_id, count=50, category="stream",
                      order="chronological", **kwargs):
        """
        Post's comments

        :param post_id: The id of the post
        :param count: The number of comments to return
        :param category: The type of comment. Can be 'stream', 'toplevel'
        :param order: The order of comments. Can be 'chronological',
                      'reverse_chronological'
        :return: List of comments
        """

        num_comments = 0
        try:
            comments = self.api.post_comments(
                post_id, filter=category, order=order, params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        while num_comments < count:
            if not comments.get('data'):
                return

            for comment in comments['data']:
                num_comments += 1
                yield comment
                if num_comments >= count:
                    return

            cursors = comments['paging']['cursors']
            if cursors['after'] == cursors['before']:
                return

            try:
                comments = self.api.post_comments(
                    post_id, after=cursors['after'], filter=category,
                    order=order, params=kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

    def page_posts(self, page_id, count=50, post_type="posts",
                   include_hidden=False, **kwargs):
        """
        Page's posts

        :param page_id: The id of the page
        :param count: The number of posts to retrieve
        :param post_type: The type of posts. Can be 'posts' for posts
                          published by the page, 'feed' for posts made to the
                          timeline of the page by anyone, 'tagged' for public
                          posts tagging the page, 'promotable_posts' for
                          posts that can be boosted (including unpublished
                          and scheduled posts
        :param include_hidden: Include posts hidden by the page
        :return: List of posts
        """

        num_posts = 0
        try:
            posts = self.api.page_posts(
                page_id, post_type=post_type, include_hidden=include_hidden,
                params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return
        while num_posts < count:
            if not posts['data']:
                return

            for post in posts['data']:
                num_posts += 1
                yield post
                if num_posts >= count:
                    return

            next_link = posts['paging'].get('next')
            if not next_link:
                return

            parsed = parse_qs(urlparse(next_link)[4])

            try:
                posts = self.api.page_posts(page_id, params=parsed)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

    def page_posts_comments(self, page_id, post_count=50,
                            post_type="posts",
                            include_hidden_posts=False, comment_count=50,
                            comment_category="stream",
                            comment_order="chronological"):
        """
        Page's post's comments

        :param page_id: The id of the page
        :param post_count: The number of posts to retrieve
        :param post_type: The type of posts. Can be 'posts' for posts
                          published by the page, 'feed' for posts made to the
                          timeline of the page by anyone, 'tagged' for public
                          posts tagging the page, 'promotable_posts' for
                          posts that can be boosted (including unpublished
                          and scheduled posts
        :param include_hidden_posts: Include posts hidden bby the page
        :param comment_count: The number of comments
        :param comment_category: The type of comment. Can be 'stream',
                                 'toplevel'
        :param comment_order: The order of comments. Can be 'chronological',
                              'reverse_chronological'
        :return: List of comments with associated post ids
        """
        try:
            posts = self.page_posts(
                page_id, count=post_count, post_type=post_type,
                include_hidden=include_hidden_posts)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        for post in posts:
            if isinstance(post, ApiError):
                self.log_error(post)
                self.log_error("Function halted")
                yield post
                return

            try:
                comments = self.post_comments(
                    post['id'], count=comment_count,
                    category=comment_category, order=comment_order)

                for comment in comments:
                    comment['post_id'] = post['id']
                    yield comment
            except ApiError as e:
                self.log_error(e)
                self.log_error("Skipped request")
            except FatalApiError as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return


class Twitter(Source):
    def __init__(self, app_key, app_secret, oauth_token, oauth_token_secret,
                 log_function=print):
        super().__init__(log_function=log_function)
        self.api = apis.Twitter(app_key, app_secret, oauth_token,
                                oauth_token_secret)
        self.api.log_function = log_function

    def search(self, query, count=100, result_type="mixed",
               include_entities=True, max_id='', **kwargs):
        """
        Search results

        :param query: The search query. Can use standard twitter search syntax
        :param count: The number of results
        :param result_type: The type of result. Can be 'mixed', 'recent',
                            'popular'
        :param include_entities: Include tweet's entities
        :param max_id: The maximum id the results can contain. Used to limit
                       recent results
        :return: The list of resulting tweets
        """

        num_tweets = 0
        try:
            tweets = self.api.search(
                query, count=count, result_type=result_type,
                include_entities=include_entities, max_id=max_id, params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        while num_tweets < count:
            for tweet in tweets['statuses']:
                num_tweets += 1
                yield tweet
                if num_tweets >= count:
                    return

            next_results = tweets['search_metadata'].get('next_results')
            if not next_results:
                return

            next_args = parse_qs(next_results[1:])
            try:
                tweets = self.api.search(
                    query, count=count, result_type=result_type,
                    include_entities=include_entities,
                    max_id=next_args['max_id'][0], params=kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

    def user(self, username, count=3200, exclude_replies=False,
             include_retweets=False, **kwargs):
        """
        User's tweets

        :param username: The user's twitter handle
        :param count: The number of results to return. Note that the maximum
                      of 3200 is not always reflected in the amount of
                      tweets twitter may return
        :param exclude_replies: Exclude tweets in reply to other tweets
        :param include_retweets: Include retweets of other tweets
        :return: A list of the user's tweets
        """

        num_tweets = 0
        try:
            tweets = self.api.user(
                username, count=count, exclude_replies=exclude_replies,
                include_retweets=include_retweets, params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        while num_tweets < count:
            if len(tweets) == 0:
                return

            for tweet in tweets:
                num_tweets += 1
                yield tweet
                if num_tweets >= count:
                    return

            max_id = tweets[-1]['id'] - 1

            try:
                tweets = self.api.user(
                    username, count=count, max_id=max_id, exclude_replies=
                    exclude_replies, include_retweets=include_retweets,
                    params=kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return


class Youtube(Source):
    def __init__(self, api_key, log_function=print):
        super().__init__(log_function=log_function)
        self.api = apis.Youtube(api_key)
        self.api.log_function = log_function

    def videos(self, videos, **kwargs):
        """
        Videos

        :param videos: List of video ids
        :return: A list of videos
        """

        chunk_size = 20
        i = 0

        while i < len(videos):
            chunk = videos[i:i + chunk_size]

            req = self.api.videos(chunk, params=kwargs)
            for video in req['items']:
                i += 1
                yield video

    def search(self, query, count=50, order="date", channel_id=None,
               event_type=None, location=None, location_radius=None,
               published_after=None, published_before=None, region_code=None,
               relevance_language=None, safe_search=None, topic_id=None,
               video_caption=None, video_category_id=None,
               video_definition=None, video_dimension=None,
               video_duration=None, video_embeddable=None,
               video_license=None, video_syndicated=None, video_type=None,
               **kwargs):
        """
        Search

        :param query: The search query
        :param count: The number of results to return
        :param order: The order of the results. Can be 'date', 'rating',
                      'relevance', 'reviewCount', 'title'
        :param channel_id: The id of the channel (not its name). Restricts
                           results to only those from the channel
        :param event_type: The broadcast event type. Can be 'completed',
                           'live', 'upcoming'
        :param location: The location's coordinates. In lat,lng format
        :param location_radius: The radius the location can be in. Can use m
                                or km
        :param published_after: RFC 3339 formatted time
        :param published_before: RFC 3339 formatted time
        :param region_code: two-letter ISO country code
        :param relevance_language: Search results most relevant to ISO 639-1
                                   two-letter language code
        :param safe_search: Can be 'moderate', 'none', 'strict'
        :param topic_id: Freebase topic id
        :param video_caption: Videos containing captions. Can be 'any',
                            'closedCaption', 'none'
        :param video_category_id: The youtube video category id
        :param video_definition: The resolution of the video. Can be 'any',
                                 'high', 'standard'
        :param video_dimension: The number of dimensions. Can be 'any', '2d',
                                '3d'
        :param video_duration: The duration of the video. Can be 'any',
                               'long', 'medium', 'short' (x>0, x>20, 20>x>4,
                               4>x)
        :param video_embeddable: Can the video be embedded
        :param video_license: The video's license. Can be 'any',
                              'creativeCommon', 'youtube'
        :param video_syndicated: Can the video be played outside youtube.com
        :param video_type: The type of video. Can be 'any', 'episode', 'movie'
        :return: The list of results
        """

        num_videos = 0
        try:
            videos = self.api.search(query, count=count, order=order,
                                     channel_id=channel_id,
                                     event_type=event_type,
                                     location=location,
                                     location_radius=location_radius,
                                     published_after=published_after,
                                     published_before=published_before,
                                     region_code=region_code,
                                     relevance_language=relevance_language,
                                     safe_search=safe_search, topic_id=topic_id,
                                     video_caption=video_caption,
                                     video_category_id=video_category_id,
                                     video_definition=video_definition,
                                     video_dimension=video_dimension,
                                     video_duration=video_duration,
                                     video_embeddable=video_embeddable,
                                     video_license=video_license,
                                     video_syndicated=video_syndicated,
                                     video_type=video_type,
                                     params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        while num_videos < count:
            if len(videos) == 0:
                return

            for video in videos['items']:
                num_videos += 1
                yield video
                if num_videos >= count:
                    return

            next_page = videos.get('nextPageToken')
            if not next_page:
                return

            try:
                videos = self.api.search(query, count=count, order=order,
                                         channel_id=channel_id,
                                         event_type=event_type,
                                         location=location,
                                         location_radius=location_radius,
                                         published_after=published_after,
                                         published_before=published_before,
                                         region_code=region_code,
                                         relevance_language=relevance_language,
                                         safe_search=safe_search,
                                         topic_id=topic_id,
                                         video_caption=video_caption,
                                         video_category_id=video_category_id,
                                         video_definition=video_definition,
                                         video_dimension=video_dimension,
                                         video_duration=video_duration,
                                         video_embeddable=video_embeddable,
                                         video_license=video_license,
                                         video_syndicated=video_syndicated,
                                         video_type=video_type,
                                         page=next_page, params=kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

    def channel(self, channel_id, count=200, order="date", **kwargs):
        """
        Channel videos

        :param channel_id: The channel id (not the name)
        :param count: The number of videos to return
        :param order: The order of videos. Can be 'date', 'rating',
                      'relevance', 'reviewCount', 'title'
        :return: The list of videos
        """

        try:
            search = self.search(
                query=None, channel_id=channel_id, count=count, order=order,
                kwargs=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        for result in search:
            yield result

    def video_comments(self, video_id, count=200, order="time",
                       search_terms=None, comment_format="html", **kwargs):
        """
        Video comments

        :param video_id: The id of the video
        :param count: The number of comments to return
        :param order: The order of the comments. Can be 'time', 'relevance'
        :param search_terms: List of strings that the comments must contain
        :param comment_format: The format of the comment. Can be 'plainText',
                               'html'
        :return: The list of comments
        """

        num_comments = 0
        try:
            comments = self.api.video_comments(
                video_id, count=count, order=order, search_terms=search_terms,
                text_format=comment_format, params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        while num_comments < count:
            if len(comments) == 0:
                return

            for comment in comments['items']:
                num_comments += 1
                yield comment
                if num_comments >= count:
                    return

            next_page = comments.get('nextPageToken')
            if not next_page:
                return

            try:
                comments = self.api.video_comments(
                    video_id, count=count, order=order, page=next_page,
                    search_terms=search_terms, text_format=comment_format,
                    params=kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

    def search_video_comments(self, query, video_count=50,
                              video_order="date", channel_id=None,
                              event_type=None, location=None,
                              location_radius=None,  published_after=None,
                              published_before=None,  region_code=None,
                              relevance_language=None,  safe_search=None,
                              topic_id=None,  video_caption=None,
                              video_category_id=None,  video_definition=None,
                              video_dimension=None, video_duration=None,
                              video_embeddable=None, video_license=None,
                              video_syndicated=None, video_type=None,
                              comment_count=50, comment_order="time",
                              comment_search_terms=None,
                              comment_format="html", **kwargs):
        """
        Search video comments

        :param query: The search query
        :param video_count: The number of videos to retrieve
        :param comment_count: The number of comments to return per video
        :param video_order: The order of the results. Can be 'date', 'rating',
                            'relevance', 'reviewCount', 'title'
        :param channel_id: The id of the channel (not its name). Restricts
                           results to only those from the channel
        :param event_type: The broadcast event type. Can be 'completed',
                           'live', 'upcoming'
        :param location: The location's coordinates. In lat,lng format
        :param location_radius: The radius the location can be in. Can use m
                                or km
        :param published_after: RFC 3339 formatted time
        :param published_before: RFC 3339 formatted time
        :param region_code: two-letter ISO country code
        :param relevance_language: Search results most relevant to ISO 639-1
                                   two-letter language code
        :param safe_search: Can be 'moderate', 'none', 'strict'
        :param topic_id: Freebase topic id
        :param video_caption: Videos containing captions. Can be 'any',
                            'closedCaption', 'none'
        :param video_category_id: The youtube video category id
        :param video_definition: The resolution of the video. Can be 'any',
                                 'high', 'standard'
        :param video_dimension: The number of dimensions. Can be 'any', '2d',
                                '3d'
        :param video_duration: The duration of the video. Can be 'any',
                               'long', 'medium', 'short' (x>0, x>20, 20>x>4,
                               4>x)
        :param video_embeddable: Can the video be embedded
        :param video_license: The video's license. Can be 'any',
                              'creativeCommon', 'youtube'
        :param video_syndicated: Can the video be played outside youtube.com
        :param video_type: The type of video. Can be 'any', 'episode', 'movie'
        :param comment_order: The order of the comments. Can be 'time',
                              'relevance'
        :param comment_search_terms: List of strings that the comments must
                                     contain
        :param comment_format: The format of the comment. Can be 'plainText',
                               'html'
        :return: The list of comments
        """

        try:
            search = self.search(query, count=video_count, order=video_order,
                                 channel_id=channel_id,
                                 event_type=event_type, location=location,
                                 location_radius=location_radius,
                                 published_after=published_after,
                                 published_before=published_before,
                                 region_code=region_code,
                                 relevance_language=relevance_language,
                                 safe_search=safe_search, topic_id=topic_id,
                                 video_caption=video_caption,
                                 video_category_id=video_category_id,
                                 video_definition=video_definition,
                                 video_dimension=video_dimension,
                                 video_duration=video_duration,
                                 video_embeddable=video_embeddable,
                                 video_license=video_license,
                                 video_syndicated=video_syndicated,
                                 video_type=video_type)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        for video in search:

            try:
                comments = self.video_comments(
                    video['id']['videoId'], count=comment_count,
                    order=comment_order, search_terms=comment_search_terms,
                    comment_format=comment_format, params=kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

            for comment in comments:
                yield comment

    def channel_video_comments(self, channel_id, video_count=50,
                               video_order="relevance", comment_count=50,
                               comment_order="relevance",
                               comment_text=None,
                               comment_format="html", **kwargs):
        """
        Channel video comments

        :param channel_id: The id of the channel (not the name)
        :param video_count: The number of videos to retrieve
        :param video_order: The order of the results. Can be 'date', 'rating',
                            'relevance', 'reviewCount', 'title'
        :param comment_count: The number of comments to retrieve from each video
        :param comment_order: The order of the comments. Can be 'time',
                              'relevance'
        :param comment_text: List of strings that the comments must
                             contain
        :param comment_format: The format of the comment. Can be 'plainText',
                               'html'
        :param kwargs:
        :return: A list of comments
        """
        #TODO Check the videos don't contain an api error
        try:
            videos = self.channel(
                channel_id, count=video_count, order=video_order,
                params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        for video in videos:

            try:
                comments = self.video_comments(
                    video['id']['videoId'], count=comment_count,
                    order=comment_order, search_terms=comment_text,
                    comment_format=comment_format, params=kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

            for comment in comments:
                yield comment

    def guess_channel_id(self, channel_name, count=5):
        """
        Guess the channel id given a channel name

        :param channel_name: The name of the channel
        :param count: The number of results to return
        :return: A list of channels
        """

        try:
            channels = self.api.guess_channel_id(channel_name, count=count)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        for channel in channels:
            yield channel


class Reddit(Source):
    def __init__(self, application_id, application_secret, log_function=print):
        super().__init__(log_function=log_function)
        self.api = apis.Reddit(application_id, application_secret)
        self.api.log_function = log_function

    def search(self, query, count=50, order="new", time_period="all", **kwargs):
        """
        Search's threads

        :param query: The search query
        :param count: The number of threads to return
        :param order: The order of the threads. Can be 'top', 'new',
                      'relevance', 'comments'.
        :param time_period: The time period in which the thread was created.
                            Can be 'all', 'year', 'month', 'week', 'today',
                            'hour'
        :return: A list of threads
        """

        num_threads = 0
        try:
            threads = self.api.search(
                query, count=count, order=order, time_period=time_period,
                params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        while num_threads < count:
            for thread in threads['data']['children']:
                num_threads += 1
                yield thread
                if num_threads >= count:
                    return

            after = threads['data'].get('after')
            if not after:
                return

            try:
                threads = self.api.search(
                    query, count=count, order=order, time_period=time_period,
                    page=after, params=kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

    def subreddit(self, subreddit, count=100, category="new", time_period="all",
                  **kwargs):
        """
        Subreddit's threads

        :param subreddit: The name of the subreddit
        :param count: The number of threads to return
        :param category: The type of thread. Can be 'top', 'new', 'hot',
                         'rising', 'controversial'
        :param time_period: The time period in which the thread was created.
                            Can be 'all', 'year', 'month', 'week', 'today',
                            'hour'
        :return: A list of threads
        """

        num_threads = 0
        try:
            threads = self.api.subreddit(
                subreddit, count=count, category=category,
                time_period=time_period, params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        while num_threads < count:
            for thread in threads['data']['children']:
                num_threads += 1
                yield thread
                if num_threads >= count:
                    return

            after = threads['data'].get('after')
            if not after:

                return
            try:
                threads = self.api.subreddit(
                    subreddit, count=count, category=category,
                    time_period="all", page=after, params=kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

    def user(self, user, count=100, order="new", result_type="overview",
             **kwargs):
        """
        User's posts

        :param user: The user's name
        :param count: The number of results
        :param order: The order of results. Can be 'new', 'hot', 'top',
                      'controversial'
        :param result_type: The type of result. Can be 'overview',
                            'submitted', 'comments', 'gilded'
        :return: A list of posts
        """

        num_posts = 0

        try:
            posts = self.api.user(
                user, count=count, order=order, result_type=result_type,
                params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        while num_posts < count:
            for thread in posts['data']['children']:
                num_posts += 1
                yield thread
                if num_posts >= count:
                    return

            after = posts['data'].get('after')
            if not after:
                return

            try:
                posts = self.api.user(
                    user, count=count, order=order, result_type=result_type,
                    page=after, params=kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

    def _extract_comment(self, comment):
        """
        Get the parent comment and replies from a comment

        :param comment: The parent comment
        :return: A list of comments, with the parent at the start
        """

        lst = []
        if comment['data'].get('replies', False):
            for reply in comment['data']['replies']['data']['children']:
                lst.extend(self._extract_comment(reply))
            del comment['data']['replies']
        lst.insert(0, comment)
        return lst

    def threads(self, id_sub_list, **kwargs):
        """
        Threads

        :param id_sub_list: A list of tuples containing thread ids and
                            subreddits
        :return: A list of threads
        """

        for thread_tuple in id_sub_list:
            thread_id, subreddit = thread_tuple
            try:
                thread = self.api.thread_comments(thread_id, subreddit, kwargs)
            except (ApiError, FatalApiError) as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return
            thread = {"thread": thread[0],
                      "comments": thread[1]}
            yield thread

    def thread_comments(self, thread_id, subreddit, count=200, order="top",
                        **kwargs):
        """
        Threads's comments

        :param thread_id: The id of the thread
        :param subreddit: The name of the thread's subreddit
        :param count: The number of comments to return
        :param order: The order of the comments. Can be 'top', 'new', 'best',
                      'controversial', 'old', 'q&a'
        :return: A list of comments
        """

        num_comments = 0

        try:
            comments = self.api.thread_comments(
                thread_id, subreddit, count=count, order=order, params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return
        more = []

        if isinstance(comments, dict):
            e = "Invalid thread"
            self.log_error(e)
            yield FatalApiError(e)
            return

        # Get reddit's first lot of comments
        for top_level_comment in comments[1]['data']['children']:
            for comment in self._extract_comment(top_level_comment):
                if comment['kind'] != "more":
                    num_comments += 1
                    yield comment
                    if num_comments >= count:
                        return
                else:
                    more.extend(comment['data']['children'])

        # Request hidden comments
        name = comments[0]['data']['children'][0]['data']['name']
        chunk_size = 20
        i = 0

        while i < len(more):
            chunk = more[i:i + chunk_size]  # request more in chunks

            try:
                comments = self.api.more_children(chunk, name)
            except ApiError as e:
                self.log_error(e)
                self.log_error("Request skipped")
                continue
            except FatalApiError as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

            for top_level_comment in comments['json']['data']['things']:
                for comment in (self._extract_comment(top_level_comment)):
                    if comment['kind'] != "more":
                        num_comments += 1
                        yield comment
                        if num_comments >= count:
                            return
                    else:
                        if comment['data']['children']:
                            more.extend(comment['data']['children'])

            i += chunk_size

    def search_thread_comments(self, query, thread_count=50,
                               comment_count=500, search_order="top",
                               search_time_period="all",
                               comment_order="top", **kwargs):
        """
        Search thread comments

        :param query: The search query
        :param thread_count: The number of threads to retrieve comments from
        :param comment_count: The number of comments to retrieve from each
                              thread
        :param search_order: The order of the threads. Can be 'top', 'new',
                             'relevance', 'comments'.
        :param search_time_period: The time period of the search. Can be
                                   'all', 'year', 'month', 'week', 'today',
                                   'hour'
        :param comment_order: The order of the comments. Can be 'top', 'new',
                              'best', 'controversial', 'old', 'q&a'
        :return: A list of comments
        """

        try:
            search = self.search(
                query, count=thread_count, order=search_order,
                time_period=search_time_period, params=kwargs)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        for thread in search:

            try:
                comments = self.thread_comments(
                    thread['data']['id'], thread['data']['subreddit'],
                    count=comment_count, order=comment_order, params=kwargs)
            except ApiError as e:
                self.log_error(e)
                self.log_error("Request skipped")
                continue
            except FatalApiError as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

            for comment in comments:
                yield comment

    def subreddit_thread_comments(self, subreddit, thread_count=50,
                                  comment_count=500, thread_order="top",
                                  search_time_period="all",
                                  comment_order="top", **kwargs):
        """
        Subreddit thread comments

        :param subreddit: The name of the subreddit
        :param thread_count: The number of threads to retrieve comments from
        :param comment_count: The number of comments to retrieve from each
                              thread
        :param thread_order: The order of the threads. Can be 'top', 'new',
                             'relevance', 'comments'.
        :param search_time_period: The time period of the search. Can be
                                   'all', 'year', 'month', 'week', 'today',
                                   'hour'
        :param comment_order: The order of the comments. Can be 'top', 'new',
                              'best', 'controversial', 'old', 'q&a'
        :return: A list of comments
        """

        try:
            threads = self.subreddit(
                subreddit, count=thread_count, time_period=search_time_period,
                category=thread_order)
        except (ApiError, FatalApiError) as e:
            self.log_error(e)
            self.log_error("Function halted")
            yield e
            return

        for thread in threads:
            if isinstance(thread, FatalApiError):
                self.log_error(thread)
                self.log_error("Function halted")
                yield thread
                return

            elif isinstance(thread, ApiError):
                self.log_error(thread)
                self.log_error("Skipped request")
                continue

            try:
                comments = self.thread_comments(
                    thread['data']['id'], thread['data']['subreddit'],
                    count=comment_count, order=comment_order, params=kwargs)
            except ApiError as e:
                self.log_error(e)
                self.log_error("Request skipped")
                continue
            except FatalApiError as e:
                self.log_error(e)
                self.log_error("Function halted")
                yield e
                return

            for comment in comments:
                yield comment

