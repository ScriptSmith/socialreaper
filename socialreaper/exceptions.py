from pprint import pformat


class ApiError(Exception):
    """The non-fatal failure of the api to fulfill a request"""

    def __init__(self, error):
        self.error = error

    def __str__(self):
        string = ""
        if hasattr(self.error, 'request'):
            string += pformat(vars(self.error.request))
        if hasattr(self.error, 'response'):
            string += pformat(vars(self.error.response))
        return string


class FatalApiError(ApiError):
    """The fatal failure of the api to fulfill a request"""
