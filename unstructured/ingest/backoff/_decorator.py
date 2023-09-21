# coding:utf-8
import logging
from typing import Any, Callable, Iterable, Optional, Type, Union

from backoff._common import _config_handlers, _log_backoff, _log_giveup, _prepare_logger
from backoff._jitter import full_jitter
from backoff._typing import (
    _CallableT,
    _Handler,
    _Jitterer,
    _MaybeCallable,
    _MaybeLogger,
    _MaybeSequence,
    _Predicate,
    _WaitGenerator,
)

from unstructured.ingest.backoff import _sync


def on_exception(
    wait_gen: _WaitGenerator,
    exception: _MaybeSequence[Type[Exception]],
    *,
    max_tries: Optional[_MaybeCallable[int]] = None,
    max_time: Optional[_MaybeCallable[float]] = None,
    jitter: Union[_Jitterer, None] = full_jitter,
    giveup: _Predicate[Exception] = lambda e: False,
    on_success: Union[_Handler, Iterable[_Handler], None] = None,
    on_backoff: Union[_Handler, Iterable[_Handler], None] = None,
    on_giveup: Union[_Handler, Iterable[_Handler], None] = None,
    raise_on_giveup: bool = True,
    logger: _MaybeLogger = "backoff",
    backoff_log_level: int = logging.INFO,
    giveup_log_level: int = logging.ERROR,
    **wait_gen_kwargs: Any,
) -> Callable[[_CallableT], _CallableT]:
    """Returns decorator for backoff and retry triggered by exception.

    Args:
        wait_gen: A generator yielding successive wait times in
            seconds.
        exception: An exception type (or tuple of types) which triggers
            backoff.
        jitter: A function of the value yielded by wait_gen returning
            the actual time to wait. This distributes wait times
            stochastically in order to avoid timing collisions across
            concurrent clients. Wait times are jittered by default
            using the full_jitter function. Jittering may be disabled
            altogether by passing jitter=None.
        giveup: Function accepting an exception instance and
            returning whether or not to give up. Optional. The default
            is to always continue.
        on_success: Callable (or iterable of callables) with a unary
            signature to be called in the event of success. The
            parameter is a dict containing details about the invocation.
        on_backoff: Callable (or iterable of callables) with a unary
            signature to be called in the event of a backoff. The
            parameter is a dict containing details about the invocation.
        on_giveup: Callable (or iterable of callables) with a unary
            signature to be called in the event that max_tries
            is exceeded.  The parameter is a dict containing details
            about the invocation.
        raise_on_giveup: Boolean indicating whether the registered exceptions
            should be raised on giveup. Defaults to `True`
        logger: Name or Logger object to log to. Defaults to 'backoff'.
        backoff_log_level: log level for the backoff event. Defaults to "INFO"
        giveup_log_level: log level for the give up event. Defaults to "ERROR"
        **wait_gen_kwargs: Any additional keyword args specified will be
            passed to wait_gen when it is initialized.  Any callable
            args will first be evaluated and their return values passed.
            This is useful for runtime configuration.
    """

    def decorate(target):
        nonlocal logger, on_success, on_backoff, on_giveup

        logger = _prepare_logger(logger)
        on_success = _config_handlers(on_success)
        on_backoff = _config_handlers(
            on_backoff,
            default_handler=_log_backoff,
            logger=logger,
            log_level=backoff_log_level,
        )
        on_giveup = _config_handlers(
            on_giveup,
            default_handler=_log_giveup,
            logger=logger,
            log_level=giveup_log_level,
        )

        return _sync.retry_exception(
            target,
            wait_gen,
            exception,
            jitter=jitter,
            giveup=giveup,
            on_success=on_success,
            on_backoff=on_backoff,
            on_giveup=on_giveup,
            raise_on_giveup=raise_on_giveup,
            wait_gen_kwargs=wait_gen_kwargs,
        )

    # Return a function which decorates a target with a retry loop.
    return decorate
