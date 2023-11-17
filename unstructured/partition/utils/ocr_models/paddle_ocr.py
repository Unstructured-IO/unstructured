import functools

from unstructured.logger import logger
from unstructured.partition.utils.constants import DEFAULT_PADDLE_LANG


@functools.lru_cache(maxsize=None)
def load_agent(language: str = DEFAULT_PADDLE_LANG):
    import paddle
    from unstructured_paddleocr import PaddleOCR

    """Loads the PaddleOCR agent as a global variable to ensure that we only load it once."""

    # Disable signal handlers at C++ level upon failing
    # ref: https://www.paddlepaddle.org.cn/documentation/docs/en/api/paddle/
    #      disable_signal_handler_en.html#disable-signal-handler
    paddle.disable_signal_handler()
    # Use paddlepaddle-gpu if there is gpu device available
    gpu_available = paddle.device.cuda.device_count() > 0
    if gpu_available:
        logger.info(f"Loading paddle with GPU on language={language}...")
    else:
        logger.info(f"Loading paddle with CPU on language={language}...")
    try:
        # Enable MKL-DNN for paddle to speed up OCR if OS supports it
        # ref: https://paddle-inference.readthedocs.io/en/master/
        #      api_reference/cxx_api_doc/Config/CPUConfig.html
        paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            use_gpu=gpu_available,
            lang=language,
            enable_mkldnn=True,
            show_log=False,
        )
    except AttributeError:
        paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            use_gpu=gpu_available,
            lang=language,
            enable_mkldnn=False,
            show_log=False,
        )
    return paddle_ocr
