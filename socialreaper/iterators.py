from .apis import Facebook as FacebookApi
from .exceptions import ApiError, FatalApiError
from urllib.parse import urlparse, parse_qs


class IterError(Exception):
    def __init__(self, e, variables):
        self.error = e
        self.vars = variables

    def __str__(self):
        return "An API error has occurred:  " + str(self.error)


class Iter:
    def __init__(self):
        # API object
        self.api = None

        # Response from api
        self.response = {}

        # Data from the response
        self.data = []

        # Index of data
        self.i = 0

        # Paging count, for restarting progress
        self.page_count = 0

    def __iter__(self):
        return self

    def __next__(self):
        # If not at the end of data, return the next element, else get more
        if self.i < len(self.data):
            result = self.data[self.i]
            self.i += 1

            return result

        else:
            try:
                self.get_data()
            except StopIteration:
                raise StopIteration
            self.i = 0
            return self.__next__()

    def page_jump(self, count):
        """
        Page through data quickly. Used to resume failed job or jump to another
        page
        :param count: The number of pages to iterate over
        """
        for i in range(count):
            self.get_data()

    def get_data(self):
        """
        Obtain the data to iterate over from the API
        :return:
        """
        pass


class Source:
    @staticmethod
    def merge(args, fields):
        if not args:
            args = {}

        if not fields:
            return args

        args['fields'] = ",".join(fields)
        return args

    @staticmethod
    def none_to_dict(value):
        return {} if not value else value


def merge(args, fields):
    if not args:
        args = {}

    if not fields:
        return args

    args['fields'] = fields
    return args


class IterIter:
    def __init__(self, outer, key, inner_func, inner_args):
        # Outer iter to obtain keys from
        self.outer = outer

        # Key string for outer function's data
        self.key = key

        # Inner iter to obtain data from
        self.inner = None

        # The function to create the inner iter from
        self.inner_func = inner_func

        # The inner function's arguments
        self.inner_args = inner_args

        # Does the outer iter need a step
        self.outer_jump = True

    def __iter__(self):
        return self

    def __next__(self):
        # If outer iter needs to step
        if self.outer_jump:
            # Get key from outer iter's return
            # When outer iter is over, StopIteration is raised
            key = self.outer.__next__().get(self.key)
            # Create the inner iter by calling the function with key and args
            self.inner = self.inner_func(key, **self.inner_args)
            # Toggle jumping off
            self.outer_jump = False

        # Return data from inner iter
        try:
            return self.inner.__next__()
        except StopIteration:
            # If inner iter is over, step outer
            self.outer_jump = True
            return self.__next__()


class Facebook(Source):
    def __init__(self, api_key):
        self.api_key = api_key
        self.dummy_api = FacebookApi(api_key)

        # Make use of nested queries, limiting scraping time
        self.nested_queries = False

    def test(self):
        try:
            api = FacebookApi(self.api_key)
            api.api_call('facebook', {'access_token': self.api_key})
            return True, "Working"

        except ApiError as e:
            return False, e

    def no_edge(self, node, fields, **kwargs):
        return iter([])
        # return self.FacebookIter(self.api_key, node, "", fields, **kwargs)

    def one_edge(self, node, edge, fields, **kwargs):
        return self.FacebookIter(self.api_key, node, edge, fields, **kwargs)

    def two_edge(self, node, outer_func, inner_func, first_fields,
                 second_fields, first_args, second_args):

        first_args = merge(first_args, first_fields)
        second_args = merge(second_args, second_fields)
        return IterIter(outer_func(node, **first_args), "id",
                        inner_func,
                        second_args)

    def three_edge(self, node, outer_func, inner_func, first_fields,
                   second_fields, third_fields, first_args, second_args,
                   third_args):

        first_args = merge(first_args, first_fields)
        second_args = merge(second_args, second_fields)
        third_args = merge(third_args, third_fields)
        return IterIter(
            outer_func(node, None, None, first_args,
                       second_args), "id", inner_func, third_args)

    def page(self, page_id, fields=None, **kwargs):
        return self.no_edge(page_id, fields, **kwargs)

    def page_feed(self, page_id, fields=None, **kwargs):
        return self.one_edge(page_id, "feed", fields, **kwargs)

    def page_feed_likes(self, page_id, feed_fields=None, like_fields=None,
                        feed_args=None, like_args=None):
        return self.two_edge(page_id, self.page_feed, self.post_likes,
                             feed_fields, like_fields,
                             feed_args, like_args)

    def page_feed_reactions(self, page_id, feed_fields=None,
                            reaction_fields=None, feed_args=None,
                            reaction_args=None):
        return self.two_edge(page_id, self.page_feed, self.post_reactions,
                             feed_fields,
                             reaction_fields, feed_args, reaction_args)

    def page_feed_comments(self, page_id, feed_fields=None, comment_fields=None,
                           feed_args=None, comment_args=None):
        return self.two_edge(page_id, self.page_feed, self.post_comments,
                             feed_fields,
                             comment_fields, feed_args, comment_args)

    def page_feed_sharedposts(self, page_id, feed_fields=None,
                              sharedpost_fields=None, feed_args=None,
                              sharedpost_args=None):
        return self.two_edge(page_id, self.page_feed, self.post_sharedposts,
                             feed_fields,
                             sharedpost_fields, feed_args, sharedpost_args)

    def page_feed_attachments(self, page_id, feed_fields=None,
                              attachment_fields=None, feed_args=None,
                              attachment_args=None):
        return self.two_edge(page_id, self.page_feed, self.post_attachments,
                             feed_fields,
                             attachment_fields, feed_args, attachment_args)

    def page_events(self, page_id, fields=None, **kwargs):
        return self.one_edge(page_id, "events", fields, **kwargs)

    def page_events_admins(self, page_id, events_fields=None, admins_fields=None, events_args=None, admins_args=None):
        return self.two_edge(page_id, self.page_events, self.event_admins, events_fields, admins_fields, events_args, admins_args)

    def page_events_attending(self, page_id, events_fields=None, attending_fields=None, events_args=None, attending_args=None):
        return self.two_edge(page_id, self.page_events, self.event_attending, events_fields, attending_fields, events_args, attending_args)

    def page_events_comments(self, page_id, events_fields=None, comments_fields=None, events_args=None, comments_args=None):
        return self.two_edge(page_id, self.page_events, self.event_comments, events_fields, comments_fields, events_args, comments_args)

    def page_events_declined(self, page_id, events_fields=None, declined_fields=None, events_args=None, declined_args=None):
        return self.two_edge(page_id, self.page_events, self.event_declined, events_fields, declined_fields, events_args, declined_args)

    def page_events_feed(self, page_id, events_fields=None, feed_fields=None, events_args=None, feed_args=None):
        return self.two_edge(page_id, self.page_events, self.event_feed, events_fields, feed_fields, events_args, feed_args)

    def page_events_feed_likes(self, page_id, events_fields=None, feed_fields=None, likes_fields=None, events_args=None, feed_args=None, likes_args=None):
        return self.three_edge(page_id, self.page_events_feed, self.post_likes, events_fields, feed_fields, likes_fields, events_args, feed_args, likes_args)

    def page_events_feed_reactions(self, page_id, events_fields=None, feed_fields=None, reactions_fields=None, events_args=None, feed_args=None, reactions_args=None):
        return self.three_edge(page_id, self.page_events_feed, self.post_reactions, events_fields, feed_fields, reactions_fields, events_args, feed_args, reactions_args)

    def page_events_feed_comments(self, page_id, events_fields=None, feed_fields=None, comments_fields=None, events_args=None, feed_args=None, comments_args=None):
        return self.three_edge(page_id, self.page_events_feed, self.post_comments, events_fields, feed_fields, comments_fields, events_args, feed_args, comments_args)

    def page_events_feed_sharedposts(self, page_id, events_fields=None, feed_fields=None, sharedposts_fields=None, events_args=None, feed_args=None, sharedposts_args=None):
        return self.three_edge(page_id, self.page_events_feed, self.post_sharedposts, events_fields, feed_fields, sharedposts_fields, events_args, feed_args, sharedposts_args)

    def page_events_feed_attachments(self, page_id, events_fields=None, feed_fields=None, attachments_fields=None, events_args=None, feed_args=None, attachments_args=None):
        return self.three_edge(page_id, self.page_events_feed, self.post_attachments, events_fields, feed_fields, attachments_fields, events_args, feed_args, attachments_args)

    def page_events_interested(self, page_id, events_fields=None, interested_fields=None, events_args=None, interested_args=None):
        return self.two_edge(page_id, self.page_events, self.event_interested, events_fields, interested_fields, events_args, interested_args)

    def page_events_live_videos(self, page_id, events_fields=None, live_videos_fields=None, events_args=None, live_videos_args=None):
        return self.two_edge(page_id, self.page_events, self.event_live_videos, events_fields, live_videos_fields, events_args, live_videos_args)

    def page_events_live_videos_likes(self, page_id, events_fields=None, live_videos_fields=None, likes_fields=None, events_args=None, live_videos_args=None, likes_args=None):
        return self.three_edge(page_id, self.page_events_live_videos, self.live_videos_likes, events_fields, live_videos_fields, likes_fields, events_args, live_videos_args, likes_args)

    def page_events_live_videos_reactions(self, page_id, events_fields=None, live_videos_fields=None, reactions_fields=None, events_args=None, live_videos_args=None, reactions_args=None):
        return self.three_edge(page_id, self.page_events_live_videos, self.live_videos_reactions, events_fields, live_videos_fields, reactions_fields, events_args, live_videos_args, reactions_args)

    def page_events_live_videos_comments(self, page_id, events_fields=None, live_videos_fields=None, comments_fields=None, events_args=None, live_videos_args=None, comments_args=None):
        return self.three_edge(page_id, self.page_events_live_videos, self.live_videos_comments, events_fields, live_videos_fields, comments_fields, events_args, live_videos_args, comments_args)

    def page_events_live_videos_errors(self, page_id, events_fields=None, live_videos_fields=None, errors_fields=None, events_args=None, live_videos_args=None, errors_args=None):
        return self.three_edge(page_id, self.page_events_live_videos, self.live_videos_errors, events_fields, live_videos_fields, errors_fields, events_args, live_videos_args, errors_args)

    def page_events_live_videos_blocked_users(self, page_id, events_fields=None, live_videos_fields=None, blocked_users_fields=None, events_args=None, live_videos_args=None, blocked_users_args=None):
        return self.three_edge(page_id, self.page_events_live_videos, self.live_videos_blocked_users, events_fields, live_videos_fields, blocked_users_fields, events_args, live_videos_args, blocked_users_args)

    def page_events_maybe(self, page_id, events_fields=None, maybe_fields=None, events_args=None, maybe_args=None):
        return self.two_edge(page_id, self.page_events, self.event_maybe, events_fields, maybe_fields, events_args, maybe_args)

    def page_events_noreply(self, page_id, events_fields=None, noreply_fields=None, events_args=None, noreply_args=None):
        return self.two_edge(page_id, self.page_events, self.event_noreply, events_fields, noreply_fields, events_args, noreply_args)

    def page_events_photos(self, page_id, events_fields=None, photos_fields=None, events_args=None, photos_args=None):
        return self.two_edge(page_id, self.page_events, self.event_photos, events_fields, photos_fields, events_args, photos_args)

    def page_events_photos_likes(self, page_id, events_fields=None, photos_fields=None, likes_fields=None, events_args=None, photos_args=None, likes_args=None):
        return self.three_edge(page_id, self.page_events_photos, self.photo_likes, events_fields, photos_fields, likes_fields, events_args, photos_args, likes_args)

    def page_events_photos_reactions(self, page_id, events_fields=None, photos_fields=None, reactions_fields=None, events_args=None, photos_args=None, reactions_args=None):
        return self.three_edge(page_id, self.page_events_photos, self.photo_reactions, events_fields, photos_fields, reactions_fields, events_args, photos_args, reactions_args)

    def page_events_photos_comments(self, page_id, events_fields=None, photos_fields=None, comments_fields=None, events_args=None, photos_args=None, comments_args=None):
        return self.three_edge(page_id, self.page_events_photos, self.photo_comments, events_fields, photos_fields, comments_fields, events_args, photos_args, comments_args)

    def page_events_photos_sharedposts(self, page_id, events_fields=None, photos_fields=None, sharedposts_fields=None, events_args=None, photos_args=None, sharedposts_args=None):
        return self.three_edge(page_id, self.page_events_photos, self.photo_sharedposts, events_fields, photos_fields, sharedposts_fields, events_args, photos_args, sharedposts_args)

    def page_events_photos_sponsor_tags(self, page_id, events_fields=None, photos_fields=None, sponsor_tags_fields=None, events_args=None, photos_args=None, sponsor_tags_args=None):
        return self.three_edge(page_id, self.page_events_photos, self.photo_sponsor_tags, events_fields, photos_fields, sponsor_tags_fields, events_args, photos_args, sponsor_tags_args)

    def page_events_photos_tags(self, page_id, events_fields=None, photos_fields=None, tags_fields=None, events_args=None, photos_args=None, tags_args=None):
        return self.three_edge(page_id, self.page_events_photos, self.photo_tags, events_fields, photos_fields, tags_fields, events_args, photos_args, tags_args)

    def page_events_picture(self, page_id, events_fields=None, picture_fields=None, events_args=None, picture_args=None):
        return self.two_edge(page_id, self.page_events, self.event_picture, events_fields, picture_fields, events_args, picture_args)

    def page_events_roles(self, page_id, events_fields=None, roles_fields=None, events_args=None, roles_args=None):
        return self.two_edge(page_id, self.page_events, self.event_roles, events_fields, roles_fields, events_args, roles_args)

    def page_albums(self, page_id, fields=None, **kwargs):
        return self.one_edge(page_id, "albums", fields, **kwargs)

    def page_albums_picture(self, page_id, albums_fields=None, picture_fields=None, albums_args=None, picture_args=None):
        return self.two_edge(page_id, self.page_albums, self.album_picture, albums_fields, picture_fields, albums_args, picture_args)

    def page_albums_photos(self, page_id, albums_fields=None, photos_fields=None, albums_args=None, photos_args=None):
        return self.two_edge(page_id, self.page_albums, self.album_photos, albums_fields, photos_fields, albums_args, photos_args)

    def page_albums_photos_likes(self, page_id, albums_fields=None, photos_fields=None, likes_fields=None, albums_args=None, photos_args=None, likes_args=None):
        return self.three_edge(page_id, self.page_albums_photos, self.photo_likes, albums_fields, photos_fields, likes_fields, albums_args, photos_args, likes_args)

    def page_albums_photos_reactions(self, page_id, albums_fields=None, photos_fields=None, reactions_fields=None, albums_args=None, photos_args=None, reactions_args=None):
        return self.three_edge(page_id, self.page_albums_photos, self.photo_reactions, albums_fields, photos_fields, reactions_fields, albums_args, photos_args, reactions_args)

    def page_albums_photos_comments(self, page_id, albums_fields=None, photos_fields=None, comments_fields=None, albums_args=None, photos_args=None, comments_args=None):
        return self.three_edge(page_id, self.page_albums_photos, self.photo_comments, albums_fields, photos_fields, comments_fields, albums_args, photos_args, comments_args)

    def page_albums_photos_sharedposts(self, page_id, albums_fields=None, photos_fields=None, sharedposts_fields=None, albums_args=None, photos_args=None, sharedposts_args=None):
        return self.three_edge(page_id, self.page_albums_photos, self.photo_sharedposts, albums_fields, photos_fields, sharedposts_fields, albums_args, photos_args, sharedposts_args)

    def page_albums_photos_sponsor_tags(self, page_id, albums_fields=None, photos_fields=None, sponsor_tags_fields=None, albums_args=None, photos_args=None, sponsor_tags_args=None):
        return self.three_edge(page_id, self.page_albums_photos, self.photo_sponsor_tags, albums_fields, photos_fields, sponsor_tags_fields, albums_args, photos_args, sponsor_tags_args)

    def page_albums_photos_tags(self, page_id, albums_fields=None, photos_fields=None, tags_fields=None, albums_args=None, photos_args=None, tags_args=None):
        return self.three_edge(page_id, self.page_albums_photos, self.photo_tags, albums_fields, photos_fields, tags_fields, albums_args, photos_args, tags_args)

    def page_albums_sharedposts(self, page_id, albums_fields=None, sharedposts_fields=None, albums_args=None, sharedposts_args=None):
        return self.two_edge(page_id, self.page_albums, self.album_sharedposts, albums_fields, sharedposts_fields, albums_args, sharedposts_args)

    def page_albums_likes(self, page_id, albums_fields=None, likes_fields=None, albums_args=None, likes_args=None):
        return self.two_edge(page_id, self.page_albums, self.album_likes, albums_fields, likes_fields, albums_args, likes_args)

    def page_albums_reactions(self, page_id, albums_fields=None, reactions_fields=None, albums_args=None, reactions_args=None):
        return self.two_edge(page_id, self.page_albums, self.album_reactions, albums_fields, reactions_fields, albums_args, reactions_args)

    def page_albums_comments(self, page_id, albums_fields=None, comments_fields=None, albums_args=None, comments_args=None):
        return self.two_edge(page_id, self.page_albums, self.album_comments, albums_fields, comments_fields, albums_args, comments_args)

    def page_photos(self, page_id, fields=None, **kwargs):
        return self.one_edge(page_id, "photos", fields, **kwargs)

    def page_photos_likes(self, page_id, photos_fields=None, likes_fields=None, photos_args=None, likes_args=None):
        return self.two_edge(page_id, self.page_photos, self.photo_likes, photos_fields, likes_fields, photos_args, likes_args)

    def page_photos_reactions(self, page_id, photos_fields=None, reactions_fields=None, photos_args=None, reactions_args=None):
        return self.two_edge(page_id, self.page_photos, self.photo_reactions, photos_fields, reactions_fields, photos_args, reactions_args)

    def page_photos_comments(self, page_id, photos_fields=None, comments_fields=None, photos_args=None, comments_args=None):
        return self.two_edge(page_id, self.page_photos, self.photo_comments, photos_fields, comments_fields, photos_args, comments_args)

    def page_photos_sharedposts(self, page_id, photos_fields=None, sharedposts_fields=None, photos_args=None, sharedposts_args=None):
        return self.two_edge(page_id, self.page_photos, self.photo_sharedposts, photos_fields, sharedposts_fields, photos_args, sharedposts_args)

    def page_photos_sponsor_tags(self, page_id, photos_fields=None, sponsor_tags_fields=None, photos_args=None, sponsor_tags_args=None):
        return self.two_edge(page_id, self.page_photos, self.photo_sponsor_tags, photos_fields, sponsor_tags_fields, photos_args, sponsor_tags_args)

    def page_photos_tags(self, page_id, photos_fields=None, tags_fields=None, photos_args=None, tags_args=None):
        return self.two_edge(page_id, self.page_photos, self.photo_tags, photos_fields, tags_fields, photos_args, tags_args)

    def page_live_videos(self, page_id, fields=None, **kwargs):
        return self.one_edge(page_id, "live_videos", fields, **kwargs)

    def page_live_videos_likes(self, page_id, live_videos_fields=None, likes_fields=None, live_videos_args=None, likes_args=None):
        return self.two_edge(page_id, self.page_live_videos, self.live_video_likes, live_videos_fields, likes_fields, live_videos_args, likes_args)

    def page_live_videos_reactions(self, page_id, live_videos_fields=None, reactions_fields=None, live_videos_args=None, reactions_args=None):
        return self.two_edge(page_id, self.page_live_videos, self.live_video_reactions, live_videos_fields, reactions_fields, live_videos_args, reactions_args)

    def page_live_videos_comments(self, page_id, live_videos_fields=None, comments_fields=None, live_videos_args=None, comments_args=None):
        return self.two_edge(page_id, self.page_live_videos, self.live_video_comments, live_videos_fields, comments_fields, live_videos_args, comments_args)

    def page_live_videos_errors(self, page_id, live_videos_fields=None, errors_fields=None, live_videos_args=None, errors_args=None):
        return self.two_edge(page_id, self.page_live_videos, self.live_video_errors, live_videos_fields, errors_fields, live_videos_args, errors_args)

    def page_live_videos_blocked_users(self, page_id, live_videos_fields=None, blocked_users_fields=None, live_videos_args=None, blocked_users_args=None):
        return self.two_edge(page_id, self.page_live_videos, self.live_video_blocked_users, live_videos_fields, blocked_users_fields, live_videos_args, blocked_users_args)

    def page_videos(self, page_id, fields=None, **kwargs):
        return self.one_edge(page_id, "videos", fields, **kwargs)

    def page_videos_auto_generated_captions(self, page_id, videos_fields=None, auto_generated_captions_fields=None, videos_args=None, auto_generated_captions_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_auto_generated_captions, videos_fields, auto_generated_captions_fields, videos_args, auto_generated_captions_args)

    def page_videos_captions(self, page_id, videos_fields=None, captions_fields=None, videos_args=None, captions_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_captions, videos_fields, captions_fields, videos_args, captions_args)

    def page_videos_comments(self, page_id, videos_fields=None, comments_fields=None, videos_args=None, comments_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_comments, videos_fields, comments_fields, videos_args, comments_args)

    def page_videos_crosspost_shared_pages(self, page_id, videos_fields=None, crosspost_shared_pages_fields=None, videos_args=None, crosspost_shared_pages_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_crosspost_shared_pages, videos_fields, crosspost_shared_pages_fields, videos_args, crosspost_shared_pages_args)

    def page_videos_likes(self, page_id, videos_fields=None, likes_fields=None, videos_args=None, likes_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_likes, videos_fields, likes_fields, videos_args, likes_args)

    def page_videos_reactions(self, page_id, videos_fields=None, reactions_fields=None, videos_args=None, reactions_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_reactions, videos_fields, reactions_fields, videos_args, reactions_args)

    def page_videos_sharedposts(self, page_id, videos_fields=None, sharedposts_fields=None, videos_args=None, sharedposts_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_sharedposts, videos_fields, sharedposts_fields, videos_args, sharedposts_args)

    def page_videos_sponsor_tags(self, page_id, videos_fields=None, sponsor_tags_fields=None, videos_args=None, sponsor_tags_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_sponsor_tags, videos_fields, sponsor_tags_fields, videos_args, sponsor_tags_args)

    def page_videos_tags(self, page_id, videos_fields=None, tags_fields=None, videos_args=None, tags_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_tags, videos_fields, tags_fields, videos_args, tags_args)

    def page_videos_thumbnails(self, page_id, videos_fields=None, thumbnails_fields=None, videos_args=None, thumbnails_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_thumbnails, videos_fields, thumbnails_fields, videos_args, thumbnails_args)

    def page_videos_insights(self, page_id, videos_fields=None, insights_fields=None, videos_args=None, insights_args=None):
        return self.two_edge(page_id, self.page_videos, self.video_insights, videos_fields, insights_fields, videos_args, insights_args)

    def page_picture(self, page_id, fields=None, **kwargs):
        return self.one_edge(page_id, "picture", fields, **kwargs)

    def group(self, group_id, fields=None, **kwargs):
        return iter([])

    def group_admins(self, group_id, fields=None, **kwargs):
        return self.one_edge(group_id, "admins", fields, **kwargs)

    def group_albums(self, group_id, fields=None, **kwargs):
        return self.one_edge(group_id, "albums", fields, **kwargs)

    def group_albums_picture(self, group_id, albums_fields=None, picture_fields=None, albums_args=None, picture_args=None):
        return self.two_edge(group_id, self.group_albums, self.album_picture, albums_fields, picture_fields, albums_args, picture_args)

    def group_albums_photos(self, group_id, albums_fields=None, photos_fields=None, albums_args=None, photos_args=None):
        return self.two_edge(group_id, self.group_albums, self.album_photos, albums_fields, photos_fields, albums_args, photos_args)

    def group_albums_photos_likes(self, group_id, albums_fields=None, photos_fields=None, likes_fields=None, albums_args=None, photos_args=None, likes_args=None):
        return self.three_edge(group_id, self.group_albums_photos, self.photos_likes, albums_fields, photos_fields, likes_fields, albums_args, photos_args, likes_args)

    def group_albums_photos_reactions(self, group_id, albums_fields=None, photos_fields=None, reactions_fields=None, albums_args=None, photos_args=None, reactions_args=None):
        return self.three_edge(group_id, self.group_albums_photos, self.photos_reactions, albums_fields, photos_fields, reactions_fields, albums_args, photos_args, reactions_args)

    def group_albums_photos_comments(self, group_id, albums_fields=None, photos_fields=None, comments_fields=None, albums_args=None, photos_args=None, comments_args=None):
        return self.three_edge(group_id, self.group_albums_photos, self.photos_comments, albums_fields, photos_fields, comments_fields, albums_args, photos_args, comments_args)

    def group_albums_photos_sharedposts(self, group_id, albums_fields=None, photos_fields=None, sharedposts_fields=None, albums_args=None, photos_args=None, sharedposts_args=None):
        return self.three_edge(group_id, self.group_albums_photos, self.photos_sharedposts, albums_fields, photos_fields, sharedposts_fields, albums_args, photos_args, sharedposts_args)

    def group_albums_photos_sponsor_tags(self, group_id, albums_fields=None, photos_fields=None, sponsor_tags_fields=None, albums_args=None, photos_args=None, sponsor_tags_args=None):
        return self.three_edge(group_id, self.group_albums_photos, self.photos_sponsor_tags, albums_fields, photos_fields, sponsor_tags_fields, albums_args, photos_args, sponsor_tags_args)

    def group_albums_photos_tags(self, group_id, albums_fields=None, photos_fields=None, tags_fields=None, albums_args=None, photos_args=None, tags_args=None):
        return self.three_edge(group_id, self.group_albums_photos, self.photos_tags, albums_fields, photos_fields, tags_fields, albums_args, photos_args, tags_args)

    def group_albums_sharedposts(self, group_id, albums_fields=None, sharedposts_fields=None, albums_args=None, sharedposts_args=None):
        return self.two_edge(group_id, self.group_albums, self.album_sharedposts, albums_fields, sharedposts_fields, albums_args, sharedposts_args)

    def group_albums_likes(self, group_id, albums_fields=None, likes_fields=None, albums_args=None, likes_args=None):
        return self.two_edge(group_id, self.group_albums, self.album_likes, albums_fields, likes_fields, albums_args, likes_args)

    def group_albums_reactions(self, group_id, albums_fields=None, reactions_fields=None, albums_args=None, reactions_args=None):
        return self.two_edge(group_id, self.group_albums, self.album_reactions, albums_fields, reactions_fields, albums_args, reactions_args)

    def group_albums_comments(self, group_id, albums_fields=None, comments_fields=None, albums_args=None, comments_args=None):
        return self.two_edge(group_id, self.group_albums, self.album_comments, albums_fields, comments_fields, albums_args, comments_args)

    def group_docs(self, group_id, fields=None, **kwargs):
        return self.one_edge(group_id, "docs", fields, **kwargs)

    def group_events(self, group_id, fields=None, **kwargs):
        return self.one_edge(group_id, "events", fields, **kwargs)

    def group_events_admins(self, group_id, events_fields=None, admins_fields=None, events_args=None, admins_args=None):
        return self.two_edge(group_id, self.group_events, self.event_admins, events_fields, admins_fields, events_args, admins_args)

    def group_events_attending(self, group_id, events_fields=None, attending_fields=None, events_args=None, attending_args=None):
        return self.two_edge(group_id, self.group_events, self.event_attending, events_fields, attending_fields, events_args, attending_args)

    def group_events_comments(self, group_id, events_fields=None, comments_fields=None, events_args=None, comments_args=None):
        return self.two_edge(group_id, self.group_events, self.event_comments, events_fields, comments_fields, events_args, comments_args)

    def group_events_declined(self, group_id, events_fields=None, declined_fields=None, events_args=None, declined_args=None):
        return self.two_edge(group_id, self.group_events, self.event_declined, events_fields, declined_fields, events_args, declined_args)

    def group_events_feed(self, group_id, events_fields=None, feed_fields=None, events_args=None, feed_args=None):
        return self.two_edge(group_id, self.group_events, self.event_feed, events_fields, feed_fields, events_args, feed_args)

    def group_events_feed_likes(self, group_id, events_fields=None, feed_fields=None, likes_fields=None, events_args=None, feed_args=None, likes_args=None):
        return self.three_edge(group_id, self.group_events_feed, self.post_likes, events_fields, feed_fields, likes_fields, events_args, feed_args, likes_args)

    def group_events_feed_reactions(self, group_id, events_fields=None, feed_fields=None, reactions_fields=None, events_args=None, feed_args=None, reactions_args=None):
        return self.three_edge(group_id, self.group_events_feed, self.post_reactions, events_fields, feed_fields, reactions_fields, events_args, feed_args, reactions_args)

    def group_events_feed_comments(self, group_id, events_fields=None, feed_fields=None, comments_fields=None, events_args=None, feed_args=None, comments_args=None):
        return self.three_edge(group_id, self.group_events_feed, self.post_comments, events_fields, feed_fields, comments_fields, events_args, feed_args, comments_args)

    def group_events_feed_sharedposts(self, group_id, events_fields=None, feed_fields=None, sharedposts_fields=None, events_args=None, feed_args=None, sharedposts_args=None):
        return self.three_edge(group_id, self.group_events_feed, self.post_sharedposts, events_fields, feed_fields, sharedposts_fields, events_args, feed_args, sharedposts_args)

    def group_events_feed_attachments(self, group_id, events_fields=None, feed_fields=None, attachments_fields=None, events_args=None, feed_args=None, attachments_args=None):
        return self.three_edge(group_id, self.group_events_feed, self.post_attachments, events_fields, feed_fields, attachments_fields, events_args, feed_args, attachments_args)

    def group_events_interested(self, group_id, events_fields=None, interested_fields=None, events_args=None, interested_args=None):
        return self.two_edge(group_id, self.group_events, self.event_interested, events_fields, interested_fields, events_args, interested_args)

    def group_events_live_videos(self, group_id, events_fields=None, live_videos_fields=None, events_args=None, live_videos_args=None):
        return self.two_edge(group_id, self.group_events, self.event_live_videos, events_fields, live_videos_fields, events_args, live_videos_args)

    def group_events_live_videos_likes(self, group_id, events_fields=None, live_videos_fields=None, likes_fields=None, events_args=None, live_videos_args=None, likes_args=None):
        return self.three_edge(group_id, self.group_events_live_videos, self.live_video_likes, events_fields, live_videos_fields, likes_fields, events_args, live_videos_args, likes_args)

    def group_events_live_videos_reactions(self, group_id, events_fields=None, live_videos_fields=None, reactions_fields=None, events_args=None, live_videos_args=None, reactions_args=None):
        return self.three_edge(group_id, self.group_events_live_videos, self.live_video_reactions, events_fields, live_videos_fields, reactions_fields, events_args, live_videos_args, reactions_args)

    def group_events_live_videos_comments(self, group_id, events_fields=None, live_videos_fields=None, comments_fields=None, events_args=None, live_videos_args=None, comments_args=None):
        return self.three_edge(group_id, self.group_events_live_videos, self.live_video_comments, events_fields, live_videos_fields, comments_fields, events_args, live_videos_args, comments_args)

    def group_events_live_videos_errors(self, group_id, events_fields=None, live_videos_fields=None, errors_fields=None, events_args=None, live_videos_args=None, errors_args=None):
        return self.three_edge(group_id, self.group_events_live_videos, self.live_video_errors, events_fields, live_videos_fields, errors_fields, events_args, live_videos_args, errors_args)

    def group_events_live_videos_blocked_users(self, group_id, events_fields=None, live_videos_fields=None, blocked_users_fields=None, events_args=None, live_videos_args=None, blocked_users_args=None):
        return self.three_edge(group_id, self.group_events_live_videos, self.live_video_blocked_users, events_fields, live_videos_fields, blocked_users_fields, events_args, live_videos_args, blocked_users_args)

    def group_events_maybe(self, group_id, events_fields=None, maybe_fields=None, events_args=None, maybe_args=None):
        return self.two_edge(group_id, self.group_events, self.event_maybe, events_fields, maybe_fields, events_args, maybe_args)

    def group_events_noreply(self, group_id, events_fields=None, noreply_fields=None, events_args=None, noreply_args=None):
        return self.two_edge(group_id, self.group_events, self.event_noreply, events_fields, noreply_fields, events_args, noreply_args)

    def group_events_photos(self, group_id, events_fields=None, photos_fields=None, events_args=None, photos_args=None):
        return self.two_edge(group_id, self.group_events, self.event_photos, events_fields, photos_fields, events_args, photos_args)

    def group_events_photos_likes(self, group_id, events_fields=None, photos_fields=None, likes_fields=None, events_args=None, photos_args=None, likes_args=None):
        return self.three_edge(group_id, self.group_events_photos, self.photo_likes, events_fields, photos_fields, likes_fields, events_args, photos_args, likes_args)

    def group_events_photos_reactions(self, group_id, events_fields=None, photos_fields=None, reactions_fields=None, events_args=None, photos_args=None, reactions_args=None):
        return self.three_edge(group_id, self.group_events_photos, self.photo_reactions, events_fields, photos_fields, reactions_fields, events_args, photos_args, reactions_args)

    def group_events_photos_comments(self, group_id, events_fields=None, photos_fields=None, comments_fields=None, events_args=None, photos_args=None, comments_args=None):
        return self.three_edge(group_id, self.group_events_photos, self.photo_comments, events_fields, photos_fields, comments_fields, events_args, photos_args, comments_args)

    def group_events_photos_sharedposts(self, group_id, events_fields=None, photos_fields=None, sharedposts_fields=None, events_args=None, photos_args=None, sharedposts_args=None):
        return self.three_edge(group_id, self.group_events_photos, self.photo_sharedposts, events_fields, photos_fields, sharedposts_fields, events_args, photos_args, sharedposts_args)

    def group_events_photos_sponsor_tags(self, group_id, events_fields=None, photos_fields=None, sponsor_tags_fields=None, events_args=None, photos_args=None, sponsor_tags_args=None):
        return self.three_edge(group_id, self.group_events_photos, self.photo_sponsor_tags, events_fields, photos_fields, sponsor_tags_fields, events_args, photos_args, sponsor_tags_args)

    def group_events_photos_tags(self, group_id, events_fields=None, photos_fields=None, tags_fields=None, events_args=None, photos_args=None, tags_args=None):
        return self.three_edge(group_id, self.group_events_photos, self.photo_tags, events_fields, photos_fields, tags_fields, events_args, photos_args, tags_args)

    def group_events_picture(self, group_id, events_fields=None, picture_fields=None, events_args=None, picture_args=None):
        return self.two_edge(group_id, self.group_events, self.event_picture, events_fields, picture_fields, events_args, picture_args)

    def group_events_roles(self, group_id, events_fields=None, roles_fields=None, events_args=None, roles_args=None):
        return self.two_edge(group_id, self.group_events, self.event_roles, events_fields, roles_fields, events_args, roles_args)

    def group_feed(self, group_id, fields=None, **kwargs):
        return self.one_edge(group_id, "feed", fields, **kwargs)

    def group_feed_likes(self, group_id, feed_fields=None, likes_fields=None, feed_args=None, likes_args=None):
        return self.two_edge(group_id, self.group_feed, self.post_likes, feed_fields, likes_fields, feed_args, likes_args)

    def group_feed_reactions(self, group_id, feed_fields=None, reactions_fields=None, feed_args=None, reactions_args=None):
        return self.two_edge(group_id, self.group_feed, self.post_reactions, feed_fields, reactions_fields, feed_args, reactions_args)

    def group_feed_comments(self, group_id, feed_fields=None, comments_fields=None, feed_args=None, comments_args=None):
        return self.two_edge(group_id, self.group_feed, self.post_comments, feed_fields, comments_fields, feed_args, comments_args)

    def group_feed_sharedposts(self, group_id, feed_fields=None, sharedposts_fields=None, feed_args=None, sharedposts_args=None):
        return self.two_edge(group_id, self.group_feed, self.post_sharedposts, feed_fields, sharedposts_fields, feed_args, sharedposts_args)

    def group_feed_attachments(self, group_id, feed_fields=None, attachments_fields=None, feed_args=None, attachments_args=None):
        return self.two_edge(group_id, self.group_feed, self.post_attachments, feed_fields, attachments_fields, feed_args, attachments_args)

    def group_files(self, group_id, fields=None, **kwargs):
        return self.one_edge(group_id, "files", fields, **kwargs)

    def group_live_videos(self, group_id, fields=None, **kwargs):
        return self.one_edge(group_id, "live_videos", fields, **kwargs)

    def group_live_videos_likes(self, group_id, live_videos_fields=None, likes_fields=None, live_videos_args=None, likes_args=None):
        return self.two_edge(group_id, self.group_live_videos, self.live_video_likes, live_videos_fields, likes_fields, live_videos_args, likes_args)

    def group_live_videos_reactions(self, group_id, live_videos_fields=None, reactions_fields=None, live_videos_args=None, reactions_args=None):
        return self.two_edge(group_id, self.group_live_videos, self.live_video_reactions, live_videos_fields, reactions_fields, live_videos_args, reactions_args)

    def group_live_videos_comments(self, group_id, live_videos_fields=None, comments_fields=None, live_videos_args=None, comments_args=None):
        return self.two_edge(group_id, self.group_live_videos, self.live_video_comments, live_videos_fields, comments_fields, live_videos_args, comments_args)

    def group_live_videos_errors(self, group_id, live_videos_fields=None, errors_fields=None, live_videos_args=None, errors_args=None):
        return self.two_edge(group_id, self.group_live_videos, self.live_video_errors, live_videos_fields, errors_fields, live_videos_args, errors_args)

    def group_live_videos_blocked_users(self, group_id, live_videos_fields=None, blocked_users_fields=None, live_videos_args=None, blocked_users_args=None):
        return self.two_edge(group_id, self.group_live_videos, self.live_video_blocked_users, live_videos_fields, blocked_users_fields, live_videos_args, blocked_users_args)

    def group_members(self, group_id, fields=None, **kwargs):
        return self.one_edge(group_id, "members", fields, **kwargs)

    def group_photos(self, group_id, fields=None, **kwargs):
        return self.one_edge(group_id, "photos", fields, **kwargs)

    def group_photos_likes(self, group_id, photos_fields=None, likes_fields=None, photos_args=None, likes_args=None):
        return self.two_edge(group_id, self.group_photos, self.photo_likes, photos_fields, likes_fields, photos_args, likes_args)

    def group_photos_reactions(self, group_id, photos_fields=None, reactions_fields=None, photos_args=None, reactions_args=None):
        return self.two_edge(group_id, self.group_photos, self.photo_reactions, photos_fields, reactions_fields, photos_args, reactions_args)

    def group_photos_comments(self, group_id, photos_fields=None, comments_fields=None, photos_args=None, comments_args=None):
        return self.two_edge(group_id, self.group_photos, self.photo_comments, photos_fields, comments_fields, photos_args, comments_args)

    def group_photos_sharedposts(self, group_id, photos_fields=None, sharedposts_fields=None, photos_args=None, sharedposts_args=None):
        return self.two_edge(group_id, self.group_photos, self.photo_sharedposts, photos_fields, sharedposts_fields, photos_args, sharedposts_args)

    def group_photos_sponsor_tags(self, group_id, photos_fields=None, sponsor_tags_fields=None, photos_args=None, sponsor_tags_args=None):
        return self.two_edge(group_id, self.group_photos, self.photo_sponsor_tags, photos_fields, sponsor_tags_fields, photos_args, sponsor_tags_args)

    def group_photos_tags(self, group_id, photos_fields=None, tags_fields=None, photos_args=None, tags_args=None):
        return self.two_edge(group_id, self.group_photos, self.photo_tags, photos_fields, tags_fields, photos_args, tags_args)

    def group_videos(self, group_id, fields=None, **kwargs):
        return self.one_edge(group_id, "videos", fields, **kwargs)

    def group_videos_auto_generated_captions(self, group_id, videos_fields=None,
                                             auto_generated_captions_fields=None,
                                             videos_args=None,
                                             auto_generated_captions_args=None):
        return self.two_edge(group_id, self.group_videos,
                             self.video_auto_generated_captions, videos_fields,
                             auto_generated_captions_fields, videos_args,
                             auto_generated_captions_args)

    def group_videos_captions(self, group_id, videos_fields=None,
                              captions_fields=None, videos_args=None,
                              captions_args=None):
        return self.two_edge(group_id, self.group_videos, self.video_captions,
                             videos_fields, captions_fields, videos_args,
                             captions_args)

    def group_videos_comments(self, group_id, videos_fields=None,
                              comments_fields=None, videos_args=None,
                              comments_args=None):
        return self.two_edge(group_id, self.group_videos, self.video_comments,
                             videos_fields, comments_fields, videos_args,
                             comments_args)

    def group_videos_crosspost_shared_pages(self, group_id, videos_fields=None,
                                            crosspost_shared_pages_fields=None,
                                            videos_args=None,
                                            crosspost_shared_pages_args=None):
        return self.two_edge(group_id, self.group_videos,
                             self.video_crosspost_shared_pages, videos_fields,
                             crosspost_shared_pages_fields, videos_args,
                             crosspost_shared_pages_args)

    def group_videos_likes(self, group_id, videos_fields=None,
                           likes_fields=None, videos_args=None,
                           likes_args=None):
        return self.two_edge(group_id, self.group_videos, self.video_likes,
                             videos_fields, likes_fields, videos_args,
                             likes_args)

    def group_videos_reactions(self, group_id, videos_fields=None,
                               reactions_fields=None, videos_args=None,
                               reactions_args=None):
        return self.two_edge(group_id, self.group_videos, self.video_reactions,
                             videos_fields, reactions_fields, videos_args,
                             reactions_args)

    def group_videos_sharedposts(self, group_id, videos_fields=None,
                                 sharedposts_fields=None, videos_args=None,
                                 sharedposts_args=None):
        return self.two_edge(group_id, self.group_videos,
                             self.video_sharedposts, videos_fields,
                             sharedposts_fields, videos_args, sharedposts_args)

    def group_videos_sponsor_tags(self, group_id, videos_fields=None,
                                  sponsor_tags_fields=None, videos_args=None,
                                  sponsor_tags_args=None):
        return self.two_edge(group_id, self.group_videos,
                             self.video_sponsor_tags, videos_fields,
                             sponsor_tags_fields, videos_args,
                             sponsor_tags_args)

    def group_videos_tags(self, group_id, videos_fields=None, tags_fields=None,
                          videos_args=None, tags_args=None):
        return self.two_edge(group_id, self.group_videos, self.video_tags,
                             videos_fields, tags_fields, videos_args, tags_args)

    def group_videos_thumbnails(self, group_id, videos_fields=None,
                                thumbnails_fields=None, videos_args=None,
                                thumbnails_args=None):
        return self.two_edge(group_id, self.group_videos,
                             self.video_thumbnails, videos_fields,
                             thumbnails_fields, videos_args, thumbnails_args)

    def group_videos_insights(self, group_id, videos_fields=None,
                              insights_fields=None, videos_args=None,
                              insights_args=None):
        return self.two_edge(group_id, self.group_videos, self.video_insights,
                             videos_fields, insights_fields, videos_args,
                             insights_args)

    def event(self, event_id, fields=None, **kwargs):
        return self.no_edge(event_id, fields, **kwargs)

    def event_admins(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "admins", fields, **kwargs)

    def event_attending(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "attending", fields, **kwargs)

    def event_comments(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "comments", fields, **kwargs)

    def event_declined(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "declined", fields, **kwargs)

    def event_feed(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "feed", fields, **kwargs)

    def event_feed_likes(self, event_id, feed_fields=None, like_fields=None,
                         feed_args=None, like_args=None):
        return self.two_edge(event_id, self.event_feed, self.post_likes,
                             feed_fields, like_fields, feed_args, like_args)

    def event_feed_reactions(self, event_id, feed_fields=None,
                             reaction_fields=None, feed_args=None,
                             reaction_args=None):
        return self.two_edge(event_id, self.event_feed, self.post_reactions,
                             feed_fields, reaction_fields, feed_args,
                             reaction_args)

    def event_feed_comments(self, event_id, feed_fields=None,
                            comment_fields=None, feed_args=None,
                            comment_args=None):
        return self.two_edge(event_id, self.event_feed, self.post_comments,
                             feed_fields, comment_fields, feed_args,
                             comment_args)

    def event_feed_sharedposts(self, event_id, feed_fields=None,
                               sharedpost_fields=None, feed_args=None,
                               sharedpost_args=None):
        return self.two_edge(event_id, self.event_feed, self.post_sharedposts,
                             feed_fields, sharedpost_fields, feed_args,
                             sharedpost_args)

    def event_feed_attachments(self, event_id, feed_fields=None,
                               attachment_fields=None, feed_args=None,
                               attachment_args=None):
        return self.two_edge(event_id, self.event_feed, self.post_attachments,
                             feed_fields, attachment_fields, feed_args,
                             attachment_args)

    def event_interested(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "interested", fields, **kwargs)

    def event_live_videos(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "live_videos", fields, **kwargs)

    def event_live_videos_likes(self, event_id, live_video_fields=None,
                                like_fields=None, live_video_args=None,
                                like_args=None):
        return self.two_edge(event_id, self.event_live_videos,
                             self.live_video_likes, live_video_fields,
                             like_fields, live_video_args, like_args)

    def event_live_videos_reactions(self, event_id, live_video_fields=None,
                                    reaction_fields=None, live_video_args=None,
                                    reaction_args=None):
        return self.two_edge(event_id, self.event_live_videos,
                             self.live_video_reactions, live_video_fields,
                             reaction_fields, live_video_args, reaction_args)

    def event_live_videos_comments(self, event_id, live_video_fields=None,
                                   comment_fields=None, live_video_args=None,
                                   comment_args=None):
        return self.two_edge(event_id, self.event_live_videos,
                             self.live_video_comments, live_video_fields,
                             comment_fields, live_video_args, comment_args)

    def event_live_videos_errors(self, event_id, live_video_fields=None,
                                 error_fields=None, live_video_args=None,
                                 error_args=None):
        return self.two_edge(event_id, self.event_live_videos,
                             self.live_video_errors, live_video_fields,
                             error_fields, live_video_args, error_args)

    def event_live_videos_blocked_users(self, event_id, live_video_fields=None,
                                        blocked_user_fields=None,
                                        live_video_args=None,
                                        blocked_user_args=None):
        return self.two_edge(event_id, self.event_live_videos,
                             self.live_video_blocked_users, live_video_fields,
                             blocked_user_fields, live_video_args,
                             blocked_user_args)

    def event_maybe(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "maybe", fields, **kwargs)

    def event_noreply(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "noreply", fields, **kwargs)

    def event_photos(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "photos", fields, **kwargs)

    def event_photos_likes(self, event_id, photo_fields=None, like_fields=None,
                           photo_args=None, like_args=None):
        return self.two_edge(event_id, self.event_photos, self.photo_likes,
                             photo_fields, like_fields, photo_args, like_args)

    def event_photos_reactions(self, event_id, photo_fields=None,
                               reaction_fields=None, photo_args=None,
                               reaction_args=None):
        return self.two_edge(event_id, self.event_photos, self.photo_reactions,
                             photo_fields, reaction_fields, photo_args,
                             reaction_args)

    def event_photos_comments(self, event_id, photo_fields=None,
                              comment_fields=None, photo_args=None,
                              comment_args=None):
        return self.two_edge(event_id, self.event_photos, self.photo_comments,
                             photo_fields, comment_fields, photo_args,
                             comment_args)

    def event_photos_sharedposts(self, event_id, photo_fields=None,
                                 sharedpost_fields=None, photo_args=None,
                                 sharedpost_args=None):
        return self.two_edge(event_id, self.event_photos,
                             self.photo_sharedposts, photo_fields,
                             sharedpost_fields, photo_args, sharedpost_args)

    def event_photos_sponsor_tags(self, event_id, photo_fields=None,
                                  sponsor_tag_fields=None, photo_args=None,
                                  sponsor_tag_args=None):
        return self.two_edge(event_id, self.event_photos,
                             self.photo_sponsor_tags, photo_fields,
                             sponsor_tag_fields, photo_args, sponsor_tag_args)

    def event_photos_tags(self, event_id, photo_fields=None, tag_fields=None,
                          photo_args=None, tag_args=None):
        return self.two_edge(event_id, self.event_photos, self.photo_tags,
                             photo_fields, tag_fields, photo_args, tag_args)

    def event_picture(self, event_id, fields=None, **kwargs):
        if not kwargs:
            kwargs = {}
        kwargs['redirect'] = ''

        try:
            response = FacebookApi(self.api_key).node_edge(event_id, "picture",
                                                           params=kwargs)
            return iter([response['data']])
        except ApiError as e:
            raise IterError(e, vars(self))

    def event_roles(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "roles", fields, **kwargs)

    def post(self, post_id, fields=None, **kwargs):
        return self.no_edge(post_id, fields, **kwargs)

    def post_likes(self, post_id, fields=None, **kwargs):
        return self.one_edge(post_id, "likes", fields, **kwargs)

    def post_reactions(self, post_id, fields=None, **kwargs):
        return self.one_edge(post_id, "reactions", fields, **kwargs)

    def post_comments(self, post_id, fields=None, **kwargs):
        return self.one_edge(post_id, "comments", fields, **kwargs)

    def post_sharedposts(self, post_id, fields=None, **kwargs):
        return self.one_edge(post_id, "sharedposts", fields, **kwargs)

    def post_attachments(self, post_id, fields=None, **kwargs):
        return self.one_edge(post_id, "attachments", fields, **kwargs)

    def comment(self, comment_id, fields=None, **kwargs):
        return self.no_edge(comment_id, fields, **kwargs)

    def comment_likes(self, comment_id, fields=None, **kwargs):
        return self.one_edge(comment_id, "likes", fields, **kwargs)

    def comment_reactions(self, comment_id, fields=None, **kwargs):
        return self.one_edge(comment_id, "reactions", fields, **kwargs)

    def comment_comments(self, comment_id, fields=None, **kwargs):
        return self.one_edge(comment_id, "comments", fields, **kwargs)

    def album(self, album_id, fields=None, **kwargs):
        return self.no_edge(album_id, fields, **kwargs)

    def album_picture(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "picture", fields, **kwargs)

    def album_photos(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "photos", fields, **kwargs)

    def album_photos_likes(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "photos_likes", fields, **kwargs)

    def album_photos_reactions(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "photos_reactions", fields, **kwargs)

    def album_photos_comments(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "photos_comments", fields, **kwargs)

    def album_photos_sharedposts(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "photos_sharedposts", fields, **kwargs)

    def album_photos_sponsor_tags(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "photos_sponsor_tags", fields, **kwargs)

    def album_photos_tags(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "photos_tags", fields, **kwargs)

    def album_sharedposts(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "sharedposts", fields, **kwargs)

    def album_likes(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "likes", fields, **kwargs)

    def album_reactions(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "reactions", fields, **kwargs)

    def album_comments(self, album_id, fields=None, **kwargs):
        self.one_edge(album_id, "comments", fields, **kwargs)

    def photo(self, photo_id, fields=None, **kwargs):
        return self.no_edge(photo_id, fields, **kwargs)

    def photo_likes(self, photo_id, fields=None, **kwargs):
        return self.one_edge(photo_id, "likes", fields, **kwargs)

    def photo_reactions(self, photo_id, fields=None, **kwargs):
        return self.one_edge(photo_id, "reactions", fields, **kwargs)

    def photo_comments(self, photo_id, fields=None, **kwargs):
        return self.one_edge(photo_id, "comments", fields, **kwargs)

    def photo_sharedposts(self, photo_id, fields=None, **kwargs):
        return self.one_edge(photo_id, "sharedposts", fields, **kwargs)

    def photo_sponsor_tags(self, photo_id, fields=None, **kwargs):
        return self.one_edge(photo_id, "sponsor_tags", fields, **kwargs)

    def photo_tags(self, photo_id, fields=None, **kwargs):
        return self.one_edge(photo_id, "tags", fields, **kwargs)

    def video(self, video_id, fields=None, **kwargs):
        return self.no_edge(video_id, fields, **kwargs)

    def video_auto_generated_captions(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "auto_generated_captions", fields,
                             **kwargs)

    def video_captions(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "captions", fields, **kwargs)

    def video_comments(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "comments", fields, **kwargs)

    def video_crosspost_shared_pages(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "crosspost_shared_pages", fields,
                             **kwargs)

    def video_likes(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "likes", fields, **kwargs)

    def video_reactions(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "reactions", fields, **kwargs)

    def video_sharedposts(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "sharedposts", fields, **kwargs)

    def video_sponsor_tags(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "sponsor_tags", fields, **kwargs)

    def video_tags(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "tags", fields, **kwargs)

    def video_thumbnails(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "thumbnails", fields, **kwargs)

    def video_insights(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "insights", fields, **kwargs)

    def live_video(self, live_video_id, fields=None, **kwargs):
        return self.no_edge(live_video_id, fields, **kwargs)

    def live_video_likes(self, live_video_id, fields=None, **kwargs):
        return self.one_edge(live_video_id, "likes", fields, **kwargs)

    def live_video_reactions(self, live_video_id, fields=None, **kwargs):
        return self.one_edge(live_video_id, "reactions", fields, **kwargs)

    def live_video_comments(self, live_video_id, fields=None, **kwargs):
        return self.one_edge(live_video_id, "comments", fields, **kwargs)

    def live_video_errors(self, live_video_id, fields=None, **kwargs):
        return self.one_edge(live_video_id, "errors", fields, **kwargs)

    def live_video_blocked_users(self, live_video_id, fields=None, **kwargs):
        return self.one_edge(live_video_id, "blocked_users", fields, **kwargs)

    class FacebookIter(Iter):
        def __init__(self, api_key, node, edge, fields=None,
                     reverse_order=False, **kwargs):
            super().__init__()
            self.api = FacebookApi(api_key)

            self.node = node
            self.edge = edge
            self.fields = fields
            self.params = kwargs

            # Reverse paging order if in reverse mode
            self.next = 'previous' if reverse_order else 'next'
            self.after = 'before' if reverse_order else 'after'

        def get_data(self):
            self.page_count += 1

            try:
                self.response = self.api.node_edge(
                    self.node, self.edge, fields=self.fields,
                    params=self.params)
                self.data = self.response['data']

                paging = self.response.get('paging')

                if not paging:
                    raise StopIteration

                if paging.get('next'):
                    # Parse the next url and extract the params
                    self.params = parse_qs(urlparse(paging[self.next])[4])
                else:
                    if paging.get('cursors'):
                        # Replace the after paramater
                        self.params[self.after] = paging['cursors'][self.after]
                    else:
                        raise StopIteration

            except ApiError as e:
                raise IterError(e, vars(self))