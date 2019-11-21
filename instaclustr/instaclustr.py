from instaclustr.helper import dump, sync_dump
import aiohttp, requests, json, logging
from requests.auth import HTTPBasicAuth
import os, sys
import re
from cachetools import cached, TTLCache
from cachetools.keys import hashkey

## Logging config
logger = logging.getLogger(__name__)
log_level = logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO').upper())
logger.setLevel(log_level)
logger.addHandler(logging.StreamHandler(sys.stdout))


# cache setup
cache = TTLCache(maxsize=5, ttl=600)
cache_cg = TTLCache(maxsize=100, ttl=600)  # YMMV on the maxsize
cache_cgt = TTLCache(maxsize=100, ttl=600)  # YMMV on the maxsize

# Instaclustr endpoints
ic_topics_url = os.getenv('IC_TOPICS_URL', 'https://api.instaclustr.com/monitoring/v1/clusters/{0}/topics')
ic_topic_metrics_url = os.getenv('IC_TOPIC_METRICS_URL', 'https://api.instaclustr.com/monitoring/v1/clusters/{0}?metrics={1}')
ic_consumer_group_url = os.getenv('IC_CONSUMER_GROUP_URL', 'https://api.instaclustr.com/monitoring/v1/clusters/{0}/kafka/consumerGroups')
ic_consumer_group_topics_url = os.getenv('IC_CONSUMER_GROUP_TOPICS_URL',
                                         'https://api.instaclustr.com/monitoring/v1/clusters/{0}/kafka/consumerGroupState?consumerGroup={1}')
ic_consumer_group_metrics_url = os.getenv('IC_CONSUMER_GROUP_METRICS_URL', 'https://api.instaclustr.com/monitoring/v1/clusters/{0}\
/kafka/consumerGroupMetrics?consumerGroup={1}&topic={2}&metrics=consumerGroupLag,clientCount')
ic_consumer_group_client_metrics_url = os.getenv('IC_CONSUMER_GROUP_CLIENT_METRICS_URL', 'https://api.instaclustr.com/monitoring/v1\
/clusters/{0}/kafka/consumerGroupClientMetrics?consumerGroup={1}&topic={2}&metrics=consumerLag,consumerCount,partitionCount')


def envkey(*args, auth={}, **kwargs):
    key = hashkey(*args, **kwargs)
    key += tuple(sorted(auth.items()))
    return key


# Calls the instaclustr API and returns a metrics payload.
async def getInstaclustrMetrics(cluster_id, metrics_list, auth={}, index=0, dump_file=False):
    auth_details = aiohttp.BasicAuth(login=auth.get("ic_user_name"), password=auth.get("ic_api_key"))
    target = ic_topic_metrics_url.format(cluster_id, ','.join(metrics_list))
    session = aiohttp.ClientSession()
    async with session.get(url=target, auth=auth_details) as response:
        if response.status != 200 or response.headers['Content-Type'] != 'application/json':
            logger.error('Missing metrics data from instaclustr - HTTP response code: {0}; \
HTTP Header Content-Type: {1}'.format(response.status, response.headers['Content-Type']))
            await session.close()
            return None
        metrics = await response.text()
        # Dump metrics response as a JSON payload (for testing).
        if dump_file:
            await dump(metrics, 'instaclustr-{0}.json'.format(index))
        await session.close()
        return metrics


# Fetches topic tags from the cluster for a node and match pattern - cacheable.
@cached(cache, key=envkey)
def getInstaclustrTopics(cluster_id, regex_pattern: re.Pattern, ic_topic_list='kt::{0}::messagesInPerTopic', dump_file=False, auth={}):
    auth_details = HTTPBasicAuth(username=auth.get("ic_user_name"), password=auth.get("ic_api_key"))
    target = ic_topics_url.format(cluster_id)
    response = requests.get(url=target, auth=auth_details)
    if not response.ok or response.headers['Content-Type'] != 'application/json':
        logger.error('Could not return topics from Instaclustr - {0}'.format(response.status_code))
        return None
    if dump_file:
        sync_dump(response.content, 'instaclustr-topics.json')
    logger.debug('Topics from Instaclustr: {}'.format(response.content))
    # Generate the topic metrics list from the returned topics
    topics = list(filter(regex_pattern.match, json.loads(response.content)))
    extra_metrics = ','.join([ic_topic_list.format(x) for x in topics])
    return extra_metrics


@cached(cache=cache_cg, key=envkey)
def getInstaclustrConsumerGroups(cluster_id, regex_pattern: re.Pattern, dump_file=False, auth={},):
    auth_details = HTTPBasicAuth(username=auth.get("ic_user_name"), password=auth.get("ic_api_key"))
    target = ic_consumer_group_url.format(cluster_id)
    response = requests.get(url=target, auth=auth_details)
    if not response.ok or response.headers['Content-Type'] != 'application/json':
        logger.error('Could not return consumer groups from Instaclustr - {0}'.format(response.status_code))
        logger.error(target)
        return None
    if dump_file:
        sync_dump(response.content, 'instaclustr-consumer-groups.json')
    logger.debug('Consumer Groups from Instaclustr: {}'.format(response.content))
    groups = list(filter(regex_pattern.match, response.json()))
    return groups


@cached(cache=cache_cgt, key=envkey)
def getInstaclustrConsumerGroupTopics(cluster_id, consumer_group, topics_only=True, dump_file=False, auth={}):
    auth_details = HTTPBasicAuth(username=auth.get("ic_user_name"), password=auth.get("ic_api_key"))
    target = ic_consumer_group_topics_url.format(cluster_id, consumer_group)
    response = requests.get(url=target, auth=auth_details)
    if not response.ok or response.headers['Content-Type'] != 'application/json':
        logger.error('Could not return consumer group topics from Instaclustr - {0}'.format(response.status_code))
        logger.error(target + auth.get("ic_api_key"))
        return None
    if dump_file:
        sync_dump(response.content, 'instaclustr-consumer-group-topics-{0}.json'.format(consumer_group))
    if topics_only:
        return [b for b in response.json()]
    return response.content


# Calls the instaclustr API and returns consumer group metrics payload.
async def getInstaclustrConsumerGroupMetrics(cluster_id, consumer_group, topic, auth={}, dump_file=False):
    auth_details = aiohttp.BasicAuth(login=auth.get("ic_user_name"), password=auth.get("ic_api_key"))
    target = ic_consumer_group_metrics_url.format(cluster_id, consumer_group, topic)
    session = aiohttp.ClientSession()
    async with session.get(url=target, auth=auth_details) as response:
        if response.status != 200 or response.headers['Content-Type'] != 'application/json':
            logger.error('Missing consumer group metrics data from instaclustr - HTTP response code: {0}; \
HTTP Header Content-Type: {1}'.format(response.status, response.headers['Content-Type']))
            logger.error(target)
            await session.close()
            return None
        metrics = await response.text()
        # Dump metrics response as a JSON payload (for testing).
        if dump_file:
            await dump(metrics, 'consumer-group-metrics-{0}-{1}.json'.format(consumer_group, topic))
        await session.close()
        return metrics


# Calls the instaclustr API and returns consumer group client metrics payload.
async def getInstaclustrConsumerGroupClientMetrics(cluster_id, consumer_group, topic, auth={}, dump_file=False):
    auth_details = aiohttp.BasicAuth(login=auth.get("ic_user_name"), password=auth.get("ic_api_key"))
    target = ic_consumer_group_client_metrics_url.format(cluster_id, consumer_group, topic)
    session = aiohttp.ClientSession()
    async with session.get(url=target, auth=auth_details) as response:
        if response.status != 200 or response.headers['Content-Type'] != 'application/json':
            logger.error('Missing consumer group client metrics data from instaclustr - HTTP response code: {0}; \
HTTP Header Content-Type: {1}'.format(response.status, response.headers['Content-Type']))
            logger.error(target)
            await session.close()
            return None
        metrics = await response.text()
        # Dump metrics response as a JSON payload (for testing).
        if dump_file:
            await dump(metrics, 'consumer-group-client-metrics-{0}-{1}.json'.format(consumer_group, topic))
        await session.close()
        return metrics
