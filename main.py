from flask import Flask, request, Response, jsonify
from werkzeug.exceptions import BadRequest
from jsonschema import validate, ValidationError
from backends import InMemoryKvStore, LocalDiskKvStore, KeyConflict
import logging
from uuid import uuid4

REQUEST_SCHEMA = {
        'type': 'object',
        'properties': {
            'value': {"type": ["string", "number", "boolean", "null"]},
        },
        'additionalProperties': False
    }

RETURN_SCHEMA = {
        'type': 'object',
        'required': ['status'],
        'properties': {
            'value': {"type": ["string", "number", "boolean", "null"]},
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

# TODO make this an arg
backend_type = 'in_memory'

app = Flask("kv_store")
logging.basicConfig()
logger = logging.getLogger(__name__)

DEFAULT_PORT = 8080
DEFAULT_HOST = '127.0.0.1'  # '::' for IPv6


@app.route("/kv/{key}", methods=['GET', 'POST', 'PUT', 'DELETE'])
def kv_operation(key):
    txn_id = uuid4()
    logger.info(f'{"txn_id": "{txn_id}", "verb": "{request.method}", "key", "{key}", "src": "{request.remote_addr}" }')

    if request.method == 'GET':
        value = backend.get(key, txn_id)
        return _build_response(200, key, value, 1000)

    elif request.method == 'POST':
        body = request.get_json()
        validate(body, REQUEST_SCHEMA)
        value = body['value']
        backend.create(key, value, txn_id)
        return _build_response(201, key, value, NO_ERROR, {'Location': request.base_url})

    elif request.method == 'PUT':
        body = request.get_json()
        validate(body, REQUEST_SCHEMA)
        value = body['value']
        status = backend.replace(key, value, txn_id)
        return _build_response(status, key, value, NO_ERROR, {'Location': request.base_url})

    elif request.method == 'DELETE':
        backend.delete(key, txn_id)
        _build_response(200, key, api_status=NO_ERROR)


@app.errorhandler(BadRequest)
def handle_non_json_request(e):
    return _build_response(400, api_status=FAILED_TO_PARSE_REQUEST_BODY, error="JSON parsing error")


@app.errorhandler(ValidationError)
def handle_bad_json_request(e):
    return _build_response(400, api_status=FAILED_TO_VALIDATE_REQUEST_BODY, error=str(e))


@app.errorhandler(KeyConflict)
def handle_key_conflict(e):
    return _build_response(409, api_status=CREATE_KEY_ALREADY_PRESENT, error=str(e))


@app.errorhandler(KeyError)
def handle_key_missing(e):
    return _build_response(404, api_status=KEY_NOT_PRESENT, error=str(e))


def _build_response(http_status, key=None, value=None, api_status=None, error=None, headers=None):
    response = Response()
    response.status = http_status
    body = {}
    if key is not None:
        body['key'] = key
    if value is not None:
        body['value'] = value
    if api_status is not None:
        body['status'] = api_status
    if error is not None:
        body['error'] = error
    response.set_data(jsonify(body))
    response.content_type = 'application/json'
    response.headers += headers
    return response


if __name__ == '__main__':
    # TODO get IP, ports etc.
    backend = BACKENDS[backend_type]()
    app.run()
