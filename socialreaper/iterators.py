from .apis import Facebook as FacebookApi
from .exceptions import ApiError, FatalApiError
from urllib.parse import urlparse, parse_qs
from .builders import FacebookFunctions


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

        # Key used on inner functions
        self.inner_key = None

        # Inner iter to obtain data from
        self.inner = None

        # The function to create the inner iter from
        self.inner_func = inner_func

        # The inner function's arguments
        self.inner_args = inner_args

        self.include_parents = False
        if inner_args.get('include_parents'):
            self.include_parents = inner_args.pop('include_parents')

        # Does the outer iter need a step
        self.outer_jump = True

    def __iter__(self):
        return self

    def __next__(self):
        # If outer iter needs to step
        if self.outer_jump:
            # Get key from outer iter's return
            # When outer iter is over, StopIteration is raised
            self.inner_key = self.outer.__next__().get(self.key)
            # Create the inner iter by calling the function with key and args
            self.inner = self.inner_func(self.inner_key, **self.inner_args)
            # Toggle jumping off
            self.outer_jump = False

        # Return data from inner iter
        try:
            next_item = self.inner.__next__()
            if self.include_parents:
                next_item['parent_id'] = self.inner_key
            return next_item
            # return self.inner.__next__()
        except StopIteration:
            # If inner iter is over, step outer
            self.outer_jump = True
            return self.__next__()


class Facebook(Source, FacebookFunctions):
    def __init__(self, api_key):
        super().__init__()
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

    def iter_iter(self, *args, **kwargs):
        return IterIter(*args, **kwargs)

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
                        # Replace the after parameter
                        self.params[self.after] = paging['cursors'][self.after]
                    else:
                        raise StopIteration

            except ApiError as e:
                raise IterError(e, vars(self))