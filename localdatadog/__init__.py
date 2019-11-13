from datadog import initialize
import logging
logger = logging.getLogger(__name__)
name = "localdatadog"
# Assuming you've set `DD_API_KEY` and `DD_APP_KEY` in your env,
# initialize() will pick it up automatically
initialize()
