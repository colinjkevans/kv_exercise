import functools
import logging
import pickle
import os.path
from abc import ABC, abstractmethod
from threading import Lock
from flask import g

logger = logging.getLogger(__name__)


class KeyConflict(Exception):
    def __init__(self, key, old_value, new_value):
        """
        Raised when performing operations on a key that is not expected to exist (e.g. create)

        :param key: The pre-existing key
        :param old_value: The value associated with the pre-existing key
        :param new_value: New value attempted to assign the key
        """
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        super().__init__()

    def __str__(self):
        return f'Key: {self.key}, Existing value: {self.old_value}, Supplied value: {self.new_value}'


class ABCBackend(ABC):
    @abstractmethod
    def create(self, key, value):
        """
        Add an item to the KV store

        :param key: Key to be added
        :param value: Value to be added
        :return: None
        :raises KeyError: If the key to create is already present
        """
        raise NotImplementedError()

    @abstractmethod
    def replace(self, key, value):
        """
        Replace the value associated with a key. If the key does not exist it will be created.

        :param key: The key for which value should be replaced
        :param value: The new value
        :return: The previous value of the key, or None if key wasn't present
        :raises KeyError: If the key to replace is not present
        """
        raise NotImplementedError()

    @abstractmethod
    def delete(self, key):
        """
        Delete a key from the store

        :param key: The key to delete
        :return: The value deleted
        :raises KeyError: If the key to delete is not present
        """
        raise NotImplementedError()

    @abstractmethod
    def get(self, key):
        """
        Get the value associated with a key

        :param key: The key for which to get the associated value
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
        super().__init__()

    def create(self, key, value):
        if key in self.kv_store:
            logger.info(
                f'{{"txn_id": "{g.txn_id}", '
                f'"key", "{key}", '
                f'"new_value": "{value}", '
                f'"old_value": "{self.kv_store[key]}", '
                f'"message": "Key conflict in create operation"}}')
            raise KeyConflict(key, self.kv_store[key], value)
        self.kv_store[key] = value

    def replace(self, key, value):
        if key not in self.kv_store:
            logger.info(
                f'{{"txn_id": "{g.txn_id}", '
                f'"key", "{key}", '
                f'"value": "{value}", '
                f'"message": "Replace operation on key that did not exist"}}')
            old_value = None
        else:
            old_value = self.kv_store[key]
        self.kv_store[key] = value
        return old_value

    def delete(self, key):
        return self.kv_store.pop(key)

    def get(self, key):
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
            logger.info('Creating new kv_store file')
            with open(self.filename, 'wb') as f:
                pickle.dump({}, f)
        else:
            logger.info("Found existing kv_store file")
        self.lock = Lock()
        super().__init__()

    def _safe_op(self, kv_op):
        with self.lock:
            with open(self.filename, 'rb') as f:
                kv_store, value = kv_op(f)
            with open(self.filename, 'wb') as f:
                pickle.dump(kv_store, f)
        return value

    def create(self, key, value):
        self._safe_op(functools.partial(self._create, key, value))

    def replace(self, key, value):
        return self._safe_op(functools.partial(self._replace, key, value))

    def delete(self, key):
        return self._safe_op(functools.partial(self._delete, key))

    def get(self, key):
        return self._safe_op(functools.partial(self._get, key))

    @staticmethod
    def _create(key, value, open_file):
        kv_store = pickle.load(open_file)
        if key in kv_store:
            raise KeyConflict(key, kv_store[key])
        kv_store[key] = value
        return kv_store, value

    @staticmethod
    def _replace(key, value, open_file):
        kv_store = pickle.load(open_file)
        if key not in kv_store:
            logger.info(
                f'{{"txn_id": "{g.txn_id}", '
                f'"key", "{key}", '
                f'"value": "{value}", '
                f'"message": "Replace operation on key that did not exist"}}')
            old_value = None
        else:
            old_value = kv_store[key]
        kv_store[key] = value
        return kv_store, old_value

    @staticmethod
    def _delete(key, open_file):
        kv_store = pickle.load(open_file)
        value = kv_store.pop(key)
        return kv_store, value

    @staticmethod
    def _get(key, open_file):
        kv_store = pickle.load(open_file)
        return kv_store, kv_store[key]
