import logging

from flask import Flask, request
from unittest import TextTestRunner, TestSuite
from io import StringIO
from test import DeleteTests, ReplaceTests, ParametrizedTestCase

REQUEST_SCHEMA = {
        'type': 'object',
        'properties': {
            'baseurl': {"type": ["string"]},
        },
        'additionalProperties': False
    }

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8081

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask("kv_test_service")


@app.post("/test_deletion")
def test_deletion():
    return _run_tests(DeleteTests)


@app.post("/test_overwrite")
def test_overwrite():
    return _run_tests(ReplaceTests)


def _run_tests(test_class):
    baseurl = request.get_json()['baseurl']
    logger.info(f"KV Service is at {baseurl}")

    stream = StringIO()
    runner = TextTestRunner(verbosity=2, stream=stream)
    suite = TestSuite()
    suite.addTest(ParametrizedTestCase.parametrize(test_class, baseurl=baseurl))
    result = runner.run(suite)
    stream.seek(0)
    return (
        "#######\ntestsRun: {}\n#######\nerrors: {}\n#######\noutput:\n{}\n#######\n".format(
            result.testsRun, result.errors, stream.read()),
        200,
        {"Content-Type": "text/plain"})


if __name__ == "__main__":
    app.run(DEFAULT_HOST, DEFAULT_PORT)
