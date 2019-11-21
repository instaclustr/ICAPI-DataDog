# Instaclustr (IC) API Doc

Collection of all the Instaclustr related calls this application makes.
Important to not is that you can only retrieve 20 Instaclustr metrics at a time.

## Standard metrics

The `IC_METRICS_LIST` variable determines which IC metrics we are interested in.

## Topic Metrics

Fetching topics relies on the `IC_TOPIC_REGEX` to be set. As the name implies,
topics which match the regex pattern will be read from Instaclustr.

## Consumer Group Metrics

Fetching consumer group metrics (and consumer group client metrics) relies on
the `IC_CONSUMER_GROUP_REGEX` variable to be set.

Sadly the API doesn't expose the consumer group metrics in a similar way it does
with the topics.

For starters, it has its own endpoint so we couldn't reuse the code easily,
though much of the logic is quite similar. The sample bash script below
describes how you might do this with cUrl.

```bash
CLUSTER_ID=09d41322-8b24-4bbe-9928-621e415b5e7f
CONSUMER_GROUP=kafka-group
TOPIC=kafka-topic

# Get topic list for Consumer Group
curl -u ${IC_USER_NAME}:${IC_API_KEY} "https://api.instaclustr.com/monitoring/v1/clusters/${CLUSTER_ID}/kafka/consumerGroupState?consumerGroup=${CONSUMER_GROUP}"

# Show consumer group client metrics for the topic
curl -u ${IC_USER_NAME}:${IC_API_KEY} "https://api.instaclustr.com/monitoring/v1/clusters/${CLUSTER_ID}/kafka/consumerGroupClientMetrics?consumerGroup=${CONSUMER_GROUP}&metrics=consumerLag,consumerCount,partitionCount&topic=${TOPIC}"

# Show consumer group metrics for the topic
curl -u ${IC_USER_NAME}:${IC_API_KEY} "https://api.instaclustr.com/monitoring/v1/clusters/${CLUSTER_ID}/kafka/consumerGroupMetrics?consumerGroup=${CONSUMER_GROUP}&topic=${TOPIC}&metrics=consumerGroupLag,clientCount"
```

### Fetch flow

First we fetch the list of consumer-groups by invoking the function
`getInstaclustrConsumerGroups`.

Next we can get the topics which are available for a consumer group by calling
the function `getInstaclustrConsumerGroupTopics`.

Searching for each consumer group and topic, we can fetch the consumer group
and consumer group client metrics by calling the two functions
`getInstaclustrConsumerGroupMetrics` and
`getInstaclustrConsumerGroupClientMetrics`

### Limitations

The API for Consumer Group metrics only support fetching 1 query parameter for
the consumer group and topic - both of which are mandatory to use the API.

As our clusters (in multiple environments) have topics and consumer groups
being created dynamically based on needs, we need to poll the Instaclustr API
for an updated list of the two. Caching solves this problem for us and I remark
that _YMMV_ with the cache settings set in the code (i.e. 10min TTL, 100
objects).

With `export LOG_LEVEL=info`, the difference in successive runs with caching
activated is an order of magnitude better than without.

```json
# Number of consumer groups found in the cluster (less than 100, which is the
# cache size)
{
  "type": "log",
  "written_at": "2019-11-18T03:22:50.700Z",
  "written_ts": 1574047370700651000,
  "component_id": "-",
  "component_name": "-",
  "component_instance": 0,
  "logger": "instaclustr-monitor",
  "thread": "MainThread",
  "level": "INFO",
  "line_no": 94,
  "module": "ic2datadog",
  "msg": "Number of consumer groups found: 38"
}

# First API call to instaclustr to fetch metrics and send to DD
{
  "type": "log",
  "written_at": "2019-11-18T03:22:50.700Z",
  "written_ts": 1574047370700651000,
  "component_id": "-",
  "component_name": "-",
  "component_instance": 0,
  "logger": "instaclustr-monitor",
  "thread": "MainThread",
  "level": "INFO",
  "line_no": 94,
  "module": "ic2datadog",
  "msg": "Number of consumer groups found: 38"
}
{
  "type": "log",
  "written_at": "2019-11-18T03:23:40.668Z",
  "written_ts": 1574047420668667000,
  "component_id": "-",
  "component_name": "-",
  "component_instance": 0,
  "logger": "instaclustr-monitor",
  "thread": "MainThread",
  "level": "INFO",
  "line_no": 136,
  "module": "ic2datadog",
  "msg": "total time 52.49968409538269 seconds"
}

# Next call to instaclustr API and send to DD
{
  "type": "log",
  "written_at": "2019-11-18T03:24:48.831Z",
  "written_ts": 1574047488831456000,
  "component_id": "-",
  "component_name": "-",
  "component_instance": 0,
  "logger": "instaclustr-monitor",
  "thread": "MainThread",
  "level": "INFO",
  "line_no": 136,
  "module": "ic2datadog",
  "msg": "total time 3.667846918106079 seconds"
}

```
