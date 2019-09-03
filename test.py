import unittest, json, sys, os, requests, responses
from unittest.mock import Mock, patch
from ic2datadog import getInstaclustrMetrics, shipToDataDog, buildTags, main
from datadog import initialize, api

def mocked_datadog_send_ok(*args, **kwargs):
    return {"status": "ok"}

def mocked_datadog_send_failed(*args, **kwargs):
    return {"status": "failed"}

class Test(unittest.TestCase):

    @responses.activate
    def test_icgetmetricswithdata(self,):
        responses.add(responses.GET, 'https://instaclustr.com/200',
                  json={'nodata': 'found'}, status=200)
        a = getInstaclustrMetrics(target='https://instaclustr.com/200', dump=True)
        self.assertTrue(a.ok)

    @responses.activate
    def test_icgetmetricsnodata(self,):
        responses.add(responses.GET, 'https://instaclustr.com/200',
                  json={'dontwrite': 'anydata'}, status=200)
        a = getInstaclustrMetrics(target='https://instaclustr.com/200')
        self.assertTrue(a.ok)

    @responses.activate
    def test_icunauthorized(self):
        responses.add(responses.GET, 'https://instaclustr.com/401',
                  json={'unauthorized': 'noaccess'}, status=401)
        a = getInstaclustrMetrics(target='https://instaclustr.com/401')
        self.assertTrue(a.status_code == 401)

    def test_buildtags(self):
        # Prefer to read the data from the repo than code it into the test.
        node = []
        with open("./test-data/instaclustr-metrics.json") as file:
           data = file.read()
           node = json.loads(data)[0]
        tag_list = buildTags(node)
        self.assertIn('ic_rack_name:ap-southeast-2a', tag_list)
        self.assertIn('ic_data_centre_provider:AWS_VPC', tag_list)
        self.assertIn('ic_provider_account_provider:AWS_VPC', tag_list)
        self.assertIn('ic_data_centre_name:AP_SOUTHEAST_2', tag_list)

    @patch('datadog.api.Metric.send', side_effect=mocked_datadog_send_ok)
    def test_shiptodatadog(self, mock_send):
        metrics = []
        with open("./test-data/instaclustr-metrics.json") as file:
           data = file.read()
           metrics = json.loads(data)
        shipToDataDog(metrics)
        mock_send.assert_called()

    @patch('datadog.api.Metric.send', side_effect=mocked_datadog_send_failed)
    def test_fail_send_datadog(self, mock_send):
        metrics = []
        with open("./test-data/instaclustr-metrics.json") as file:
           data = file.read()
           metrics = json.loads(data)

        shipToDataDog(metrics)
        mock_send.assert_called()

    @patch('datadog.api.Metric.send', side_effect=mocked_datadog_send_ok)
    def test_empty_node_list(self, mock_send):
        metrics = []
        with open("./test-data/instaclustr-nometrics.json") as file:
           data = file.read()
           metrics = json.loads(data)
        shipToDataDog(metrics)
        mock_send.assert_not_called()

    # def test_main(self):
    #     with patch.object(sys, 'argv', ['prog', '--once']):
    #         main()


if __name__ == '__main__':
    unittest.main()
