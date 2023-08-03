import multiprocessing as mp
from typing import Any, Optional


class ProcessorResourceSingleton:
    """
    Singleton class for managing shared resources among multiple processes.

    This class ensures that each process gets its own instance of shared resources,
    such as connections, keys, sessions, and other arbitrary data.
    """

    _instances: dict = {}

    def __new__(cls) -> "ProcessorResourceSingleton":
        pid = mp.current_process().pid
        if pid not in cls._instances:
            cls._instances[pid] = super().__new__(cls)
            cls._instances[pid]._data_store = {}  # Initialize the data store for this process
        return cls._instances[pid]

    def set_data(self, key: str, value: Any) -> None:
        """Set data with the given key and value in the data store."""
        self._data_store[key] = value

    def get_data(self, key: str) -> Optional[Any]:
        """Get the value of data with the given key from the data store."""
        return self._data_store.get(key)
