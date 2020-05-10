from aiohttp import web
from aiohttp.web import HTTPNotFound
import aiofiles
import asyncio
import os
import logging
import argparse


async def archivate(request):
    photos_path = request.app.args.path

    archive_hash = request.match_info['archive_hash']
    archive_path = os.path.join(photos_path, archive_hash)

    if not os.path.exists(archive_path):
        raise HTTPNotFound(text='Архив не существует или был удален')

    response = web.StreamResponse()
    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip"'
    await response.prepare(request)

    process = await asyncio.create_subprocess_exec('zip',
                                                   *['-r', '-', archive_hash],
                                                   cwd=photos_path,
                                                   stdout=asyncio.subprocess.PIPE,
                                                   stderr=asyncio.subprocess.PIPE)
    try:
        while True:
            archive_chunk = await process.stdout.readline()
            await response.write(archive_chunk)
            if not archive_chunk:
                break

            if request.app.args.delay:
                await asyncio.sleep(1)  # Для имитации медленного коннекта

    except asyncio.CancelledError:
        process.kill()
        await process.communicate()

        if request.app.args.logging:
            logging.info('Download was interrupted')
    finally:
        return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def read_arguments():
    parser = argparse.ArgumentParser(description='Download microservice')
    parser.add_argument('-l', '--logging', action='store_true', help='Enable logging')
    parser.add_argument('-d', '--delay', action='store_true', help='Enable response delay')
    parser.add_argument('-p', '--path', default="test_photos", help='Photos path')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = read_arguments()
    logging.basicConfig(level=logging.INFO)

    app = web.Application()
    app.args = args
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
