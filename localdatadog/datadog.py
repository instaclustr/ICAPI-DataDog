import logging, sys, os, time
from datetime import datetime
from datadog import api
from .helper import buildTags
from instaclustr.helper import sync_dump
from asgiref.sync import sync_to_async
sys.path.append("..")

# Logging setup
logger = logging.getLogger(__name__)
log_level = logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO').upper())
logger.setLevel(log_level)
logger.addHandler(logging.StreamHandler(sys.stdout))


@sync_to_async(thread_sensitive=False)
def shipToDataDog(ic_cluster_id: str, dd_metric_prefix: str, ic_tags=[], metrics=[], dump_file=False):
    epoch = datetime(1970, 1, 1)
    myformat = "%Y-%m-%dT%H:%M:%S.%fZ"
    send_list = []
    for node in metrics:
        tag_list = buildTags(node, ic_cluster_id)
        # Pre-populate if it's a consumer group metric
        topic_tag = ['topic:' + node["topic"]] if "topic" in node else []
        # Consumer group tags populated at this level
        consumer_group_tag = ['consumerGroup:' + node["consumerGroup"]] if "consumerGroup" in node else []
        client_id_tag = ['clientID:' + node["clientID"]] if "clientID" in node else []
        for metric in node["payload"]:
            topic_tag = ['topic:' + metric["topic"]] if "topic" in metric else topic_tag
            dd_metric_name = '{0}.{1}.{2}'.format(dd_metric_prefix, metric["metric"], metric["type"])
            try:
                mydt = datetime.strptime(metric["values"][0]["time"], myformat)
                time_val = int((mydt - epoch).total_seconds())
                logger.debug(metric)
                logger.debug(dd_metric_name)
                send_list.append({'metric': dd_metric_name,
                                  'points': [(time_val, float(metric["values"][0]["value"]))],
                                  'tags': ic_tags + tag_list + topic_tag + consumer_group_tag + client_id_tag})
            except IndexError:
                # No time component to the metric: kafka broker state metric edge case.
                logger.debug(metric)
                logger.debug(dd_metric_name)
                time_val = int(time.time())
                send_list.append({'metric': dd_metric_name,
                                  'points': [(time_val, float(metric["unit"]))],
                                  'tags': ic_tags + tag_list + topic_tag + consumer_group_tag + client_id_tag})
                pass

    # Sends metrics per node as per tagging rules.
    if (send_list):
        logger.debug('Sending: {0}'.format(send_list))
        if dump_file:
            sync_dump(send_list, 'datadog-output.json')
        try:
            dd_response = api.Metric.send(send_list)
            if dd_response['status'] != 'ok':
                logger.fatal('Error sending metrics to DataDog: {0}'.format(dd_response))
            else:
                logger.info('Sent metrics of node to DataDog API with response: {0}'.format(dd_response['status']))
                return 'ok'
        except Exception as e:
            logger.error('Could not send metrics to DataDog: ' + str(e))
    else:
        logger.error('Empty list from the instaclustr API for the cluster: {0}'.format(ic_cluster_id))
    return None
