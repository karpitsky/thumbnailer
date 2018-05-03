#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import magic
import os
import ssl
import subprocess
import uuid

import flask
import requests
from PIL import Image


app = flask.Flask(__name__)


def resize_image(data):
    final_size = 640

    im = Image.open(io.BytesIO(data))
    if im.mode not in ('L', 'RGB'):
        im = im.convert('RGB')

    src_width, src_height = im.size
    if src_width > src_height:
        position_x = float(src_width) / 2 - float(src_height) / 2
        position_y = 0
        new_size = src_height
    else:
        position_x = 0
        position_y = float(src_height) / 2 - float(src_width) / 2
        new_size = src_width
    im = im.crop((
        int(position_x),
        int(position_y),
        int(position_x + new_size),
        int(position_y + new_size)
    ))
    im = im.resize((final_size, final_size), Image.ANTIALIAS)

    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=100)
    return buf.getvalue()


def video_thumbnail(data):
    file_path = os.path.join('/tmp', uuid.uuid4().hex)
    video_file_path = '{}.mp4'.format(file_path)
    image_file_path = '{}.jpg'.format(file_path)
    f = open(video_file_path, 'wb')
    f.write(data)
    f.close()

    cmd = ['ffmpeg', '-i', video_file_path, '-ss', '1', '-f', 'image2', '-vframes', '1', '-y', image_file_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    proc.wait()
    if proc.returncode:
        os.remove(video_file_path)
        raise Exception('Can\'t save a preview')
    data = open(image_file_path, 'rb').read()
    os.remove(video_file_path)
    os.remove(image_file_path)
    return data


@app.route('/')
def thumbnail():
    url = flask.request.args.get('url')
    if not url:
        return '`url` param is required', 400
    try:
        data = requests.get(url)
        if data.status_code != 200:
            return data.content, 400
        data = data.content
    except (requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
            requests.exceptions.TooManyRedirects,
            requests.exceptions.ChunkedEncodingError,
            ssl.SSLError) as ex:
        return str(ex), 400

    mimetype = magic.from_buffer(data[:1024], mime=True)
    if 'image' in mimetype:
        image = resize_image(data)
    elif 'video' in mimetype:
        try:
            image = video_thumbnail(data)
        except Exception as ex:
            return str(ex), 400
        image = resize_image(image)
    else:
        return 'The file from the url is not an image or video', 400
    return flask.send_file(io.BytesIO(image), mimetype='image/jpeg')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
