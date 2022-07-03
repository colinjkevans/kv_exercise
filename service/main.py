import os
import sys
import logging

from flask import Flask, request, g
from werkzeug.exceptions import BadRequest
from jsonschema import validate, ValidationError
from backends import InMemoryKvStore, LocalDiskKvStore, KeyConflict
from uuid import uuid4

REQUEST_SCHEMA = {
        'type': 'object',
        'properties': {
            'value': {"type": ["string", "number", "boolean"]},
        },
        'additionalProperties': False
    }

RETURN_SCHEMA = {
        'type': 'object',
        'required': ['status'],
        'properties': {
            'value': {
                "type": ["string", "number", "boolean", "null"],
                "description": "The value associated with the key after this transaction"},
            'status': {"type": "number"},
            'error': {"type": "string"}
        },
        'additionalProperties': False
    }

NO_ERROR = 1000
KEY_NOT_PRESENT = 3001
CREATE_KEY_ALREADY_PRESENT = 3003
FAILED_TO_PARSE_REQUEST_BODY = 3004
FAILED_TO_VALIDATE_REQUEST_BODY = 3005

BACKENDS = {
    'in_memory': InMemoryKvStore,
    'local_disk': LocalDiskKvStore}

DEFAULT_BACKEND_TYPE = 'local_disk'
backend = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PORT = 8080
DEFAULT_HOST = '127.0.0.1'


def create_app(backend_type=DEFAULT_BACKEND_TYPE):
    app = Flask("kv_store")
    app.config['backend'] = BACKENDS[backend_type]()

    @app.route("/api/v1//kv/<key>", methods=['GET', 'POST', 'PUT', 'DELETE'])
    def kv_operation(key):
        g.txn_id = uuid4()
        g.key = key
        g.api_status = NO_ERROR
        logger.info(
            f'{{"txn_id": "{g.txn_id}", "verb": "{request.method}", "key", "{key}", "src": "{request.remote_addr}" }}')

        if request.method == 'GET':
            g.action = "get"
            value = app.config['backend'].get(key)
            g.value = value
            return _build_response(200, key, value, g.api_status)

        elif request.method == 'POST':
            g.action = "create"
            value = _read_request_value()
            app.config['backend'].create(key, value)
            g.value = value
            return _build_response(
                201, key=key, value=value, api_status=g.api_status, headers={'Location': request.base_url})

        elif request.method == 'PUT':
            g.action = "replace"
            value = _read_request_value()
            old_value = app.config['backend'].replace(key, value)
            status = 201 if old_value is None else 200
            g.value = value
            return _build_response(
                status, key=key, value=value, api_status=g.api_status, headers={'Location': request.base_url})

        elif request.method == 'DELETE':
            g.action = "delete"
            old_value = app.config['backend'].delete(key)
            g.value = None
            return _build_response(200, key=key, api_status=g.api_status)

    @app.errorhandler(BadRequest)
    def handle_non_json_request(e):
        g.api_status = FAILED_TO_PARSE_REQUEST_BODY
        g.error_message = str(e)
        return _build_response(400, api_status=g.api_status, error=str(e))

    @app.errorhandler(ValidationError)
    def handle_bad_json_request(e):
        g.api_status = FAILED_TO_VALIDATE_REQUEST_BODY
        g.error_message = str(e)
        return _build_response(400, api_status=g.api_status, error=str(e))

    @app.errorhandler(KeyConflict)
    def handle_key_conflict(e):
        g.api_status = CREATE_KEY_ALREADY_PRESENT
        g.error_message = str(e)
        return _build_response(409, api_status=g.api_status, error=str(e))

    @app.errorhandler(KeyError)
    def handle_key_missing(e):
        g.api_status = KEY_NOT_PRESENT
        g.error_message = str(e)
        return _build_response(404, api_status=g.api_status, error=str(e))

    @app.after_request
    def _log_result(response):
        if 'txn_id' not in g:
            return response

        txn_id = g.get('txn_id', None)
        action = g.get('action', None)
        key = g.get('key', None)
        value = g.get('value', None)
        api_status = g.get('api_status', None)
        error_message = g.get('error_message', None)
        if response.status.startswith('2'):
            logger.info(
                f'{{"txn_id": "{txn_id}", '
                f'"action": {action}, '
                f'"key": {key}, '
                f'"value": {value}, '
                f'"status": {api_status}}}')
        else:
            logger.info(
                f'{{"txn_id": "{txn_id}", '
                f'"action": {action}, '
                f'"key": {key}, '
                f'"status": {api_status}, '
                f'"error": {error_message}}}')
        return response

    return app


def _read_request_value():
    body = request.get_json()
    validate(body, REQUEST_SCHEMA)
    return body['value']


def _build_response(http_status, key=None, value=None, api_status=None, error=None, headers=None):
    body = {}
    if key is not None:
        body['key'] = key
    if value is not None:
        body['value'] = value
    if api_status is not None:
        body['status'] = api_status
    if error is not None:
        body['error'] = error
    return body, http_status, headers


if __name__ == '__main__':

    try:
        ip = sys.argv[1]
        port = sys.argv[2]
        kv_backend_type = sys.argv[3]
    except IndexError:
        # IP/port not supplied, look for environment variables or set default
        ip = os.environ.get("KV_SERVICE_IP", DEFAULT_HOST)
        port = os.environ.get("KV_SERVICE_PORT", DEFAULT_PORT)
        kv_backend_type = os.environ.get("KV_SERVICE_BACKEND", DEFAULT_BACKEND_TYPE)

    kv_app = create_app(backend_type=kv_backend_type)
    logger.info(f'Backend is {kv_backend_type}')

    kv_app.run(ip, port)
