import asyncio
from flask import Flask, request, send_file
import aiohttp
import aiofiles
import os
import shutil
import uuid
import logging

def guess_extension(content_type):
    if content_type == 'image/jpeg':
        return '.jpg'
    elif content_type == 'image/png':
        return '.png'
    elif content_type == 'application/pdf':
        return '.pdf'
    # Add more cases as needed
    else:
        return ''



logging.basicConfig(filename='app.log', level=logging.INFO)
app = Flask(__name__)

html = '''
    <style>
        body {
            font-family: Arial, sans-serif;
        }
        form {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 20px;
        }
        input[type="text"] {
            width: 70%;
            padding: 12px 20px;
            margin: 8px 0;
            box-sizing: border-box;
            border: 2px solid #ccc;
            border-radius: 4px;
        }
        input[type="submit"] {
            width: 30%;
            background-color: #4CAF50;
            color: white;
            padding: 14px 20px;
            margin: 8px 0;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background-color: #45a049;
        }
    </style>
    <form method="post">
        <label for="url">URL:</label>
        <input type="text" id="url" name="url">
        <input type="submit" value="Download">
    </form>
'''

async def download_website(session, url, project_folder):
    async with session.get(url) as response:
        content_type = response.headers.get('content-type', '')
        extension = guess_extension(content_type)
        filename = os.path.basename(url)
        filepath = os.path.join(project_folder, filename)

        async with aiofiles.open(filepath, mode='wb') as f:
            await f.write(await response.read())

        if extension:
            os.rename(filepath, os.path.splitext(filepath)[0] + extension)


async def download_and_zip_website(url, project_folder):
    async with aiohttp.ClientSession() as session:
        await download_website(session, url, project_folder)

        for subdir, _, files in os.walk(project_folder):
            for file in files:
                filepath = os.path.join(subdir, file)
                new_filepath = os.path.join(subdir, adjust_extension(file, 'html'))
                os.rename(filepath, new_filepath)

        zip_name = str(uuid.uuid4())
        shutil.make_archive(zip_name, 'zip', root_dir=project_folder)

        return zip_name


def adjust_extension(filename, new_extension):
    basename = os.path.basename(filename)
    name, _ = os.path.splitext(basename)
    return f"{name}.{new_extension}"


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        logging.info(f'Index route requested {request.user_agent} {request.remote_user} {request.remote_addr}')

        url = request.form.get('url')
        if not url:
            logging.info(f'not valid url {url}')
            return html + '(Error: URL not provided)'
        os.makedirs("./data")
        project_folder = './data'

        if not os.path.isdir(project_folder):
            return f"Error: {project_folder} is not a valid directory"
        if not os.access(project_folder, os.W_OK):
            return html + f"Error: {project_folder} is not writable"

        zip_name = asyncio.run(download_and_zip_website(url, project_folder))
        return send_file(f'{zip_name}.zip', as_attachment=True, download_name=f'{zip_name}.zip')
    return html


if __name__ == '__main__':
    async def main():

        app.run(host='0.0.0.0')

    loop = asyncio.get_event_loop()
    task = loop.create_task(main())
    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        pass
