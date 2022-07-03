## API

All `PUT`/`POST` requests must have `Content-type: application/json` header.

kv-service takes the following requests to endpoint `/api/v1/kv/{key}`:
- `GET` - get the value associated with `{key}`
  - returns
    - 200 with json body `{"key": {key}, "value": {value}, "status": 1000 }`
    - 404 if `{key}` is not present
- `POST` - creates a key at `{key}` with value specified in `{value}` json property
  - includes body matching `REQUEST_SCHEMA` in `service/main.py`
  - returns
    - Successful request: 201 with json body `{ "key": {key}, "value": {value} "status": 1000}`
    - If the key already exists: 409 with json body `{ "error": {error message}, "status": 3003 }`
- `PUT` - creates or replaces a key at `{key}` with value specified in `{value}` json property
  - includes body matching `REQUEST_SCHEMA` in `service/main.py`
  - returns
    - Successful request with new key: 201 with json body `{ "key": {key}, "value": {value} "status": 1000}`
    - Successful request replacing key: 200 with json body `{ "key": {key}, "value": {value} "status": 1000}`
- `DELETE` removes the key and value at `{key}`
  - returns
    - 200 with json body `{"key": {key}, "status": 1000 }`
    - 404 if `{key}` is not present

kv-test-service takes a `POST` request with body matching `REQUEST_SCHEMA` in `test/test_service.py`, specifying the
host/port where the kv-service can be found. Returns a plain text response containing the output of tests in 
`test/test.py`

## Dev Usage
Bother services can be run on the flask dev server (werkzeug) from the cli as follows:

#### KV Service
`python main.py [host port backend]`

host, port and backend must all be supplied on the CLI or none. If none are supplied environment variables can be used to
override defaults.
- `KV_SERVICE_IP` : default 127.0.0.1
- `KV_SERVICE_PORT` : default 8080
- `KV_SERVICE_BACKEND` : default `in_memory`
  - backend can be "in_memory" or "local_disk"

#### Test Service
`python test_service.py`
IP/PORT selections are not implemented. The service as run from the cli in werkzeug runs on localhost:8081


####
Apps can also be run with a wsgi server, such as gunicorn. See Dockerfiles for example commands.


## Docker
To run both services in docker on the same host

#### KV Service
```
cd service
sudo docker build -t 'kv-service' .
sudo docker run -d -p 8080:8080 --name kv-service kv-service
```

#### Test Service
```
cd test
sudo docker build -t 'kv-test-service' .
sudo docker run -d -p 8080:8080 --link kv-service --name kv-service kv-service
```

Requests to the test service can be run with:
```
curl \
    -X POST \
    -H 'Content-Type: application/json' \ 
    -d '{"baseurl": "http://kv-service:8080"}' \ 
    http://localhost:8081/test_overwrite
```

```
curl \
    -X POST \
    -H 'Content-Type: application/json' \ 
    -d '{"baseurl": "http://kv-service:8080"}' \ 
    http://localhost:8081/test_deletion
```

## Notes on "quickly change the transport layer protocol"
This requirement in the spec had be scratching my head a bit - it sounds like running a REST service over UDP rather
than TCP. That seems to be
- a non-trivial undertaking, since typical HTTP servers don't offer it as a configuration
option.
- somewhat contrary to the HTTP spec, which says HTTP should use a reliable transport.
- not the responsibility of the application, but of the server handling the application.

With that in mind, my only suggestion for meeting this requirement is to swap in a server that supports HTTP/3, which 
uses UDP for its transport layer. This is not implemented, but wrapping the flask wsgi app as asgi
(e.g. using `asgiref.wsgi.WsgiToAsgi`), and running in the `hypercorn` server ought to allow the service to be run over
a different transport layer protocol.

