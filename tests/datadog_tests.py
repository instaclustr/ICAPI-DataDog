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

        # Simple metrics test - Payload empty from Instaclustr.
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

        # Simple metrics test - DD Response != 'ok'
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
        mocked_get.assert_called_once_with(
            [
                {
                    "metric": "on.slaConsumerRecordsProcessed.count",
                    "points": [
                        (
                            1567471685,
                            30.0
                        )
                    ],
                    "tags": [
                        "ic_node_id:00000000-0000-0000-0000-000000000001",
                        "ic_cluster_id:yes",
                        "ic_private_ip:10.0.0.2",
                        "ic_rack_name:ap-southeast-2a",
                        "ic_data_centre_custom_name:KAFKA_VPC_DEVELOPMENT",
                        "ic_data_centre_name:AP_SOUTHEAST_2",
                        "ic_data_centre_provider:AWS_VPC",
                        "ic_provider_account_name:Lendi AWS Account",
                        "ic_provider_account_provider:AWS_VPC",
                        "region:ap-southeast-2",
                        "availability_zone:ap-southeast-2a"
                    ]
                },
                {
                    "metric": "on.cpuUtilization.percentage",
                    "points": [
                        (
                            1567471685,
                            1.61892901618929
                        )
                    ],
                    "tags": [
                        "ic_node_id:00000000-0000-0000-0000-000000000001",
                        "ic_cluster_id:yes",
                        "ic_private_ip:10.0.0.2",
                        "ic_rack_name:ap-southeast-2a",
                        "ic_data_centre_custom_name:KAFKA_VPC_DEVELOPMENT",
                        "ic_data_centre_name:AP_SOUTHEAST_2",
                        "ic_data_centre_provider:AWS_VPC",
                        "ic_provider_account_name:Lendi AWS Account",
                        "ic_provider_account_provider:AWS_VPC",
                        "region:ap-southeast-2",
                        "availability_zone:ap-southeast-2a"
                    ]
                }
            ])
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
        mocked_get.assert_called_once_with(
            [
                {
                    "metric": "on.slaConsumerRecordsProcessed.count",
                    "points": [
                        (
                            1567471685,
                            30.0
                        )
                    ],
                    "tags": [
                        "ic_node_id:00000000-0000-0000-0000-000000000001",
                        "ic_cluster_id:yes",
                        "ic_private_ip:10.0.0.2",
                        "ic_rack_name:ap-southeast-2a",
                        "ic_data_centre_custom_name:KAFKA_VPC_DEVELOPMENT",
                        "ic_data_centre_name:AP_SOUTHEAST_2",
                        "ic_data_centre_provider:AWS_VPC",
                        "ic_provider_account_name:Lendi AWS Account",
                        "ic_provider_account_provider:AWS_VPC",
                        "region:ap-southeast-2",
                        "availability_zone:ap-southeast-2a"
                    ]
                },
                {
                    "metric": "on.cpuUtilization.percentage",
                    "points": [
                        (
                            1567471685,
                            1.61892901618929
                        )
                    ],
                    "tags": [
                        "ic_node_id:00000000-0000-0000-0000-000000000001",
                        "ic_cluster_id:yes",
                        "ic_private_ip:10.0.0.2",
                        "ic_rack_name:ap-southeast-2a",
                        "ic_data_centre_custom_name:KAFKA_VPC_DEVELOPMENT",
                        "ic_data_centre_name:AP_SOUTHEAST_2",
                        "ic_data_centre_provider:AWS_VPC",
                        "ic_provider_account_name:Lendi AWS Account",
                        "ic_provider_account_provider:AWS_VPC",
                        "region:ap-southeast-2",
                        "availability_zone:ap-southeast-2a"
                    ]
                }
            ])
        assert response == 'ok'

        # Throw exception from the api.Metric.send method
        mocked_get.side_effect = Exception('api.Metric.send failed to send to DD')
        response = await datadog.shipToDataDog('yes', 'on', ic_tags=[], metrics=metrics)
        captured = capfd.readouterr()
        assert mocked_get.call_count == 2
        assert 'Could not send metrics to DataDog' in captured.out


async def test_shipToDataDog_topics(capfd):
    with patch('datadog.api.Metric.send') as mocked_get:
        # Simple metrics test - DD Response == 'ok
        metrics = [
            {
                "consumerGroup": "group-20",
                "topic": "test1",
                "clientID": "client-2",
                "payload": [
                    {
                        "metric": "consumerLag",
                        "type": "count",
                        "unit": "messages",
                        "values": [
                            {
                                "value": "30.0",
                                "time": "2019-09-17T11:38:59.000Z"
                            }
                        ]
                    },
                    {
                        "metric": "consumerCount",
                        "type": "count",
                        "unit": "consumers",
                        "values": [
                            {
                                "value": "1.0",
                                "time": "2019-09-17T11:38:59.000Z"
                            }
                        ]
                    }
                ]
            }
        ]
        mocked_get.return_value = {
            "status": 'ok'
        }

        response = await datadog.shipToDataDog('yes', 'on', ic_tags=[], metrics=metrics)
        mocked_get.assert_called_once_with(
            [
                {
                    "metric": "on.consumerLag.count",
                    "points": [
                        (
                            1568720339,
                            30.0
                        )
                    ],
                    "tags": [
                        "ic_cluster_id:yes",
                        "topic:test1",
                        "consumerGroup:group-20",
                        "clientID:client-2"
                    ]
                },
                {
                    "metric": "on.consumerCount.count",
                    "points": [
                        (
                            1568720339,
                            1.0
                        )
                    ],
                    "tags": [
                        "ic_cluster_id:yes",
                        "topic:test1",
                        "consumerGroup:group-20",
                        "clientID:client-2"
                    ]
                }
            ]
        )
        assert response == 'ok'

        mocked_get.reset_mock()
        metrics = [
            {
                "consumerGroup": "group-20",
                "topic": "test1",
                "payload": [
                    {
                        "metric": "consumerGroupLag",
                        "type": "count",
                        "unit": "messages",
                        "values": [
                            {
                                "value": "30.0",
                                "time": "2019-09-17T11:52:45.000Z"
                            }
                        ]
                    },
                    {
                        "metric": "clientCount",
                        "type": "count",
                        "unit": "clients",
                        "values": [
                            {
                                "value": "1.0",
                                "time": "2019-09-17T11:52:45.000Z"
                            }
                        ]
                    }
                ]
            }
        ]
        response = await datadog.shipToDataDog('yes', 'on', ic_tags=[], metrics=metrics)
        mocked_get.assert_called_once_with(
            [
                {
                    "metric": "on.consumerGroupLag.count",
                    "points": [
                        (
                            1568721165,
                            30.0
                        )
                    ],
                    "tags": [
                        "ic_cluster_id:yes",
                        "topic:test1",
                        "consumerGroup:group-20"
                    ]
                },
                {
                    "metric": "on.clientCount.count",
                    "points": [
                        (
                            1568721165,
                            1.0
                        )
                    ],
                    "tags": [
                        "ic_cluster_id:yes",
                        "topic:test1",
                        "consumerGroup:group-20"
                    ]
                }
            ]
        )
