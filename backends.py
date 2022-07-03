import functools
import logging
import pickle
import os.path
from abc import ABC, abstractmethod
from threading import Lock

logger = logging.getLogger()


class KeyConflict(Exception):
    def __init__(self, key, value):
        """
        Raised when performing operations on a key that is not expected to exist (e.g. create)

        :param key: The pre-existing key
        :param value: The value associated with the pre-existing key
        """
        self.key = key
        self.value = value
        super().__init__()


class ABCBackend(ABC):
    @abstractmethod
    def create(self, key, value, txn_id):
        """
        Add an item to the KV store

        :param key: Key to be added
        :param value: Value to be added
        :param txn_id: Transaction ID to be used in logs
        :return: None
        :raises KeyError: If the key to create is already present
        """
        raise NotImplementedError()

    @abstractmethod
    def replace(self, key, value, txn_id):
        """
        Replace the value associated with a key. If the key does not exist it will be created.

        :param key: The key for which value should be replaced
        :param value: The new value
        :param txn_id: Transaction ID to be used in logs
        :return: None
        :raises KeyError: If the key to replace is not present
        """
        raise NotImplementedError()

    @abstractmethod
    def delete(self, key, txn_id):
        """
        Delete a key from the store

        :param key: The key to delete
        :param txn_id: Transaction ID to be used in logs
        :return: None
        :raises KeyError: If the key to delete is not present
        """
        raise NotImplementedError()

    @abstractmethod
    def get(self, key, txn_id):
        """
        Get the value associated with a key

        :param key: The key for which to get the associated value
        :param txn_id: Transaction ID to be used in logs
        :return: Value of this key
        :raises KeyError: If the requested key is not present
        """
        raise NotImplementedError()


class InMemoryKvStore(ABCBackend):
    """
    A KV store backend using python's dictionary class to store data. The data is not persistent across restarts.
    """

    def __init__(self):
        self.kv_store = {}

    def create(self, key, value, txn_id):
        if key in self.kv_store:
            logger.info(
                f'{{"txn_id": "{txn_id}", '
                f'"key", "{key}", '
                f'"new_value": "{value}", '
                f'"old_value": "{self.kv_store[key]}", '
                f'"message": "Key conflict in create operation"}}')
            raise KeyConflict(key, self.kv_store[key])
        self.kv_store[key] = value

    def replace(self, key, value, txn_id):
        if key not in self.kv_store:
            logger.info(
                f'{{"txn_id": "{txn_id}", '
                f'"key", "{key}", '
                f'"value": "{value}", '
                f'"message": "Replace operation on key that did not exist"}}')
        self.kv_store[key] = value

    def delete(self, key, txn_id):
        self.kv_store.pop(key)

    def get(self, key, txn_id):
        return self.kv_store[key]


class LocalDiskKvStore(ABCBackend):
    """
    A KV store backend using local disk to store records. Data is persistent across restarts.

    This is a naive implementation that reads and rewrites all data on each operation. Not scalable, but  included to
    demonstrate a backend with persistent storage.
    """

    def __init__(self):
        self.filename = 'kv_file'
        if not os.path.isfile(self.filename):
            with open(self.filename, 'w') as f:
                pickle.dump({}, f)
        self.lock = Lock()

    def _safe_op(self, kv_op):
        with self.lock:
            with open(self.filename, 'r') as f:
                kv_store = kv_op(f)
            with open(self.filename, 'w') as f:
                pickle.dump(kv_store, f)

    def create(self, key, value, txn_id):
        self._safe_op(functools.partial(self._create, key, value, txn_id))

    def replace(self, key, value, txn_id):
        self._safe_op(functools.partial(self._replace, key, value, txn_id))

    def delete(self, key, txn_id):
        self._safe_op(functools.partial(self._delete, key, txn_id))

    def get(self, key, txn_id):
        self._safe_op(functools.partial(self._get, key, txn_id))

    @staticmethod
    def _create(key, value, txn_id, open_file):
        kv_store = pickle.load(open_file)
        if key in kv_store:
            raise KeyConflict(key, kv_store[key])
        kv_store[key] = value
        return kv_store

    @staticmethod
    def _replace(key, value, txn_id, open_file):
        kv_store = pickle.load(open_file)
        if key not in kv_store:
            logger.info(
                f'{{"txn_id": "{txn_id}", '
                f'"key", "{key}", '
                f'"value": "{value}", '
                f'"message": "Replace operation on key that did not exist"}}')
        kv_store[key] = value

    @staticmethod
    def _delete(key, txn_id, open_file):
        kv_store = pickle.load(open_file)
        kv_store.pop(key)

    @staticmethod
    def _get(key, txn_id, open_file):
        kv_store = pickle.load(open_file)
        return kv_store[key]
