from localdatadog import datadog, helper
# from datadog import api
import json
from asynctest import patch


def test_buildtags_basic():
    # some test data from instaclustr
    test_data = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "payload": [
                {
                    "metric": "slaConsumerRecordsProcessed",
                    "type": "count",
                    "unit": "1",
                    "values": [
                        {
                            "value": "30.0",
                            "time": "2019-09-03T00:48:05.000Z"
                        }
                    ]
                },
                {
                    "metric": "cpuUtilization",
                    "type": "percentage",
                    "unit": "1",
                    "values": [
                        {
                            "value": "1.61892901618929",
                            "time": "2019-09-03T00:48:05.000Z"
                        }
                    ]
                }
            ],
            "publicIp": "",
            "privateIp": "10.0.0.2",
            "rack": {
                "name": "ap-southeast-2a",
                "dataCentre": {
                    "name": "AP_SOUTHEAST_2",
                    "provider": "AWS_VPC",
                    "customDCName": "KAFKA_VPC_DEVELOPMENT"
                },
                "providerAccount": {
                    "name": "Lendi AWS Account",
                    "provider": "AWS_VPC"
                }
            }
        }]
    node = json.loads(json.dumps(test_data[0]))
    tag_list = helper.buildTags(node, 'test-cluster')
    assert 'ic_rack_name:ap-southeast-2a' in tag_list
    assert 'ic_data_centre_provider:AWS_VPC' in tag_list
    assert 'ic_provider_account_provider:AWS_VPC' in tag_list
    assert 'ic_data_centre_name:AP_SOUTHEAST_2' in tag_list
    assert 'ic_cluster_id:test-cluster' in tag_list


async def test_shipToDataDog_basic(capfd):
    with patch('datadog.api.Metric.send') as mocked_get:
        response = await datadog.shipToDataDog('yes', 'on')
        assert mocked_get.call_count == 0  # ship method isn't called
        assert response is None

        # Simple metrics test - No payload DD Response != 'ok
        metrics = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "payload": [],
                "publicIp": "",
                "privateIp": "10.0.0.2",
                "rack": {
                    "name": "ap-southeast-2a",
                    "dataCentre": {
                        "name": "AP_SOUTHEAST_2",
                        "provider": "AWS_VPC",
                        "customDCName": "KAFKA_VPC_DEVELOPMENT"
                    },
                    "providerAccount": {
                        "name": "Lendi AWS Account",
                        "provider": "AWS_VPC"
                    }
                }
            }]
        response = await datadog.shipToDataDog('my_test_cluster', 'on', ic_tags=[], metrics=metrics)
        captured = capfd.readouterr()
        assert mocked_get.call_count == 0  # ship method isn't called
        assert 'Empty list from the instaclustr API for the cluster: my_test_cluster' in captured.out

        # Simple metrics test - DD Response != 'ok
        mocked_get.return_value = {
            "status": 'Not_OK'
        }
        metrics = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "payload": [
                    {
                        "metric": "slaConsumerRecordsProcessed",
                        "type": "count",
                        "unit": "1",
                        "values": [
                            {
                                "value": "30.0",
                                "time": "2019-09-03T00:48:05.000Z"
                            }
                        ]
                    },
                    {
                        "metric": "cpuUtilization",
                        "type": "percentage",
                        "unit": "1",
                        "values": [
                            {
                                "value": "1.61892901618929",
                                "time": "2019-09-03T00:48:05.000Z"
                            }
                        ]
                    }
                ],
                "publicIp": "",
                "privateIp": "10.0.0.2",
                "rack": {
                    "name": "ap-southeast-2a",
                    "dataCentre": {
                        "name": "AP_SOUTHEAST_2",
                        "provider": "AWS_VPC",
                        "customDCName": "KAFKA_VPC_DEVELOPMENT"
                    },
                    "providerAccount": {
                        "name": "Lendi AWS Account",
                        "provider": "AWS_VPC"
                    }
                }
            }]
        response = await datadog.shipToDataDog('yes', 'on', ic_tags=[], metrics=metrics)
        captured = capfd.readouterr()
        assert mocked_get.call_count == 1
        assert 'Error sending metrics to DataDog: ' in captured.out
        assert response is None


async def test_shipToDataDog_complex(capfd):
    with patch('datadog.api.Metric.send') as mocked_get:
        # Simple metrics test - DD Response == 'ok
        metrics = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "payload": [
                    {
                        "metric": "slaConsumerRecordsProcessed",
                        "type": "count",
                        "unit": "1",
                        "values": [
                            {
                                "value": "30.0",
                                "time": "2019-09-03T00:48:05.000Z"
                            }
                        ]
                    },
                    {
                        "metric": "cpuUtilization",
                        "type": "percentage",
                        "unit": "1",
                        "values": [
                            {
                                "value": "1.61892901618929",
                                "time": "2019-09-03T00:48:05.000Z"
                            }
                        ]
                    }
                ],
                "publicIp": "",
                "privateIp": "10.0.0.2",
                "rack": {
                    "name": "ap-southeast-2a",
                    "dataCentre": {
                        "name": "AP_SOUTHEAST_2",
                        "provider": "AWS_VPC",
                        "customDCName": "KAFKA_VPC_DEVELOPMENT"
                    },
                    "providerAccount": {
                        "name": "Lendi AWS Account",
                        "provider": "AWS_VPC"
                    }
                }
            }]
        mocked_get.return_value = {
            "status": 'ok'
        }

        response = await datadog.shipToDataDog('yes', 'on', ic_tags=[], metrics=metrics)
        assert mocked_get.call_count == 1
        assert response == 'ok'

        # Throw exception from the api.Metric.send method
        mocked_get.side_effect = Exception('api.Metric.send failed to send to DD')
        response = await datadog.shipToDataDog('yes', 'on', ic_tags=[], metrics=metrics)
        captured = capfd.readouterr()
        assert mocked_get.call_count == 2
        assert 'Could not send metrics to DataDog' in captured.out
