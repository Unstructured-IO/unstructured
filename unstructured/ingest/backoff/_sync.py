# coding:utf-8
import datetime
import functools
import time
from datetime import timedelta

from backoff._common import _init_wait_gen, _maybe_call, _next_wait
from backoff._sync import _call_handlers

from unstructured.ingest.backoff._strategy import RetryStrategy


def retry_exception(
    target,
    wait_gen,
    exception,
    *,
    jitter,
    giveup,
    on_success,
    on_backoff,
    on_giveup,
    raise_on_giveup,
    wait_gen_kwargs,
):
    @functools.wraps(target)
    def retry(self, *args, **kwargs):
        if not hasattr(self, "retry_strategy"):
            return target(self, *args, **kwargs)
        retry_strategy: RetryStrategy = self.retry_strategy
        if not retry_strategy:
            return target(self, *args, **kwargs)
        max_tries_value = _maybe_call(retry_strategy.max_tries)
        max_time_value = _maybe_call(retry_strategy.max_time)

        tries = 0
        start = datetime.datetime.now()
        wait = _init_wait_gen(wait_gen, wait_gen_kwargs)
        while True:
            tries += 1
            elapsed = timedelta.total_seconds(datetime.datetime.now() - start)
            details = {
                "target": target,
                "args": args,
                "kwargs": kwargs,
                "tries": tries,
                "elapsed": elapsed,
            }

            try:
                ret = target(self, *args, **kwargs)
            except exception as e:
                max_tries_exceeded = tries == max_tries_value
                max_time_exceeded = max_time_value is not None and elapsed >= max_time_value

                if giveup(e) or max_tries_exceeded or max_time_exceeded:
                    _call_handlers(on_giveup, **details, exception=e)
                    if raise_on_giveup:
                        raise
                    return None

                try:
                    seconds = _next_wait(wait, e, jitter, elapsed, max_time_value)
                except StopIteration:
                    _call_handlers(on_giveup, **details, exception=e)
                    raise e

                _call_handlers(on_backoff, **details, wait=seconds, exception=e)

                time.sleep(seconds)
            else:
                _call_handlers(on_success, **details)

                return ret

    return retry
