import shutil
from pathlib import Path

from unstructured.ingest.pipeline.file_handler.interfaces import FileHandler, FileStat


class LocalFileHandler(FileHandler):
    def cp(self, path1: str, path2: str, decrypt: bool = False):
        if not decrypt:
            shutil.copy(path1, path2)
            return
        decrypted_data = self.read(path1)
        with open(path2, "w") as output_f:
            output_f.write(decrypted_data)

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
