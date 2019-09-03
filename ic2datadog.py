#!/usr/bin/env python
__author__ = 'ben.slater@instaclustr.com'

from datadog import initialize, api
from time import sleep
from datetime import datetime
import requests, json, json_logging, logging
from requests.auth import HTTPBasicAuth
import os, signal, sys, argparse

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)

# Logging setup
app_name = os.getenv('APP_NAME', 'instaclustr-monitor')
log_level = logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO').upper())
json_logging.ENABLE_JSON_LOGGING = os.getenv('ENABLE_JSON_LOGGING', 'TRUE') in ['true', 'True', 'TRUE', '1', 'y', 'yes']
json_logging.init_non_web()
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
ic_user_name = os.getenv('IC_USER_NAME', default_value)
ic_api_key = os.getenv('IC_API_KEY', default_value)
## IC_TAGS should be a comma separated list of strings, e.g. tag1:this,tag2:that
ic_tags = os.getenv('IC_TAGS', 'environment:development').split(',')

ic_target = os.getenv('IC_TARGET', 'https://api.instaclustr.com/monitoring/v1/clusters/{}?metrics={}')
ic_target = ic_target.format(ic_cluster_id, ic_metrics_list)
logger.debug(ic_target)

# Builds the DataDog tags from the instaclustr data
def buildTags(node):
    id = node["id"] or ''
    public_ip = node["publicIp"] or ''
    private_ip = node["privateIp"] or ''
    rack_name = node["rack"]["name"] or ''
    data_centre_custom_name = node["rack"]["dataCentre"]["customDCName"] or ''
    data_centre_name = node["rack"]["dataCentre"]["name"] or ''
    data_centre_provider = node["rack"]["dataCentre"]["provider"] or ''
    provider_account_name = node["rack"]["providerAccount"]["name"] or ''
    provider_account_provider = node["rack"]["providerAccount"]["provider"] or ''

    tag_list = ['ic_cluster_id:' + id,
                'ic_public_ip:' + public_ip,
                'ic_private_ip:' + private_ip,
                'ic_rack_name:' + rack_name,
                'ic_data_centre_custom_name:' + data_centre_custom_name,
                'ic_data_centre_name:' + data_centre_name,
                'ic_data_centre_provider:' + data_centre_provider,
                'ic_provider_account_name:' + provider_account_name,
                'ic_provider_account_provider:' + provider_account_provider
                ]
    if data_centre_provider == 'AWS_VPC':
        tag_list = tag_list + [
            'region:' + node["rack"]["dataCentre"]["name"].lower().replace("_", "-"),
            'availability_zone:' + node["rack"]["name"]
        ]
    return tag_list

# Calls the instaclustr API and returns the payload we expect.
def getInstaclustrMetrics(target, dump=False):
    auth_details = HTTPBasicAuth(username=ic_user_name, password=ic_api_key)
    response = requests.get(url=target, auth=auth_details)

    # Dump metrics response as a JSON payload (for testing).
    if dump and response.ok and response.headers['Content-Type'] == 'application/json':
        logger.info('Dumping output to file ./test-data/instaclustr.json')
        with open('./test-data/instaclustr.json', 'w') as outfile:
            json.dump(json.loads(response.content), outfile)

    return response

def shipToDataDog(metrics=[]):
    epoch = datetime(1970, 1, 1)
    myformat = "%Y-%m-%dT%H:%M:%S.%fZ"
    for node in metrics:
        send_list = []
        id = node["id"] or ''
        tag_list = buildTags(node)

        for metric in node["payload"]:
            dd_metric_name = 'instaclustr.{0}.{1}'.format(metric["metric"],metric["type"])
            mydt = datetime.strptime(metric["values"][0]["time"], myformat)
            time_val= int((mydt - epoch).total_seconds())
            logger.debug(metric)
            logger.debug(dd_metric_name)
            send_list.append({'metric' : dd_metric_name, 'points' : [(time_val,float(metric["values"][0]["value"]))],'tags' : ic_tags + tag_list})

        # Sends metrics per node as per tagging rules.
        if (send_list):
            logger.debug('Sending: {0}'.format(send_list))
            dd_response = api.Metric.send(send_list)
            if dd_response['status'] != 'ok':
                logger.fatal('Error sending metrics to DataDog: {0}'.format(dd_response))
            else:
                logger.info('Sent metrics of node {0} to DataDog API with response: {1}'.format(id, dd_response['status']))
        else:
            logger.info('Empty list from the instaclustr API for the node: {0}'.format(id))

def main():
    consecutive_fails = 0
    # Assuming you've set `DD_API_KEY` and `DD_APP_KEY` in your env,
    # initialize() will pick it up automatically
    initialize()
    parser = argparse.ArgumentParser(description='Instaclustr metrics to DataDog forwarder.')
    parser.add_argument('--once', type=bool, nargs='?',
                        const=True, default=False,
                        help='only run the metrics forwarding once')
    args = parser.parse_args()

    while True:
        response = getInstaclustrMetrics(target=ic_target)

        if not response.ok:
            # got an error response from the Instaclustr API - raise an alert in DataDog after 3 consecutive fails
            consecutive_fails += 1
            logger.error('Error retrieving metrics from Instaclustr API: {0} - {1}'.format(response.status_code, response.content))
            logger.debug(response)
            if consecutive_fails > 3:
                logger.fatal("Instaclustr monitoring API error", "Error code is: {0}".format(response.status_code))
            # Sleep for longer as error has occurred and someone will be notified from the log message...
            sleep(60)
            continue

        consecutive_fails = 0
        metrics = json.loads(response.content)
        logger.info('Retrieve metrics from instaclustr ok - size: {0}'.format(len(response.content)))

        shipToDataDog(metrics)
        if args.once:
            break
        sleep(20)

if __name__== "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    main()
