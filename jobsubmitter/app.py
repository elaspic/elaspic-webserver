import os
import os.path as op
import shutil
import asyncio
import logging
import logging.config

from aiohttp import web

import config
import jobsubmitter
from django.conf import settings

logger = logging.getLogger(__name__)


async def generic_handler(request, request_type):
    """
    """
    # Print info
    logger.debug('{} request: {}'.format(request_type, request))
    # print_attributes(request)

    # Parse input
    if request_type == 'GET':
        data_in = dict(request.GET)
    elif request_type == 'POST':
        data_in = await request.json()
    else:
        raise Exception('Wrong request_type: {}'.format(request_type))
    logger.debug("data_in: {}".format(data_in))

    # Process input
    if data_in and data_in.get('secret_key') == settings.JOBSUBMITTER_SECRET_KEY:
        # Submit job
        muts = asyncio.ensure_future(jobsubmitter.main(data_in))
        logger.debug('muts: {}'.format(muts))
        data_out = {'status': 'submitted'}
    else:
        # Invalid request
        data_out = {'status': 'error', 'data_in': data_in}
    logger.debug('data_out:\n{}'.format(data_out))

    # Response
    resp = web.json_response(data_out, status=200)
    logger.debug('resp:\n{}'.format(resp))
    return resp


async def get(request):
    return await generic_handler(request, 'GET')


async def post(request):
    return await generic_handler(request, 'POST')


app = web.Application()
app.router.add_route('GET', '/elaspic/api/1.0/', get)
app.router.add_route('POST', '/elaspic/api/1.0/', post)


if __name__ == '__main__':
    import argparse
    import logging.config

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interactive', action='store_true')
    args = parser.parse_args()

    if args.interactive:
        config.LOGGING_CONFIGS['loggers']['']['handlers'] = ['console']
    else:
        config.LOGGING_CONFIGS['loggers']['']['handlers'] = ['debug_log']  # ['info_log']
    logging.config.dictConfig(config.LOGGING_CONFIGS)

    # Copy scripts
    local_script_dir = op.abspath(op.join(op.dirname(__file__), 'scripts'))
    os.makedirs(config.SCRIPTS_DIR, exist_ok=True)
    logger.info("Copying script files to remote ('{}')...".format(config.SCRIPTS_DIR))
    for file in os.listdir(local_script_dir):
        logger.debug(file)
        try:
            shutil.copy(
                op.join(local_script_dir, file),
                op.join(config.SCRIPTS_DIR, file)
            )
        except PermissionError:
            logger.warning("Do not have permission to copy file %s.", file)
    logger.info("Done!")

    loop = asyncio.get_event_loop()
    handler = app.make_handler()
    f = loop.create_server(handler, '0.0.0.0', 8000)
    srv = loop.run_until_complete(f)
    print('serving on: {}'.format(srv.sockets[0].getsockname()))
    logger.info('*' * 75)
    logger.info('serving on: {}'.format(srv.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(handler.finish_connections(1.0))
        loop.run_until_complete(jobsubmitter.cleanup())
        srv.close()
        loop.run_until_complete(srv.wait_closed())
        loop.run_until_complete(app.finish())
    loop.close()
