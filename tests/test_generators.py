from unittest import TestCase
from os import environ
from itertools import combinations


class Generator(TestCase):
    def check_list(self, lst):
        self.assertIsInstance(lst, list)
        self.assertGreater(len(lst), 0, "List contains no results")
        for item in lst:
            self.assertIsInstance(item, dict)

    def check_dict_keys(self, lst, keys):
        for item in lst:
            for key in keys:
                self.assertIn(key, item)


class TestFacebook(Generator):
    def setUp(self):
        from socialreaper import Facebook
        self.fbk = Facebook(environ['facebook_api_key'])

        # Reduce time
        self.fbk.api.retry_rate = 1
        self.fbk.api.num_retries = 2

    def test_one_post(self):
        posts = self.fbk.posts(["179866158722992_1302626123113651"])
        posts = list(posts)

        self.check_list(posts)
        self.check_dict_keys(posts, ["created_time", "id"])

    def test_multiple_posts(self):
        posts = self.fbk.posts(["179866158722992_1312328855476711",
                                "179866158722992_1314779625231634",
                                "179866158722992_1315190741857189",
                                "179866158722992_1309815939061336"])
        posts = list(posts)
        self.assertEqual(len(posts), 4)

    def test_fail_one_post(self):
        posts = self.fbk.posts(["xxxxxxxxxxxxxxx",
                                "179866158722992_1312328855476711"])
        posts = list(posts)
        self.assertEqual(len(posts), 1)

    def test_fail_two_posts(self):
        posts = self.fbk.posts(["srjnkrejgbksrb", "sdjnwejekfjnkwe"])
        posts = list(posts)
        self.assertIsInstance(posts[0], ApiError)

    def test_fail_auth(self):
        from socialreaper import Facebook

        fbk_fail = Facebook(environ['facebook_api_key'][:-1]+"a")
        posts = list(fbk_fail.posts("179866158722992_1312328855476711"))
        self.assertEqual(len(posts), 1)

    def test_post_comments(self):
        comments = self.fbk.post_comments("179866158722992_1302626123113651",
                                          count=100)
        comments = list(comments)

        self.check_list(comments)
        self.check_dict_keys(comments, ["created_time", "id"])

        self.assertEqual(len(comments), 100)

    def test_post_comments_count(self):
        comments = self.fbk.post_comments("179866158722992_1302626123113651",
                                          count=137)
        comments = list(comments)

        self.assertEqual(len(comments), 137)

    def test_post_comments_categories(self):
        chronological_comments = self.fbk.post_comments(
            "179866158722992_1302626123113651", category="toplevel", count=5)
        chronological_comments = list(chronological_comments)
        reverse_comments = self.fbk.post_comments(
            "179866158722992_1302626123113651", category="stream", count=5)
        reverse_comments = list(reverse_comments)

        self.assertIsNot(reverse_comments, chronological_comments)

    def test_post_comments_orders(self):
        chronological_comments = self.fbk.post_comments(
            "179866158722992_1302626123113651", order="chronological", count=5)
        chronological_comments = list(chronological_comments)
        reverse_comments = self.fbk.post_comments(
            "179866158722992_1302626123113651",
            order="reverse_chronological", count=5)
        reverse_comments = list(reverse_comments)

        self.assertIsNot(reverse_comments, chronological_comments)

    def test_page_posts(self):
        posts = self.fbk.page_posts("McdonaldsAU", count=50)
        posts = list(posts)

        self.check_list(posts)
        self.check_dict_keys(posts, ["created_time", "id"])

    def test_page_posts_types(self):
        posts = self.fbk.page_posts("mcdonaldsau", post_type="posts", count=5)
        posts = list(posts)
        feed = self.fbk.page_posts("mcdonaldsau", post_type="feed", count=5)
        feed = list(feed)
        tagged = self.fbk.page_posts("mcdonaldsau", post_type="tagged", count=5)
        tagged = list(tagged)

        for pair in combinations([posts, feed, tagged], 2):
            self.assertIsNot(*pair)

    def test_post_comments_fail(self):
        posts = self.fbk.page_posts("skfjdjekrgbkrn")
        posts = list(posts)

        self.assertEqual(len(posts), 1)
        self.assertIsInstance(posts[0], ApiError)

    def test_page_posts_comments(self):
        posts = self.fbk.page_posts_comments("wikipedia", post_count=4)
        posts = list(posts)

        self.check_list(posts)
        self.check_dict_keys(posts, ["created_time", "id"])

    def test_page_posts_comments_fail(self):
        posts = self.fbk.page_posts_comments("skfjdjekrgbkrn")
        posts = list(posts)

        self.assertEqual(len(posts), 1)
        self.assertIsInstance(posts[0], ApiError)


class TestTwitter(Generator):
    def setUp(self):
        from socialreaper import Twitter
        self.twt = Twitter(environ['twitter_app_key'],
                           environ['twitter_app_secret'],
                           environ['twitter_oauth_token'],
                           environ['twitter_oauth_token_secret'])

        # Reduce time
        self.twt.api.retry_rate = 1
        self.twt.api.num_retries = 2

    def test_search(self):
        tweets = self.twt.search("#news")
        tweets = list(tweets)

        self.check_list(tweets)
        self.check_dict_keys(tweets, ["id", "lang", "text"])

    def test_search_count(self):
        tweets = self.twt.search("beach", count=107)
        tweets = list(tweets)

        self.assertEqual(len(tweets), 107)

    def test_search_entities(self):
        tweets = self.twt.search("beach", include_entities=False, count=1)
        tweets = list(tweets)
        self.assertIsNone(tweets[0].get('entities'))
        tweets = self.twt.search("beach", include_entities=True, count=1)
        tweets = list(tweets)
        self.assertIsNotNone(tweets[0].get('entities'))

    def test_search_result_type(self):
        mixed = self.twt.search("beach", result_type="mixed")
        mixed = list(mixed)
        self.assertIsNot(len(mixed), 0)
        self.assertIsNot(mixed[0], ApiError)

        recent = self.twt.search("beach", result_type="recent")
        recent = list(recent)
        self.assertIsNot(len(recent), 0)
        self.assertIsNot(recent[0], ApiError)

        popular = self.twt.search("beach", result_type="popular")
        popular = list(popular)
        self.assertIsNot(len(popular), 0)
        self.assertIsNot(popular[0], ApiError)

        for pair in combinations([mixed, recent, popular], 2):
            self.assertIsNot(*pair)

    def test_user(self):
        tweets = self.twt.user("jack")
        tweets = list(tweets)

        self.check_list(tweets)
        self.check_dict_keys(tweets, ["id", "lang", "text"])

    def test_user_count(self):
        tweets = self.twt.user("jack", count=132)
        tweets = list(tweets)

        self.assertEqual(len(tweets), 132)

    def test_user_exclude_replies(self):
        tweets = self.twt.user("jack", exclude_replies=True, count=500)

        for tweet in tweets:
            self.assertIsNone(tweet.get("in_reply_to_status_id"))

        tweets = self.twt.user("jack", exclude_replies=False, count=500)

        reply = False
        for tweet in tweets:
            if tweet.get("in_reply_to_status_id"):
                reply = True
                break

        self.assertTrue(reply)

    def test_user_include_retweets(self):
        tweets = self.twt.user("jack", include_retweets=True, count=500)

        retweet = False
        for tweet in tweets:
            if tweet.get("retweeted_status"):
                retweet = True
                break

        self.assertTrue(retweet)

        tweets = self.twt.user("jack", include_retweets=False, count=500)

        for tweet in tweets:
            self.assertIsNone(tweet.get("retweeted_status"))


class TestReddit(Generator):
    def setUp(self):
        from socialreaper import Reddit
        self.rdt = Reddit(environ['reddit_application_id'],
                          environ['reddit_application_secret'])

        # Reduce time
        self.rdt.api.retry_rate = 1
        self.rdt.api.num_retries = 2

    def test_search(self):
        threads = self.rdt.search("video")
        threads = list(threads)

        self.check_list(threads)
        self.check_dict_keys(threads, ["kind", "data"])

        threads_data = [thread["data"] for thread in threads]
        self.check_dict_keys(threads_data, ["author", "name", "score",
                                            "num_comments", "title"])

    def test_search_count(self):
        threads = self.rdt.search("news", count=114)
        threads = list(threads)

        self.assertEqual(len(threads), 114)

    def test_search_order(self):
        top = self.rdt.search("dog", count=100, order="top")
        top = list(top)

        new = self.rdt.search("dog", count=100, order="new")
        new = list(new)

        relevance = self.rdt.search("dog", count=100, order="relevance")
        relevance = list(relevance)

        comments = self.rdt.search("dog", count=100, order="comments")
        comments = list(comments)

        for pair in combinations([top, new, relevance, comments], 2):
            self.assertIsNot(*pair)

    def test_search_time_period(self):
        all = self.rdt.search("dog", order="top", time_period="all")
        all = list(all)

        year = self.rdt.search("dog", order="top", time_period="year")
        year = list(year)

        month = self.rdt.search("dog", order="top", time_period="month")
        month = list(month)

        week = self.rdt.search("dog", order="top", time_period="week")
        week = list(week)

        today = self.rdt.search("dog", order="top", time_period="today")
        today = list(today)

        hour = self.rdt.search("dog", order="top", time_period="hour")
        hour = list(hour)

        for pair in combinations([all, year, month, week, today, hour], 2):
            self.assertIsNot(*pair)

    def test_subreddit(self):
        threads = self.rdt.subreddit("all")
        threads = list(threads)

        self.check_list(threads)
        self.check_dict_keys(threads, ["kind", "data"])

        threads_data = [thread["data"] for thread in threads]
        self.check_dict_keys(threads_data, ["author", "name", "score",
                                            "num_comments", "title"])

    def test_subreddit_count(self):
        threads = self.rdt.subreddit("videos", count=156)
        threads = list(threads)

        self.assertEqual(len(threads), 156)

    def test_subreddit_category(self):
        new = self.rdt.subreddit("videos", category="new")
        new = list(new)

        hot = self.rdt.subreddit("videos", category="hot")
        hot = list(hot)

        top = self.rdt.subreddit("videos", category="top")
        top = list(top)

        rising = self.rdt.subreddit("videos", category="rising")
        rising = list(rising)

        controversial = self.rdt.subreddit("videos", category="controversial")
        controversial = list(controversial)

        for pair in combinations([new, hot, top, rising, controversial], 2):
            self.assertIsNot(*pair)

    def test_subreddit_time_period(self):
        all = self.rdt.subreddit("aww", order="top", time_period="all")
        all = list(all)

        year = self.rdt.subreddit("aww", order="top", time_period="year")
        year = list(year)

        month = self.rdt.subreddit("aww", order="top", time_period="month")
        month = list(month)

        week = self.rdt.subreddit("aww", order="top", time_period="week")
        week = list(week)

        today = self.rdt.subreddit("aww", order="top", time_period="today")
        today = list(today)

        hour = self.rdt.subreddit("aww", order="top", time_period="hour")
        hour = list(hour)

        for pair in combinations([all, year, month, week, today, hour], 2):
            self.assertIsNot(*pair)

    def test_user(self):
        posts = self.rdt.user("spez")
        posts = list(posts)

        self.check_list(posts)
        self.check_dict_keys(posts, ["kind", "data"])

        posts_data = [post["data"] for post in posts]
        self.check_dict_keys(posts_data, ["author", "name", "score"])

    def test_user_count(self):
        posts = self.rdt.user('spez', count=114)
        posts = list(posts)

        self.assertEqual(len(posts), 114)

    def test_user_order(self):
        top = self.rdt.user("spez", count=100, order="top")
        top = list(top)

        new = self.rdt.user("spez", count=100, order="new")
        new = list(new)

        hot = self.rdt.user("spez", count=100, order="hot")
        hot = list(hot)

        controversial = self.rdt.user("spez", count=100, order="controversial")
        controversial = list(controversial)

        for pair in combinations([top, new, hot, controversial], 2):
            self.assertIsNot(*pair)

    def test_user_result_type(self):
        overview = self.rdt.user("spez", result_type="overview")
        overview = list(overview)

        submitted = self.rdt.user("spez", result_type="submitted")
        submitted = list(submitted)

        comments = self.rdt.user("spez", result_type="comments")
        comments = list(comments)

        gilded = self.rdt.user("spez", result_type="gilded")
        gilded = list(gilded)

        for pair in combinations([overview, submitted, comments, gilded], 2):
            self.assertIsNot(*pair)

    def test_threads(self):
        threads = self.rdt.threads(
            [('5qrlnd', 'movies'), ('5qrxdx', 'explainlikeimfive')])
        threads = list(threads)

        self.check_list(threads)
        self.check_dict_keys(threads, ['thread', 'comments'])

    def test_thread_comments(self):
        comments = self.rdt.thread("z1c9z", "IamA")
        comments = list(comments)

        comments_data = [comment["data"] for comment in comments]
        self.check_dict_keys(comments_data, ["author", "name", "score",
                                             "body"])

    def test_thread_comments_count(self):
        comments = self.rdt.thread("z1c9z", "IamA", count=857)
        comments = list(comments)

        self.assertEqual(len(comments), 857)

    def test_thread_comments_order(self):
        top = self.rdt.thread("z1c9z", "IamA", order="top")
        top = list(top)

        new = self.rdt.thread("z1c9z", "IamA", order="new")
        new = list(new)

        best = self.rdt.thread("z1c9z", "IamA", order="best")
        best = list(best)

        controversial = self.rdt.thread("z1c9z", "IamA",
                                        order="controversial")
        controversial = list(controversial)

        old = self.rdt.thread("z1c9z", "IamA", order="old")
        old = list(old)

        qa = self.rdt.thread("z1c9z", "IamA", order="q&a")
        qa = list(qa)

        for pair in combinations([top, new, best, controversial, old, qa], 2):
            self.assertIsNot(*pair)

    def test_search_thread_comments(self):
        comments = self.rdt.search_thread_comments("video", thread_count=5,
                                                   comment_count=50)
        comments = list(comments)

        comments_data = [comment["data"] for comment in comments]
        self.check_dict_keys(comments_data, ["author", "name", "score",
                                             "body"])

    def test_subreddit_thread_comments(self):
        comments = self.rdt.subreddit_thread_comments("all", thread_count=5,
                                                      comment_count=50)
        comments = list(comments)

        comments_data = [comment["data"] for comment in comments]
        self.check_dict_keys(comments_data, ["author", "name", "score",
                                             "body"])


class TestYoutube(Generator):
    def setUp(self):
        from socialreaper import YouTube
        self.ytb = YouTube(environ['youtube_api_key'])

    def test_search(self):
        videos = self.ytb.search("music", count=50)
        videos = list(videos)

        self.check_list(videos)
        self.check_dict_keys(videos, ["etag", "id", "kind", "snippet"])

    def test_channel(self):
        videos = self.ytb.channel("UC6nSFpj9HTCZ5t-N3Rm3-HA", count=50)
        videos = list(videos)

        self.check_list(videos)
        self.check_dict_keys(videos, ["etag", "id", "kind", "snippet"])

    def test_video_comments(self):
        pass

    def test_search_video_comments(self):
        pass

    def test_channel_video_comments(self):
        pass
