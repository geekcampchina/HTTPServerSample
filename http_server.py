#!/usr/bin/env python3

# -*- coding: utf-8 -*-

import inspect
import socketserver
from lib.util import request_msg_parse
from lib.common import MIME_TYPES
from lib.common import config
from happy_utils import HappyLog
from pathlib import Path

_hlog = HappyLog.get_instance('')


class MyTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        func_name = inspect.stack()[0][3]
        _hlog.enter_func(func_name)

        # 如果不执行recv()函数，sendall()函数不会自动分包传输，每个包总大小65k。此时，需要手动根据总大小计算分包个数。
        # 如果执行任意一次recv()函数，sendall()函数可以自动分包，调用sendall()就能发送所有数据（自动分包）。
        recv_data = self.request.recv(1024).strip()
        recv_data = str(recv_data, encoding='ascii')
        _hlog.var('recv_data', recv_data.replace('\r', ''))

        if not recv_data:
            return

        request_info = request_msg_parse(recv_data)

        url = request_info['url']

        filename = Path(config.index_page) if url == '/' or url == '' else Path(url[1:])
        file_abs_path = Path(config.web_root) / filename

        data_len = 0
        bin_data = b''

        if file_abs_path.exists():
            with open(file_abs_path, 'rb') as f:
                bin_data = f.read()

            data_len = len(bin_data)
            code = 200
            code_message = 'OK'
        else:
            code = 404
            code_message = 'Not Found'

        file_ext = filename.suffix

        if len(file_ext) > 0 and file_ext[0] == '.':
            file_ext = file_ext[1:]

        _hlog.var('file_ext', file_ext)

        mime_type = MIME_TYPES[file_ext] if file_ext in MIME_TYPES else config.default_type
        _hlog.var('mime_type', mime_type)

        response_message = \
            "HTTP/1.1 %d %s\r\n" \
            "Content-Type: %s\r\n" \
            "Content-Length: %d\r\n" \
            "Server: nginx\r\n" \
            "Accept-Ranges: bytes\r\n" \
            "\r\n" % (code, code_message, mime_type, data_len)

        _hlog.var('response_message', response_message.replace('\r', ''))

        response_message = bytes(response_message, encoding='ascii')
        response_message += bin_data
        # 方式一：recv() + sendall() 一次性发送
        self.request.sendall(response_message)

        # 方式二：手动计算分包
        # data_len = len(response_message)
        # fix_size = 65 * 1024
        # total_packet_size = int(data_len / fix_size)
        # total_packet_other = data_len % fix_size
        #
        # print('data_len=%d' % data_len)
        # print('total_packet_size=%d' % total_packet_size)
        # print('total_packet_other=%d' % total_packet_other)
        #
        # last_send_size = 0
        # n = 0
        # while True:
        #     n += 1
        #     current_send_size = last_send_size + fix_size
        #     print('A:n=%d, total_packet_size=%s' % (n, total_packet_size))
        #     print('B:last_send_size=%d, current_send_size=%s' % (last_send_size, current_send_size))
        #     self.request.send(response_message[last_send_size: current_send_size])
        #     last_send_size = current_send_size
        #
        #     if n == total_packet_size:
        #         break
        #
        # self.request.send(response_message[last_send_size: last_send_size + total_packet_other])
        # print('最后字节：%d' % (last_send_size + total_packet_other))


if __name__ == "__main__":
    HOST, PORT = config.listen, config.port

    # TCP端口复用
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer((HOST, PORT), MyTCPHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
