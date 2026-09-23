import logging


def translate_log_level(level: int) -> int:
    """Translate Python debugg level to ONNX runtime error level
    since blank pages error are shown at level 3 that should be the
    exception, and 4 the normal behavior"""
    level_name = logging.getLevelName(level)
    onnx_level = 0
    if level_name in ["NOTSET", "DEBUG", "INFO", "WARNING"]:
        onnx_level = 4
    elif level_name in ["ERROR", "CRITICAL"]:
        onnx_level = 3

    return onnx_level


logger = logging.getLogger("unstructured_inference")

logger_onnx = logging.getLogger("unstructured_inference_onnxruntime")
logger_onnx.setLevel(translate_log_level(logger.getEffectiveLevel()))
