# ICAPI-DataDog

Forked from the Instaclustr repo.

[![CircleCI](https://circleci.com/gh/lendi-au/ICAPI-DataDog/tree/master.svg?style=svg)](https://circleci.com/gh/lendi-au/ICAPI-DataDog/tree/master)

Provides a simple integration script to push data from the Instaclustr
Monitoring REST API to DataDog. It is specific to Apache Kafka monitoring.

[Instaclustr implementation docs](./instaclustr/README.md)

[DataDog implementation docs](./localdatadog/README.md)

## Usage

Built and tested on `Python 3.8.6` and `Python 3.9.0`.

### Dependencies

Install dependencies via pip3 `pip3 install -r requirements.txt`

### Environment

I use _dotenv_, check out the `.env-sample` file for the list of environment
variables needed to fetch metrics from Instaclustr and ship them to DataDog.

### Run

`python3 ic2datadog.py`.

## Docker Image Build

SemVer is used to increment the builds.
Images are [pushed to Docker Hub](https://hub.docker.com/r/tedk42/ic2datadog).
The tags in DockerHub will match the Releases of this app.

## References

[Kafka metrics exposed by Instaclustr](https://www.instaclustr.com/support/api-integrations/api-reference/monitoring-api/kafka-metrics-exposed-in-the-monitoring-api/)
For detailed instructions on how to set up see [here](https://support.instaclustr.com/hc/en-us/articles/215566468)
