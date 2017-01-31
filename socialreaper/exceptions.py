class ApiError(Exception):
    """The non-fatal failure of the api to fulfill a request"""


class FatalApiError(Exception):
    """The fatal failure of the api to fulfill a request"""
