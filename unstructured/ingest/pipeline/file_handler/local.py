from pathlib import Path

from unstructured.ingest.pipeline.file_handler.interfaces import FileHandler, FileStat


class LocalFileHandler(FileHandler):
    def stat(self, filepath: str) -> FileStat:
        path = Path(filepath)
        if path.exists():
            return FileStat(exists=True, is_file=path.is_file(), size=path.stat().st_size)
        return FileStat(exists=False)

    def _write(self, data: str, filepath: str):
        with open(filepath, "w") as output_f:
            output_f.write(data)

    def _read(self, filepath: str) -> str:
        with open(filepath) as output_f:
            return output_f.read()
