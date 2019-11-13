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
cache = TTLCache(maxsize=5, ttl=300)

# Instaclustr endpoints
ic_topics_url = os.getenv('IC_TOPICS_URL', 'https://api.instaclustr.com/monitoring/v1/clusters/{0}/topics')
ic_topic_metrics_url = os.getenv('IC_TOPIC_METRICS_URL', 'https://api.instaclustr.com/monitoring/v1/clusters/{0}?metrics={1}')


def envkey(*args, auth={}, **kwargs):
    key = hashkey(*args)
    key += tuple(sorted(auth.items()))
    return key


# Calls the instaclustr API and returns a metrics payload.
async def getInstaclustrMetrics(cluster_id, metrics_list, auth={}, index=0, dumpfile=False):
    auth_details = aiohttp.BasicAuth(login=auth.get("ic_user_name"), password=auth.get("ic_api_key"))
    target = ic_topic_metrics_url.format(cluster_id, ','.join(metrics_list))
    # auth_details = HTTPBasicAuth(username=ic_user_name, password=ic_api_key)
    session = aiohttp.ClientSession()
    async with session.get(url=target, auth=auth_details) as response:
        if response.status != 200 or response.headers['Content-Type'] != 'application/json':
            logger.error('Missing metrics data from instaclustr - HTTP response code: {0}; \
HTTP Header Content-Type: {1}'.format(response.status, response.headers['Content-Type']))
            await session.close()
            return None
        metrics = await response.text()
        # Dump metrics response as a JSON payload (for testing).
        if dumpfile:
            await dump(metrics, 'instaclustr-{0}.json'.format(index))
        await session.close()
        return metrics


# Fetches topic tags from the cluster for a node and match pattern - cacheable.
@cached(cache, key=envkey)
def getInstaclustrTopics(cluster_id, regex_pattern: re.Pattern, ic_topic_list='kt::{0}::messagesInPerTopic', dumpFile=False, auth={}):
    auth_details = HTTPBasicAuth(username=auth.get("ic_user_name"), password=auth.get("ic_api_key"))
    target = 'https://api.instaclustr.com/monitoring/v1/clusters/{0}/topics'.format(cluster_id)
    response = requests.get(url=target, auth=auth_details)
    if not response.ok or response.headers['Content-Type'] != 'application/json':
        logger.error('Could not return topics from Instaclustr - {0}'.format(response.status_code))
        return None
    if dumpFile:
        sync_dump(response.content, 'instaclustr-topics.json')
    logger.debug('Topics from Instaclustr: {}'.format(response.content))
    # Generate the topic metrics list from the returned topics
    topics = list(filter(regex_pattern.match, json.loads(response.content)))
    extra_metrics = ','.join([ic_topic_list.format(x) for x in topics])
    return extra_metrics
