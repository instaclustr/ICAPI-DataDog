#!/usr/bin/env python
__author__ = 'ben.slater@instaclustr.com'

from time import sleep
import asyncio, json, json_logging, logging
import os, signal, sys, argparse
import re, time

# My custom imports
from instaclustr.instaclustr import getInstaclustrMetrics, getInstaclustrTopics, \
    getInstaclustrConsumerGroups, getInstaclustrConsumerGroupTopics, \
    getInstaclustrConsumerGroupMetrics, getInstaclustrConsumerGroupClientMetrics
from instaclustr.helper import splitMetricsList
from localdatadog.datadog import shipToDataDog


# Logging setup
app_name = os.getenv('APP_NAME', 'instaclustr-monitor')
log_level = logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO').upper())
json_logging.init_non_web(enable_json=True)
logger = logging.getLogger(app_name)
logger.setLevel(log_level)
logger.addHandler(logging.StreamHandler(sys.stdout))

# Environment variable setup
default_value = ''
ic_cluster_id = os.getenv('IC_CLUSTER_ID', default_value)
ic_metrics_list = os.getenv('IC_METRICS_LIST',
                            'k::slaConsumerRecordsProcessed,n::cpuutilization,n::diskUtilization,\
                            n::osLoad,k::kafkaBrokerState,k::slaProducerErrors,k::slaConsumerLatency,\
                            k::slaProducerLatencyMs,k::underReplicatedPartitions,k::activeControllerCount,\
                            k::offlinePartitions,k::leaderElectionRate,k::uncleanLeaderElections,\
                            k::leaderCount,k::isrExpandRate,k::isrShrinkRate')
## Each metric must be formatted as such 'kt::{0}::metric' as {0} will be replaced.
ic_topic_list = os.getenv('IC_TOPIC_LIST',
                          'kt::{0}::messagesInPerTopic,kt::{0}::bytesOutPerTopic,kt::{0}::bytesInPerTopic,\
                          kt::{0}::fetchMessageConversionsPerTopic,kt::{0}::produceMessageConversionsPerTopic,\
                          kt::{0}::failedFetchMessagePerTopic,kt::{0}::failedProduceMessagePerTopic')
ic_user_name = os.getenv('IC_USER_NAME', default_value)
ic_api_key = os.getenv('IC_API_KEY', default_value)
## IC_TAGS should be a comma separated list of strings, e.g. tag1:this,tag2:that
ic_tags = os.getenv('IC_TAGS', 'environment:development').split(',')
dd_metric_prefix = os.getenv('DD_METRIC_PREFIX', 'instaclustr')
sleepy = int(os.getenv('TIME_BETWEEN_FETCH', 30))

## Added regex for topics we want to scrape.
ic_topic_regex = os.getenv('IC_TOPIC_REGEX', default_value)

## Added regex for consumer groups we want to scrape.
ic_consumer_group_regex = os.getenv('IC_CONSUMER_GROUP_REGEX', default_value)


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


def ic_fetch_topics(regex, auth):
    logger.info('Topic regex set. Will get topic metrics that match')
    regex_pattern = re.compile(regex)
    topic_list = getInstaclustrTopics(ic_cluster_id, regex_pattern,
                                      ic_topic_list=ic_topic_list, auth=auth)
    return (ic_metrics_list + ',' + topic_list).split(',')


async def main():
    instaclustr_fails = 0
    parser = argparse.ArgumentParser(description='Instaclustr metrics to DataDog forwarder.')
    parser.add_argument('--once', type=bool, nargs='?',
                        const=True, default=False,
                        help='only run the metrics forwarding once')
    args = parser.parse_args()

    while True:
        start_time = time.time()
        ic_auth = {
            "ic_user_name": ic_user_name,
            "ic_api_key": ic_api_key
        }
        instaclustr_response, dd_loop = [], []
        # Retrieve kafka topic metrics if regex set
        if (ic_topic_regex != default_value):
            all_metrics = ic_fetch_topics(ic_topic_regex, ic_auth)
        else:
            all_metrics = ic_metrics_list.split(',')
        logger.debug(all_metrics)

        # # Retrieve kafka consumer group metrics if regex set and ship to DataDog
        if (ic_consumer_group_regex != default_value):
            logger.info('Consumer group regex set ({0}). Will get consumer groups that match'.format(ic_consumer_group_regex))
            regex_pattern = re.compile(ic_consumer_group_regex)
            consumer_groups = getInstaclustrConsumerGroups(ic_cluster_id, regex_pattern, auth=ic_auth)
            logger.info('Number of consumer groups found: {0}'.format(len(consumer_groups)))
            for cg in consumer_groups:
                topics = getInstaclustrConsumerGroupTopics(ic_cluster_id, cg, auth=ic_auth)
                logger.info('Number of topics found for consumer group {0}: {1}'.format(cg, len(topics)))
                for topic in topics:
                    cg_metrics = asyncio.create_task(getInstaclustrConsumerGroupMetrics(ic_cluster_id, cg, topic, ic_auth))
                    instaclustr_response.append(cg_metrics)
                    cg_client_metrics = asyncio.create_task(getInstaclustrConsumerGroupClientMetrics(ic_cluster_id, cg, topic, ic_auth))
                    instaclustr_response.append(cg_client_metrics)

        # Divide into groups of 20 metrics (instaclustr API max query amount)
        groups = splitMetricsList(all_metrics, 20)
        group_index = 0
        for subset in groups:
            metrics = asyncio.create_task(getInstaclustrMetrics(cluster_id=ic_cluster_id, metrics_list=subset,
                                          auth=ic_auth, index=group_index, dump_file=False))
            instaclustr_response.append(metrics)
            group_index += 1

        # Process async tasks as they finish
        for f in asyncio.tasks.as_completed(instaclustr_response):
            # sleep(1)
            resp = await f
            # getInstaclustrMetrics will return None if it cannot fetch data.
            if resp is None:
                instaclustr_fails += 1
                continue  # skip sending to DD
            if instaclustr_fails > 3:
                logger.fatal("Multiple errors occurred with instaclustr monitoring API. Resetting error count.")
                instaclustr_fails = 0
                continue  # skip sending to DD
            metrics = json.loads(resp)
            dd_async_task = asyncio.create_task(shipToDataDog(ic_cluster_id, dd_metric_prefix, ic_tags, metrics))
            dd_loop.append(dd_async_task)

        # Process HTTP POST to DataDog as they finish
        await asyncio.gather(*dd_loop)

        # Reset the fail count for the next run
        instaclustr_fails = 0

        duration = time.time() - start_time
        logger.info("total time {0} seconds".format(duration))
        if args.once:
            break
        sleep(sleepy)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
