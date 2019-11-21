# DataDog API

This module is a wrapper around the datadog api library. We use the
`api.Metric.send` endpoint in an async manner with the related instaclustr
tags sent with the request.

## Enhancements

Given the volume of metrics sent through to DataDog, it might be good to batch
the requests in a _nice_ way.

An internal retry mechanism might also be useful.
