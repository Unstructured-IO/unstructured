from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union


class AnalysisProcessor(ABC):
    def __init__(
        self,
        filename: Union[str, Path],
        save_dir: Union[str, Path],
    ):
        self.filename = filename
        self.save_dir = save_dir

    @abstractmethod
    def process(self):
        """Performs the analysis and saves the results"""
        raise NotImplementedError()
