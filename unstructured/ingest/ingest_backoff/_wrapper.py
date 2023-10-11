# coding:utf-8
import logging
from collections.abc import Iterable as IterableType
from typing import Any, Iterable, Optional, Type, Union

from backoff import _sync
from backoff._common import _config_handlers, _prepare_logger
from backoff._jitter import full_jitter
from backoff._typing import (
    _Handler,
    _Jitterer,
    _MaybeCallable,
    _MaybeLogger,
    _MaybeSequence,
    _Predicate,
    _WaitGenerator,
)

from unstructured.ingest.ingest_backoff._common import _log_backoff, _log_giveup, _log_start


class RetryHandler:
    def __init__(
        self,
        wait_gen: _WaitGenerator,
        exception: _MaybeSequence[Type[Exception]],
        *,
        max_tries: Optional[_MaybeCallable[int]] = None,
        max_time: Optional[_MaybeCallable[float]] = None,
        jitter: Union[_Jitterer, None] = full_jitter,
        giveup: _Predicate[Exception] = lambda e: False,
        on_start: Union[_Handler, Iterable[_Handler], None] = None,
        on_success: Union[_Handler, Iterable[_Handler], None] = None,
        on_backoff: Union[_Handler, Iterable[_Handler], None] = None,
        on_giveup: Union[_Handler, Iterable[_Handler], None] = None,
        raise_on_giveup: bool = True,
        logger: _MaybeLogger = "backoff",
        start_log_level: int = logging.INFO,
        backoff_log_level: int = logging.INFO,
        giveup_log_level: int = logging.ERROR,
        **wait_gen_kwargs: Any,
    ):
        prepared_logger = _prepare_logger(logger)
        on_success = _config_handlers(on_success)
        on_start = _config_handlers(
            on_start,
            default_handler=_log_start,
            logger=prepared_logger,
            log_level=start_log_level,
        )
        on_backoff = _config_handlers(
            on_backoff,
            default_handler=_log_backoff,
            logger=prepared_logger,
            log_level=backoff_log_level,
        )
        on_giveup = _config_handlers(
            on_giveup,
            default_handler=_log_giveup,
            logger=prepared_logger,
            log_level=giveup_log_level,
        )
        prepared_logger.debug(
            "Initiating retry handler with "
            "max_tries={}, "
            "max_time={}, "
            "exception={}, "
            "start_log_level={}, "
            "backoff_log_level={}, "
            "giveup_log_level={}".format(
                max_tries,
                max_time,
                ", ".join([e.__name__ for e in exception])
                if isinstance(exception, IterableType)
                else exception.__name__,
                logging.getLevelName(start_log_level),
                logging.getLevelName(backoff_log_level),
                logging.getLevelName(giveup_log_level),
            ),
        )
        self.on_start = on_start
        self.on_success = on_success
        self.on_backoff = on_backoff
        self.on_giveup = on_giveup
        self.jitter = jitter
        self.giveup = giveup
        self.raise_on_giveup = raise_on_giveup
        self.wait_gen_kwargs = wait_gen_kwargs
        self.wait_gen = wait_gen
        self.exception = exception
        self.max_tries = max_tries
        self.max_time = max_time

    def __call__(self, target, *args, **kwargs):
        _sync._call_handlers(
            self.on_start,
            target=target,
            args=args,
            kwargs=kwargs,
            tries=None,
            elapsed=None,
            max_tries=self.max_tries,
            max_time=self.max_time,
            exception=self.exception,
        )
        wrapped_func = _sync.retry_exception(
            target,
            self.wait_gen,
            self.exception,
            max_tries=self.max_tries,
            max_time=self.max_time,
            jitter=self.jitter,
            giveup=self.giveup,
            on_success=self.on_success,
            on_backoff=self.on_backoff,
            on_giveup=self.on_giveup,
            raise_on_giveup=self.raise_on_giveup,
            wait_gen_kwargs=self.wait_gen_kwargs,
        )
        return wrapped_func(*args, **kwargs)
