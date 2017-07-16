from apis import Facebook as FacebookApi
from exceptions import ApiError, FatalApiError
from urllib.parse import urlparse, parse_qs
from os import environ, mkdir
from tools import to_csv


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

    def test(self):
        try:
            api = FacebookApi(self.api_key)
            api.api_call('facebook', {'access_token': self.api_key})
            return True, "Working"

        except ApiError as e:
            return False, e

    def no_edge(self, node, fields, **kwargs):
        return self.FacebookIter(self.api_key, node, "", fields, **kwargs)

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

    def page_events_admins(self):
        pass

    def page_events_attending(self):
        pass

    def page_events_comments(self):
        pass

    def page_events_declined(self):
        pass

    def page_events_feed(self):
        pass

    def page_events_feed_likes(self):
        pass

    def page_events_feed_reactions(self):
        pass

    def page_events_feed_comments(self):
        pass

    def page_events_feed_sharedposts(self):
        pass

    def page_events_feed_attachments(self):
        pass

    def page_events_interested(self):
        pass

    def page_events_live_videos(self):
        pass

    def page_events_live_videos_likes(self):
        pass

    def page_events_live_videos_reactions(self):
        pass

    def page_events_live_videos_comments(self):
        pass

    def page_events_live_videos_errors(self):
        pass

    def page_events_live_videos_blocked_users(self):
        pass

    def page_events_maybe(self):
        pass

    def page_events_noreply(self):
        pass

    def page_events_photos(self):
        pass

    def page_events_photos_likes(self):
        pass

    def page_events_photos_reactions(self):
        pass

    def page_events_photos_comments(self):
        pass

    def page_events_photos_sharedposts(self):
        pass

    def page_events_photos_sponsor_tags(self):
        pass

    def page_events_photos_tags(self):
        pass

    def page_events_picture(self):
        pass

    def page_events_roles(self):
        pass

    def page_events_videos(self):
        pass

    def page_events_videos_likes(self):
        pass

    def page_events_videos_reactions(self):
        pass

    def page_events_videos_comments(self):
        pass

    def page_events_videos_sharedposts(self):
        pass

    def page_events_videos(self):
        pass

    def page_events_videos_auto_generated_captions(self):
        pass

    def page_events_videos_captions(self):
        pass

    def page_events_videos_comments(self):
        pass

    def page_events_videos_crosspost_shared_pages(self):
        pass

    def page_events_videos_likes(self):
        pass

    def page_events_videos_reactions(self):
        pass

    def page_events_videos_sharedposts(self):
        pass

    def page_events_videos_sponsor_tags(self):
        pass

    def page_events_videos_tags(self):
        pass

    def page_events_videos_thumbnails(self):
        pass

    def page_events_videos_insights(self):
        pass

    def page_albums(self):
        pass

    def page_albums_picture(self):
        pass

    def page_albums_photos(self):
        pass

    def page_albums_photos_likes(self):
        pass

    def page_albums_photos_reactions(self):
        pass

    def page_albums_photos_comments(self):
        pass

    def page_albums_photos_sharedposts(self):
        pass

    def page_albums_photos_sponsor_tags(self):
        pass

    def page_albums_photos_tags(self):
        pass

    def page_albums_sharedposts(self):
        pass

    def page_albums_likes(self):
        pass

    def page_albums_reactions(self):
        pass

    def page_albums_comments(self):
        pass

    def page_photos(self):
        pass

    def page_photos_likes(self):
        pass

    def page_photos_reactions(self):
        pass

    def page_photos_comments(self):
        pass

    def page_photos_sharedposts(self):
        pass

    def page_photos_sponsor_tags(self):
        pass

    def page_photos_tags(self):
        pass

    def page_live_videos(self):
        pass

    def page_live_videos_likes(self):
        pass

    def page_live_videos_reactions(self):
        pass

    def page_live_videos_comments(self):
        pass

    def page_live_videos_errors(self):
        pass

    def page_live_videos_blocked_users(self):
        pass

    def page_videos(self):
        pass

    def page_videos_auto_generated_captions(self):
        pass

    def page_videos_captions(self):
        pass

    def page_videos_comments(self):
        pass

    def page_videos_crosspost_shared_pages(self):
        pass

    def page_videos_likes(self):
        pass

    def page_videos_reactions(self):
        pass

    def page_videos_sharedposts(self):
        pass

    def page_videos_sponsor_tags(self):
        pass

    def page_videos_tags(self):
        pass

    def page_videos_thumbnails(self):
        pass

    def page_videos_insights(self):
        pass

    def page_picture(self):
        pass

    def group(self, group_id, fields=None, **kwargs):
        return iter([])

    def group_admins(self):
        pass

    def group_albums(self):
        pass

    def group_albums_picture(self):
        pass

    def group_albums_photos(self):
        pass

    def group_albums_photos_likes(self):
        pass

    def group_albums_photos_reactions(self):
        pass

    def group_albums_photos_comments(self):
        pass

    def group_albums_photos_sharedposts(self):
        pass

    def group_albums_photos_sponsor_tags(self):
        pass

    def group_albums_photos_tags(self):
        pass

    def group_albums_sharedposts(self):
        pass

    def group_albums_likes(self):
        pass

    def group_albums_reactions(self):
        pass

    def group_albums_comments(self):
        pass

    def group_docs(self):
        pass

    def group_events_admins(self):
        pass

    def group_events_attending(self):
        pass

    def group_events_comments(self):
        pass

    def group_events_declined(self):
        pass

    def group_events_feed(self):
        pass

    def group_events_feed_likes(self):
        pass

    def group_events_feed_reactions(self):
        pass

    def group_events_feed_comments(self):
        pass

    def group_events_feed_sharedposts(self):
        pass

    def group_events_feed_attachments(self):
        pass

    def group_events_interested(self):
        pass

    def group_events_live_videos(self):
        pass

    def group_events_live_videos_likes(self):
        pass

    def group_events_live_videos_reactions(self):
        pass

    def group_events_live_videos_comments(self):
        pass

    def group_events_live_videos_errors(self):
        pass

    def group_events_live_videos_blocked_users(self):
        pass

    def group_events_maybe(self):
        pass

    def group_events_noreply(self):
        pass

    def group_events_photos(self):
        pass

    def group_events_photos_likes(self):
        pass

    def group_events_photos_reactions(self):
        pass

    def group_events_photos_comments(self):
        pass

    def group_events_photos_sharedposts(self):
        pass

    def group_events_photos_sponsor_tags(self):
        pass

    def group_events_photos_tags(self):
        pass

    def group_events_picture(self):
        pass

    def group_events_roles(self):
        pass

    def group_events_videos(self):
        pass

    def group_events_videos_likes(self):
        pass

    def group_events_videos_reactions(self):
        pass

    def group_events_videos_comments(self):
        pass

    def group_events_videos_sharedposts(self):
        pass

    def group_events_videos(self):
        pass

    def group_events_videos_auto_generated_captions(self):
        pass

    def group_events_videos_captions(self):
        pass

    def group_events_videos_comments(self):
        pass

    def group_events_videos_crosspost_shared_pages(self):
        pass

    def group_events_videos_likes(self):
        pass

    def group_events_videos_reactions(self):
        pass

    def group_events_videos_sharedposts(self):
        pass

    def group_events_videos_sponsor_tags(self):
        pass

    def group_events_videos_tags(self):
        pass

    def group_events_videos_thumbnails(self):
        pass

    def group_events_videos_insights(self):
        pass

    def group_feed(self):
        pass

    def group_feed_likes(self):
        pass

    def group_feed_reactions(self):
        pass

    def group_feed_comments(self):
        pass

    def group_feed_sharedposts(self):
        pass

    def group_feed_attachments(self):
        pass

    def group_files(self):
        pass

    def group_live_videos(self):
        pass

    def group_live_videos_likes(self):
        pass

    def group_live_videos_reactions(self):
        pass

    def group_live_videos_comments(self):
        pass

    def group_live_videos_errors(self):
        pass

    def group_live_videos_blocked_users(self):
        pass

    def group_members(self):
        pass

    def group_photos(self):
        pass

    def group_photos_likes(self):
        pass

    def group_photos_reactions(self):
        pass

    def group_photos_comments(self):
        pass

    def group_photos_sharedposts(self):
        pass

    def group_photos_sponsor_tags(self):
        pass

    def group_photos_tags(self):
        pass

    def group_videos(self, video_id, fields=None, **kwargs):
        return self.one_edge(video_id, "videos", fields, **kwargs)

    def group_videos_auto_generated_captions(self, video_id, videos_fields=None,
                                             auto_generated_captions_fields=None,
                                             videos_args=None,
                                             auto_generated_captions_args=None):
        return self.two_edge(video_id, self.group_videos,
                             self.videos_auto_generated_captions, videos_fields,
                             auto_generated_captions_fields, videos_args,
                             auto_generated_captions_args)

    def group_videos_captions(self, video_id, videos_fields=None,
                              captions_fields=None, videos_args=None,
                              captions_args=None):
        return self.two_edge(video_id, self.group_videos, self.videos_captions,
                             videos_fields, captions_fields, videos_args,
                             captions_args)

    def group_videos_comments(self, video_id, videos_fields=None,
                              comments_fields=None, videos_args=None,
                              comments_args=None):
        return self.two_edge(video_id, self.group_videos, self.videos_comments,
                             videos_fields, comments_fields, videos_args,
                             comments_args)

    def group_videos_crosspost_shared_pages(self, video_id, videos_fields=None,
                                            crosspost_shared_pages_fields=None,
                                            videos_args=None,
                                            crosspost_shared_pages_args=None):
        return self.two_edge(video_id, self.group_videos,
                             self.videos_crosspost_shared_pages, videos_fields,
                             crosspost_shared_pages_fields, videos_args,
                             crosspost_shared_pages_args)

    def group_videos_likes(self, video_id, videos_fields=None,
                           likes_fields=None, videos_args=None,
                           likes_args=None):
        return self.two_edge(video_id, self.group_videos, self.videos_likes,
                             videos_fields, likes_fields, videos_args,
                             likes_args)

    def group_videos_reactions(self, video_id, videos_fields=None,
                               reactions_fields=None, videos_args=None,
                               reactions_args=None):
        return self.two_edge(video_id, self.group_videos, self.videos_reactions,
                             videos_fields, reactions_fields, videos_args,
                             reactions_args)

    def group_videos_sharedposts(self, video_id, videos_fields=None,
                                 sharedposts_fields=None, videos_args=None,
                                 sharedposts_args=None):
        return self.two_edge(video_id, self.group_videos,
                             self.videos_sharedposts, videos_fields,
                             sharedposts_fields, videos_args, sharedposts_args)

    def group_videos_sponsor_tags(self, video_id, videos_fields=None,
                                  sponsor_tags_fields=None, videos_args=None,
                                  sponsor_tags_args=None):
        return self.two_edge(video_id, self.group_videos,
                             self.videos_sponsor_tags, videos_fields,
                             sponsor_tags_fields, videos_args,
                             sponsor_tags_args)

    def group_videos_tags(self, video_id, videos_fields=None, tags_fields=None,
                          videos_args=None, tags_args=None):
        return self.two_edge(video_id, self.group_videos, self.videos_tags,
                             videos_fields, tags_fields, videos_args, tags_args)

    def group_videos_thumbnails(self, video_id, videos_fields=None,
                                thumbnails_fields=None, videos_args=None,
                                thumbnails_args=None):
        return self.two_edge(video_id, self.group_videos,
                             self.videos_thumbnails, videos_fields,
                             thumbnails_fields, videos_args, thumbnails_args)

    def group_videos_insights(self, video_id, videos_fields=None,
                              insights_fields=None, videos_args=None,
                              insights_args=None):
        return self.two_edge(video_id, self.group_videos, self.videos_insights,
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

    def event_videos(self, event_id, fields=None, **kwargs):
        return self.one_edge(event_id, "videos", fields, **kwargs)

    def event_videos_auto_generated_captions(self, event_id, event_fields=None,
                                             auto_generated_caption_fields=None,
                                             event_args=None,
                                             auto_generated_caption_args=None):
        return self.two_edge(event_id, self.event_videos,
                             self.video_auto_generated_captions, event_fields,
                             auto_generated_caption_fields, event_args,
                             auto_generated_caption_args)

    def event_videos_captions(self, event_id, event_fields=None,
                              caption_fields=None, event_args=None,
                              caption_args=None):
        return self.two_edge(event_id, self.event_videos, self.video_captions,
                             event_fields, caption_fields, event_args,
                             caption_args)

    def event_videos_comments(self, event_id, event_fields=None,
                              comment_fields=None, event_args=None,
                              comment_args=None):
        return self.two_edge(event_id, self.event_videos, self.video_comments,
                             event_fields, comment_fields, event_args,
                             comment_args)

    def event_videos_crosspost_shared_pages(self, event_id, event_fields=None,
                                            crosspost_shared_page_fields=None,
                                            event_args=None,
                                            crosspost_shared_page_args=None):
        return self.two_edge(event_id, self.event_videos,
                             self.video_crosspost_shared_pages, event_fields,
                             crosspost_shared_page_fields, event_args,
                             crosspost_shared_page_args)

    def event_videos_likes(self, event_id, event_fields=None, like_fields=None,
                           event_args=None, like_args=None):
        return self.two_edge(event_id, self.event_videos, self.video_likes,
                             event_fields, like_fields, event_args, like_args)

    def event_videos_reactions(self, event_id, event_fields=None,
                               reaction_fields=None, event_args=None,
                               reaction_args=None):
        return self.two_edge(event_id, self.event_videos, self.video_reactions,
                             event_fields, reaction_fields, event_args,
                             reaction_args)

    def event_videos_sharedposts(self, event_id, event_fields=None,
                                 sharedpost_fields=None, event_args=None,
                                 sharedpost_args=None):
        return self.two_edge(event_id, self.event_videos,
                             self.video_sharedposts, event_fields,
                             sharedpost_fields, event_args, sharedpost_args)

    def event_videos_sponsor_tags(self, event_id, event_fields=None,
                                  sponsor_tag_fields=None, event_args=None,
                                  sponsor_tag_args=None):
        return self.two_edge(event_id, self.event_videos,
                             self.video_sponsor_tags, event_fields,
                             sponsor_tag_fields, event_args, sponsor_tag_args)

    def event_videos_tags(self, event_id, event_fields=None, tag_fields=None,
                          event_args=None, tag_args=None):
        return self.two_edge(event_id, self.event_videos, self.video_tags,
                             event_fields, tag_fields, event_args, tag_args)

    def event_videos_thumbnails(self, event_id, event_fields=None,
                                thumbnail_fields=None, event_args=None,
                                thumbnail_args=None):
        return self.two_edge(event_id, self.event_videos, self.video_thumbnails,
                             event_fields, thumbnail_fields, event_args,
                             thumbnail_args)

    def event_videos_insights(self, event_id, event_fields=None,
                              insight_fields=None, event_args=None,
                              insight_args=None):
        return self.two_edge(event_id, self.event_videos, self.video_insights,
                             event_fields, insight_fields, event_args,
                             insight_args)

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
        def __init__(self, api_key, node, edge, fields=None, **kwargs):
            super().__init__()
            self.api = FacebookApi(api_key)

            self.node = node
            self.edge = edge
            self.fields = fields
            self.params = kwargs

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
                    self.params = parse_qs(urlparse(paging['next'])[4])
                else:
                    if paging.get('cursors'):
                        self.params['after'] = paging['cursors']['after']
                    else:
                        raise StopIteration

            except ApiError as e:
                raise IterError(e, vars(self))

fbk = Facebook(environ['facebook_api_key'])
fields = ["from", "type", "message", "link", "actions", "place", "tags", "created_time",
          "object_attachment", "targeting", "feed_targeting", "published",
          "scheduled_publish_time", "backdated_time",
          "backdated_time_granularity", "child_attachments",
          "multi_share_optimized", "multi_share_end_card",
          "reactions.type(LIKE).limit(0).summary(total_count).as(reactions_like)",
          "reactions.type(LOVE).limit(0).summary(total_count).as(reactions_love)",
          "reactions.type(HAHA).limit(0).summary(total_count).as(reactions_haha)",
          "reactions.type(WOW).limit(0).summary(total_count).as(reactions_wow)",
          "reactions.type(SAD).limit(0).summary(total_count).as(reactions_sad)",
          "reactions.type(ANGRY).limit(0).summary(total_count).as(reactions_angry)",
          "likes.limit(0).summary(total_count)",
          "comments.limit(0).summary(total_count)",
          "shares.limit(0).summary(total_count)"]
pages = ["SmirnoffAustralia","JohnnieWalkerAustralia","BacardiAustralia","absolutAU","JagermeisterAustralia","JimBeamAustralia","Jameson.Australia","eljimadoraustralia","JacobsCreekAustralia","Rekorderlig.Cider","wildturkeyau","BundabergRum","canadianclubAUS","PureBlonde","JackDanielsAustralia","BaileysAustralia","AmericanHoneyAustralia","CarltonDryAustralia","Tooheys","XXXXGOLD","VB","CaptainMorganAustralia","DrinkMidori","CarltonDraught","xxxxsummerbrightlager","WolfBlassWinesAus","magnersaustralia","strongbowaustralia","Coopers","littlecreaturesbrewing","yellowglen","CoronaExtraAustralia","vodkacruiser","stoneandwoodbrewing","jamessquire","BudweiserAustralia","GreatNorthernBrewingCompany","YakAles","heineken","SolBeerAustralia","hahn","BulleitAus","GreyGooseAU","aperolspritz.au"]

for page in pages:
    feed = list(fbk.page_feed(page, fields=fields, limit=100))
    to_csv(feed, filename=f"{page}.csv")