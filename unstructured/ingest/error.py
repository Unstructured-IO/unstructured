from abc import ABC
from functools import wraps


class CustomError(Exception, ABC):
    error_string: str

    @classmethod
    def wrap(cls, f):
        """
        Provides a wrapper for a function that catches any exception and
        re-raises it as the customer error. If the exception itself is already an instance
        of the custom error, re-raises original error.
        """

        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except BaseException as error:
                if not isinstance(error, cls) and not issubclass(type(error), cls):
                    raise cls(cls.error_string.format(str(error))) from error
                raise

        return wrapper


class SourceConnectionError(CustomError):
    error_string = "Error in getting data from upstream data source: {}"


class SourceConnectionNetworkError(SourceConnectionError):
    error_string = "Error in connecting to upstream data source: {}"


class DestinationConnectionError(CustomError):
    error_string = "Error in connecting to downstream data source: {}"


class EmbeddingEncoderConnectionError(CustomError):
    error_string = "Error in connecting to the embedding model provider: {}"


class WriteError(CustomError):
    error_string = "Error in writing to downstream data source: {}"


class PartitionError(CustomError):
    error_string = "Error in partitioning content: {}"
