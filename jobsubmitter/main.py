# -*- coding: utf-8 -*-
"""
Created on Wed Dec  9 09:45:19 2015

@author: strokach
"""
import asyncio
import logging
import logging.config

from aiohttp import web

import config
import jobsubmitter

logger = logging.getLogger(__name__)


# %%
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
    logger.debug("data_in:\n{}".format(data_in))

    # Process input
    muts = asyncio.ensure_future(jobsubmitter.main(data_in))
    logger.debug('muts: {}'.format(muts))

    # Prepare output
    if data_in:
        data_out = {'status': 'submitted'}
    else:
        data_out = {'status': 'error'}
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


# %%
if __name__ == '__main__':
    import logging.config
    config.LOGGING_CONFIGS['loggers']['']['handlers'] = ['info_log', 'debug_log']
    logging.config.dictConfig(config.LOGGING_CONFIGS)

    loop = asyncio.get_event_loop()
    handler = app.make_handler()
    f = loop.create_server(handler, '127.0.0.1', 8000)
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
