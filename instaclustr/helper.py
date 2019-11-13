import logging, os, sys, aiofiles, json
logger = logging.getLogger(__name__)
log_level = logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO').upper())
logger.setLevel(log_level)
logger.addHandler(logging.StreamHandler(sys.stdout))

## Dump output directory

output_dir = os.getenv('PAYLOAD_OUTPUT_DIR', './test-data')
output_dir.strip("/")


# split the metrics list into groups size n
def splitMetricsList(l, n):
    # For item i in a range that is a length of l,
    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i + n]


# dump will async output an object to a file - always dumps to test-data directory.
async def dump(contents, filename='output.json'):
    if filename == 'output.json':
        logger.warn('using default output.json to dump file')
    output = '{0}/{1}'.format(output_dir, filename)
    try:
        logger.info('Dumping output to file {0}'.format(output))
        async with aiofiles.open(output, mode='w') as f:
            await f.write(contents)
    except Exception as e:
        logger.error('Could not dump output to file: ' + str(e))


# sync dump outputs an object to a file
def sync_dump(contents, filename='output.json'):
    if filename == 'output.json':
        logger.warn('using default output.json to dump file')
    output = '{0}/{1}'.format(output_dir, filename)
    try:
        logger.info('Dumping output to file {0}'.format(output))
        with open(output, 'w') as outfile:
            json.dump(json.loads(contents), outfile)
    except Exception as e:
        logger.error('Could not dump output to file' + str(e))
