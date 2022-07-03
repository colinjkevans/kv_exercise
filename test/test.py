import unittest
import requests
import logging

DEFAULT_BASE_URL = "http://localhost:8080"
PATH = "/api/v1/kv/{}"
KV_SERVICE_URL = DEFAULT_BASE_URL + PATH
TEST_KEY = 'foo'
TEST_VALUE = 'bar'
TEST_REPLACE_VALUE = 'baz'
PUT_TEST_JSON = {"value": TEST_VALUE}
PUT_REPLACE_JSON = {"value": TEST_REPLACE_VALUE}
PUT_NULL_JSON = {"value": None}

logger = logging.getLogger(__name__)


def clear_key(baseurl):
    r = requests.delete(baseurl + PATH.format(TEST_KEY))
    assert r.status_code in [200, 404]


def set_key(baseurl):
    r = requests.put(baseurl + PATH.format(TEST_KEY), json=PUT_TEST_JSON)
    assert r.status_code in [200, 201]


class ParametrizedTestCase(unittest.TestCase):
    """
    TestCase classes that want to be parametrized should inherit from this class.
    """
    def __init__(self, methodName='runTest', baseurl=DEFAULT_BASE_URL):
        super(ParametrizedTestCase, self).__init__(methodName)
        self.baseurl = baseurl

    @staticmethod
    def parametrize(testcase_class, baseurl=None):
        """
        Create a suite containing all tests taken from the given
        subclass, passing them the parameter 'baseurl'.
        """
        testloader = unittest.TestLoader()
        testnames = testloader.getTestCaseNames(testcase_class)
        suite = unittest.TestSuite()
        for name in testnames:
            suite.addTest(testcase_class(name, baseurl=baseurl))
        return suite


class GeneralTests(unittest.TestCase):

    def test_not_found(self):
        r = requests.get(DEFAULT_BASE_URL + "/foo")
        self.assertEqual(404, r.status_code)

    def test_numerical_key(self):
        url = DEFAULT_BASE_URL + PATH.format(123)
        r = requests.post(url, json={"value": 456})
        r = requests.get(url)
        self.assertEqual(200, r.status_code)


class DeleteTests(ParametrizedTestCase):

    def test_delete(self):

        url = self.baseurl + PATH.format(TEST_KEY)
        logger.info(f"Resource URL: {url}")

        # Ensure key to delete is present
        set_key(self.baseurl)

        # Test key deletion
        r = requests.delete(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(1000, r.json()['status'])

        # Ensure key is not present
        r = requests.get(url)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(3001, r.json()['status'])

    def test_delete_not_present(self):
        # Ensure key to delete is not present
        clear_key(self.baseurl)
        r = requests.delete(self.baseurl + PATH.format(TEST_KEY))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()['status'], 3001)


class ReplaceTests(ParametrizedTestCase):

    def test_replace_empty_key(self):
        clear_key(self.baseurl)
        r = requests.put(self.baseurl + PATH.format(TEST_KEY), json=PUT_TEST_JSON)
        self.assertEqual(201, r.status_code)
        self.assertEqual(r.json()['status'], 1000)

        g = requests.get(self.baseurl + PATH.format(TEST_KEY))
        self.assertEqual(g.status_code, 200)
        self.assertEqual(g.json()['value'], TEST_VALUE)

    def test_replace_existing_key(self):
        set_key(self.baseurl)
        r = requests.put(self.baseurl + PATH.format(TEST_KEY), json=PUT_REPLACE_JSON)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 1000)

        g = requests.get(self.baseurl + PATH.format(TEST_KEY))
        self.assertEqual(g.status_code, 200)
        self.assertEqual(g.json()['value'], TEST_REPLACE_VALUE)

    def test_replace_with_same_value(self):
        set_key(self.baseurl)
        r = requests.put(self.baseurl + PATH.format(TEST_KEY), json=PUT_TEST_JSON)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 1000)

    def test_replace_with_null(self):
        set_key(self.baseurl)
        r = requests.put(self.baseurl + PATH.format(TEST_KEY), json=PUT_NULL_JSON)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()['status'], 3005)


if __name__ == '__main__':
    unittest.main()
