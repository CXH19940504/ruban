#!/usr/bin/env python
# -*- coding=utf-8 -*-

"""
封装通用的异常处理
"""

import sys
import inspect
import traceback
import re
from flask import request
# from code import logger

MSG_FORMAT = {
    10000: u'Undefined Exception',
    10001: u'Database Execution Error',
    11000: u'Collection {collection} not exists.',
    11003: u'Database Connection Error.',
    21001: u"Relation Resource Depend Other.",
}

CHINESE_MSG = {
    10000: u'未知错误。',
    10001: u'数据库执行错误。',
    11000: u'资源表不存在。',
    11003: u'数据库连接异常。',
    21001: u"删除的资源被依赖。",
}

HTTP_STATUS_CODE = {
    400: [
        10001,
        21001,
    ],
    403: [
        30003,
        30004,
        30005,
    ],
    404: [
        11000,
    ],
    500: [
        10000,
        11003,
    ]
}

__http_status_code_mapper__ = {}
for __key__, __value__ in HTTP_STATUS_CODE.items():
    for __item__ in __value__:
        __http_status_code_mapper__[__item__] = __key__
HTTP_STATUS_CODE = __http_status_code_mapper__

NoneType = type(None)

BASE_TYPES = (int, float, str, NoneType)


class RestException(Exception):
    default_code = 10000
    default_logger_level = 'info'

    def __init__(self, code=None, **kwargs):
        self.code = code or self.default_code
        try:
            # 获取调用记录
            list_stack = inspect.stack()
            # 取得上一层调用frame
            last_stack = list_stack[1]
            var_iter = last_stack[0].f_locals.items()
        except:
            var_iter = {}
        self.msg_kwargs = {key: value for key, value in var_iter
                           if isinstance(value, BASE_TYPES)}
        self.msg_kwargs.update(kwargs)
        self.traceback_format_exc = traceback.format_exc()
        try:
            self.source_exp = sys.exc_info()[1]
        except:
            pass

    def to_dict(self):
        """
        异常信息转换为dict
        """
        dict_ = {
            'status_code': self.status_code,
            'code': self.code,
            'msg': self.format_msg(),  # 错误信息
            'request': self.format_request(),  # 请求参数
            'detail': self.detail()   # 用户自定义返回信息
        }
        return dict_

    def format_msg(self):
        """
        异常消息格式化
        """
        fm = MSG_FORMAT.get(self.code, MSG_FORMAT[10000])
        msg_dict = {key: u'' for key in re.findall('{(\w+)}', fm)}
        msg_dict.update(self.msg_kwargs)
        self.message = msg = fm.format(**msg_dict)
        return msg

    @staticmethod
    def format_request():
        result = {}
        try:
            # 格式化url
            start_pox = request.url.find('://')
            if start_pox == -1:
                start_pox = 0
            else:
                start_pox += 3
            uri = request.url
            if uri.find('/', start_pox) != -1:
                uri = uri[uri.find('/', start_pox):]
            result = {
                'method': request.method,
                'req_data': request.data,
                'uri': uri,
            }
        except:
            pass
        return result

    def detail(self):
        return {}


def register_exception(status_code, code, tpl, logger_level='info'):
    """
    注册异常
    param status_code: http 状态码
    param code: 异常代码
    param tpl： 异常信息模板
    param logger_level: 异常信息logger级别
    """
    HTTP_STATUS_CODE[code] = status_code
    MSG_FORMAT[code] = tpl

    def wrapper_class(original_class):
        # 不允许更改异常基类
        assert original_class != RestException
        setattr(original_class, 'default_code', code)
        setattr(original_class, 'default_logger_level', logger_level)
        setattr(original_class, 'status_code', status_code)
        return original_class

    return wrapper_class
