import logging
import sys
import traceback


# Default backoff handler
def _log_backoff(details, logger, log_level):
    if log_level >= logging.INFO:
        msg = "Backing off %s(...) for %.1fs (%s)"
        log_args = [details["target"].__name__, details["tries"]]
    else:
        msg = "Backing off %.1fs seconds after %d tries calling function %s(%s) -> %s"
        target_input_list = []
        if args := details.get("args"):
            target_input_list.extend([str(d) for d in args])
        if kwargs := details.get("kwargs"):
            target_input_list.extend([f"{k}={str(v)}" for k, v in kwargs.items()])
        target_input = ", ".join(target_input_list) if target_input_list else "..."
        log_args = [
            details["wait"],
            details["tries"],
            details["target"].__name__,
            target_input,
        ]
    exc_typ, exc, _ = sys.exc_info()
    if exc is not None:
        exc_fmt = traceback.format_exception_only(exc_typ, exc)[-1]
        log_args.append(exc_fmt.rstrip("\n"))
    else:
        log_args.append(str(details["value"]))
    logger.log(log_level, msg, *log_args)


# Default giveup handler
def _log_giveup(details, logger, log_level):
    if log_level >= logging.INFO:
        msg = "Giving up %s(...) after %.1fs tried(%s)"
        log_args = [details["target"].__name__, details["tries"]]
    else:
        msg = "Giving up after %d tries (%.1fs) calling function %s(%s) -> %s"
        target_input_list = []
        if args := details.get("args"):
            target_input_list.extend([str(d) for d in args])
        if kwargs := details.get("kwargs"):
            target_input_list.extend([f"{k}={str(v)}" for k, v in kwargs.items()])
        target_input = ", ".join(target_input_list) if target_input_list else "..."
        log_args = [
            details["tries"],
            details["wait"],
            details["target"].__name__,
            target_input,
        ]

    exc_typ, exc, _ = sys.exc_info()
    if exc is not None:
        exc_fmt = traceback.format_exception_only(exc_typ, exc)[-1]
        log_args.append(exc_fmt.rstrip("\n"))
    else:
        log_args.append(details["value"])

    logger.log(log_level, msg, *log_args)
