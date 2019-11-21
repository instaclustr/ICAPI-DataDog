from instaclustr import instaclustr, helper
import pytest, re, json
from asynctest import patch, MagicMock


def test_splitMetricsList_one():
    array = ['one']
    output = helper.splitMetricsList(array, 1)
    for item in output:
        assert item[0] in array


def test_splitMetricsList_four():
    array = ['one', 'two', 'three', 'four']
    output = helper.splitMetricsList(array, 1)
    for item in output:
        assert item[0] in array


def test_splitMetricsList_bad():
    array = ['five', 'two', 'three', 'four']
    output = helper.splitMetricsList(array, 1)
    for item in output:
        assert item[0] in array
        assert item[0] != 'one'


# Two helper functions below to return an async response for mocking.
async def async_magic(input):
    return input


async def async_response(input):
    return await async_magic(input)


async def test_getInstaclustrMetrics_basic():
    with patch('aiohttp.ClientSession.get') as mocked_get:
        ## Successful invocation of Instaclustr API
        mocked_get.return_value.__aenter__.side_effect = [
            MagicMock(status=200, headers={'Content-Type': "application/json"}, text=(lambda: async_response(['hello'])))
        ]
        response = await instaclustr.getInstaclustrMetrics(
            'dummy_cluster_id', ['list', 'of', 'metrics'],
            {"ic_user_name": 'user', "ic_api_key": 'key'})
        mocked_get.assert_called_once()
        assert response == ['hello']

        ## Bad auth object passed in
        with pytest.raises(Exception) as e:
            response = await instaclustr.getInstaclustrMetrics('dummy_cluster_id', {"name": 'user', "password": 'key'})
        mocked_get.assert_called_once()  # Call count remains the same for mock object
        assert 'None is not allowed as login value' in str(e.value)


async def test_getInstaclustrMetrics_bad_requests(capfd):
    with patch('aiohttp.ClientSession.get') as mocked_get:
        ## Bad request - HTTP Status code
        code, content_type = 400, 'application/json'
        mocked_get.return_value.__aenter__.side_effect = [
            MagicMock(status=code, headers={'Content-Type': content_type})
        ]
        response = await instaclustr.getInstaclustrMetrics(
            'dummy_cluster_id', ['list', 'of', 'metrics'],
            {"ic_user_name": 'user', "ic_api_key": 'key'})
        captured = capfd.readouterr()
        assert mocked_get.call_count == 1  # Call count increments for mock object
        assert response is None
        assert 'Missing metrics data from instaclustr - HTTP response code: {0}; HTTP Header Content-Type: {1}'.format(code, content_type) in captured.out

        ## Bad request - Content-Type
        code, content_type = 200, 'text/html'
        mocked_get.return_value.__aenter__.side_effect = [
            MagicMock(status=code, headers={'Content-Type': content_type})
        ]
        response = await instaclustr.getInstaclustrMetrics(
            'dummy_cluster_id', ['list', 'of', 'metrics'],
            {"ic_user_name": 'user', "ic_api_key": 'key'})
        captured = capfd.readouterr()
        assert mocked_get.call_count == 2  # Call count increments for mock object
        assert response is None
        assert 'Missing metrics data from instaclustr - HTTP response code: {0}; HTTP Header Content-Type: {1}'.format(code, content_type) in captured.out


async def test_getInstaclustrTopics_basic(requests_mock):
    ic_auth = {
        "ic_user_name": 'user',
        "ic_api_key": 'key'
    }
    headers = {'Content-Type': 'application/json'}
    topics = '["create-credit-report-event", "instaclustr-sla", "sf-funding-position-event-out", "webhook-delivery-classification"]'.encode('ascii')
    requests_mock.get("https://api.instaclustr.com/monitoring/v1/clusters/fake_clustr/topics", headers=headers, content=topics)

    ## Basic request
    regex_pattern = re.compile('.*')
    response = instaclustr.getInstaclustrTopics('fake_clustr', regex_pattern, auth=ic_auth)
    assert response == 'kt::create-credit-report-event::messagesInPerTopic,\
kt::instaclustr-sla::messagesInPerTopic,kt::sf-funding-position-event-out::messagesInPerTopic,kt::webhook-delivery-classification::messagesInPerTopic'
    assert requests_mock.call_count == 1

    ## Simple regex validation
    regex_pattern = re.compile('instaclustr-.*')
    topic_list = 'kt::{0}::messagesInPerTopic,kt::{0}::bytesOutPerTopic,kt::{0}::bytesInPerTopic,\
kt::{0}::fetchMessageConversionsPerTopic,kt::{0}::produceMessageConversionsPerTopic'
    response = instaclustr.getInstaclustrTopics('fake_clustr', regex_pattern=regex_pattern, ic_topic_list=topic_list, dump_file=False, auth=ic_auth)
    assert response == 'kt::instaclustr-sla::messagesInPerTopic,kt::instaclustr-sla::bytesOutPerTopic,kt::instaclustr-sla::bytesInPerTopic,\
kt::instaclustr-sla::fetchMessageConversionsPerTopic,kt::instaclustr-sla::produceMessageConversionsPerTopic'
    assert requests_mock.call_count == 2


async def test_getInstaclustrConsumerGroups_basic(requests_mock):
    ic_auth = {
        "ic_user_name": 'user',
        "ic_api_key": 'key'
    }
    consumer_groups = ["KafkaConsumer-1", "KafkaConsumer-2", "KafkaConsumer-3", "group-10", "group-20"]
    payload = '["KafkaConsumer-1", "KafkaConsumer-2", "KafkaConsumer-3", "group-10", "group-20"]'.encode('ascii')
    headers = {'Content-Type': 'application/json'}
    regex_pattern = re.compile('.*')
    with patch('instaclustr.helper.sync_dump') as mock_dump:
        mock_dump.return_value = True
        requests_mock.get("https://api.instaclustr.com/monitoring/v1/clusters/fake_clustr/kafka/consumerGroups", headers=headers, content=payload)
        response = instaclustr.getInstaclustrConsumerGroups(cluster_id='fake_clustr', regex_pattern=regex_pattern, auth=ic_auth, dump_file=True)
        assert mock_dump.call_count == 0  # Currently unable to mock the sync_dump function call...
        assert response == consumer_groups


async def test_getInstaclustrConsumerGroupTopics_basic_all(requests_mock):
    ic_auth = {
        "ic_user_name": 'user',
        "ic_api_key": 'key'
    }
    cluster = 'fake_cluster'
    consumer_group = 'fake_consumer_group'
    headers = {'Content-Type': 'application/json'}
    topics = {"test-topic": ["client-1", "client-2"], "test-topz": ["hi"]}
    payload = '{"test-topic": ["client-1", "client-2"], "test-topz": ["hi"]}'.encode('ascii')
    requests_mock.get('https://api.instaclustr.com/monitoring/v1/clusters/{0}/kafka/consumerGroupState?consumerGroup={1}'.format(cluster, consumer_group),
                      headers=headers, content=payload)
    response = instaclustr.getInstaclustrConsumerGroupTopics(cluster_id='fake_cluster', consumer_group=consumer_group, auth=ic_auth,
                                                             topics_only=False, dump_file=True)
    assert json.loads(response.decode()) == topics  # need to decode the binary to compare the dicts


async def test_getInstaclustrConsumerGroupTopics_basic_topics(requests_mock):
    ic_auth = {
        "ic_user_name": 'user',
        "ic_api_key": 'key'
    }
    cluster = 'fake_cluster'
    consumer_group = 'fake_consumer_group'
    headers = {'Content-Type': 'application/json'}
    topics = ["test-topic", "test-topz"]
    payload = '{"test-topic": ["client-1", "client-2"], "test-topz": ["hi"]}'.encode('ascii')
    requests_mock.get('https://api.instaclustr.com/monitoring/v1/clusters/{0}/kafka/consumerGroupState?consumerGroup={1}'.format(cluster, consumer_group),
                      headers=headers, content=payload)
    response = instaclustr.getInstaclustrConsumerGroupTopics(cluster_id=cluster, consumer_group=consumer_group, auth=ic_auth,
                                                             topics_only=True, dump_file=False)
    assert response == topics


async def test_getInstaclustrConsumerGroupMetrics_basic(capfd):
    with patch('aiohttp.ClientSession.get') as mocked_get:
        ## Bad request - HTTP Status code
        code, content_type = 400, 'application/json'
        mocked_get.return_value.__aenter__.side_effect = [
            MagicMock(status=code, headers={'Content-Type': content_type})
        ]
        response = await instaclustr.getInstaclustrConsumerGroupMetrics(
            'dummy_cluster_id', 'consumer_group', 'topic',
            {"ic_user_name": 'user', "ic_api_key": 'key'})
        captured = capfd.readouterr()
        assert mocked_get.call_count == 1  # Call count increments for mock object
        assert response is None
        assert 'Missing consumer group metrics data from instaclustr - HTTP response code: {0}; \
HTTP Header Content-Type: {1}'.format(code, content_type) in captured.out

        ## Bad request - Content-Type
        code, content_type = 200, 'text/html'
        mocked_get.return_value.__aenter__.side_effect = [
            MagicMock(status=code, headers={'Content-Type': content_type})
        ]
        response = await instaclustr.getInstaclustrConsumerGroupMetrics(
            'dummy_cluster_id', 'consumer_group', 'topic',
            {"ic_user_name": 'user', "ic_api_key": 'key'})
        captured = capfd.readouterr()
        assert mocked_get.call_count == 2  # Call count increments for mock object
        assert response is None
        assert 'Missing consumer group metrics data from instaclustr - HTTP response code: {0}; \
HTTP Header Content-Type: {1}'.format(code, content_type) in captured.out


async def test_getInstaclustrConsumerGroupClientMetrics_basic(capfd):
    with patch('aiohttp.ClientSession.get') as mocked_get:
        ## Bad request - HTTP Status code
        code, content_type = 400, 'application/json'
        mocked_get.return_value.__aenter__.side_effect = [
            MagicMock(status=code, headers={'Content-Type': content_type})
        ]
        response = await instaclustr.getInstaclustrConsumerGroupClientMetrics(
            'dummy_cluster_id', 'consumer_group', 'topic',
            {"ic_user_name": 'user', "ic_api_key": 'key'})
        captured = capfd.readouterr()
        assert mocked_get.call_count == 1  # Call count increments for mock object
        assert response is None
        assert 'Missing consumer group client metrics data from instaclustr - HTTP response code: {0}; \
HTTP Header Content-Type: {1}'.format(code, content_type) in captured.out

        ## Bad request - Content-Type
        code, content_type = 200, 'text/html'
        mocked_get.return_value.__aenter__.side_effect = [
            MagicMock(status=code, headers={'Content-Type': content_type})
        ]
        response = await instaclustr.getInstaclustrConsumerGroupClientMetrics(
            'dummy_cluster_id', 'consumer_group', 'topic',
            {"ic_user_name": 'user', "ic_api_key": 'key'})
        captured = capfd.readouterr()
        assert mocked_get.call_count == 2  # Call count increments for mock object
        assert response is None
        assert 'Missing consumer group client metrics data from instaclustr - HTTP response code: {0}; \
HTTP Header Content-Type: {1}'.format(code, content_type) in captured.out
