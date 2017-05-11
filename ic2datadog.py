#!/usr/bin/env python
__author__ = 'ben.slater@instaclustr.com'

from datadog import initialize
from time import sleep
from datadog import statsd
import requests, json
from requests.auth import HTTPBasicAuth
import os

configFile = os.path.dirname(os.path.realpath(__file__)) + "/configuration.json"
f = open(configFile)
configuration = json.loads(f.read())
f.close()

dd_options = configuration['dd_options']

initialize(**dd_options)

auth_details = HTTPBasicAuth(username=configuration['ic_options']['user_name'], password=configuration['ic_options']['api_key'])



consecutive_fails = 0
while True:
    response = requests.get(url="https://api.instaclustr.com/monitoring/v1/clusters/{0}?metrics={1},".format(configuration['cluster_id'], configuration['metrics_list']), auth=auth_details)

    if not response.ok:
        # got an error response from the Instaclustr API - raise an alert in DataDog after 3 consecutive fails
        consecutive_fails += 1
        print "Error retrieving metrics from Instaclustr API: {0} - {1}".format(response.status_code, response.content)
        if consecutive_fails > 3:
            statsd.event("Instaclustr monitoring API error", "Error code is: {0}".format(response.status_code))
        sleep(20)
        continue

    consecutive_fails = 0
    metrics = json.loads(response.content)
    for node in metrics:
        public_ip = node["publicIp"]
        private_ip = node["privateIp"]
        rack_name = node["rack"]["name"]
        data_centre_custom_name = node["rack"]["dataCentre"]["customDCName"]
        data_centre_name = node["rack"]["dataCentre"]["name"]
        data_centre_provider = node["rack"]["dataCentre"]["provider"]
        provider_account_name = node["rack"]["providerAccount"]["name"]
        provider_account_provider = node["rack"]["providerAccount"]["provider"]

        tag_list = ['ic_public_ip:' + public_ip,
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

        for metric in node["payload"]:
            dd_metric_name = 'instaclustr.{0}'.format(metric["metric"])
            if metric["metric"] == "nodeStatus":
                # node status metric maps to a data dog service check
                if metric["values"][0]["value"] =="WARN":
                    statsd.service_check(dd_metric_name, 1, tags=configuration['tags'] + tag_list) # WARN status
                else:
                    statsd.service_check(dd_metric_name, 0, tags=configuration['tags'] + tag_list) # OK status
            else:
                # all other metrics map to a data dog guage
                statsd.gauge(dd_metric_name, metric["values"][0]["value"], tags=configuration['tags'] + tag_list)

    sleep(20)


