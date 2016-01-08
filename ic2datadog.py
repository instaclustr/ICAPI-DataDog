__author__ = 'ben.slater@instaclustr.com'

from datadog import initialize
from time import sleep
from datadog import statsd
import requests, json
from requests.auth import HTTPBasicAuth

configFile = "configuration.json"
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
        if consecutive_fails > 3:
            statsd.event("Instaclustr monitoring API error", "Error code is: {0}".format(response.status_code))
        sleep(20)
        continue

    consecutive_fails = 0
    metrics = json.loads(response.content)
    for node in metrics:
        public_ip = node["publicIp"]
        for metric in node["payload"]:
            dd_metric_name = 'instaclustr.{0}.{1}'.format(public_ip,metric["metric"])
            if metric["metric"] == "nodeStatus":
                # node status metric maps to a data dog service check
                if metric["values"][0]["value"] =="WARN":
                    statsd.service_check(dd_metric_name, 1) # WARN status

                else:
                    statsd.service_check(dd_metric_name, 0) # OK status

            else:
                # all other metrics map to a data dog guage
                statsd.gauge(dd_metric_name, metric["values"][0]["value"])

    sleep(20)


