#!/usr/bin/env python
# -*- coding=utf-8 -*-

"""
封装通用的异常处理
"""


import traceback
import http.client as httplib
from flask import jsonify
from werkzeug.exceptions import HTTPException
from common.exception import RestException, register_exception
from ruban import logger

ERR_UNKNOWN = 10000


@register_exception(400, 40001, u'Request Params Error: {msg}')
class ParamsError(RestException):
    pass


@register_exception(400, 40002, u'Request Params Required: {field}')
class ParamsRequired(RestException):
    pass


@register_exception(400, 40003, u'请求字段类型错误：{field}')
class ParamsFormatError(RestException):
    pass


@register_exception(400, 40004, u'请求字段提供的值无效：{field}')
class ParamsInvalidate(RestException):
    pass


@register_exception(400, 40006, u'url中包含的参数格式错误')
class UrlParamsError(RestException):
    pass


@register_exception(400, 40008, u'数据库内部错误：{msg}')
class InterDatabaseError(RestException):
    pass


@register_exception(400, 40009, u'不存在该可视化数据：{msg}')
class TSDBMissing(RestException):
    pass


@register_exception(400, 40010, u'调用API操作失败：{msg}')
class APIFailed(RestException):
    pass


@register_exception(400, 40012, u'Request params not match table columns')
class ParamsNoMathTable(RestException):
    pass


@register_exception(400, 40013, u'已经存在该关系的绑定')
class AlreadyExistRelationship(RestException):
    pass


@register_exception(404, 40402, u'请求的数据表不存在')
class NotExistTable(RestException):
    pass


@register_exception(404, 40404, u'不存在该记录：{msg}')
class RecordNotFound(RestException):
    pass


@register_exception(409, 40901, u'数据库记录重复：{msg}')
class ExistSameRecord(RestException):
    pass


@register_exception(500, 50001, u'Undefined Exception')
class InterException(RestException):
    pass


@register_exception(500, 50002, u'服务端发生未知错误')
class InterUnknownException(RestException):
    pass


def make_error_response(code=ERR_UNKNOWN, msg='Undefined Exception',
                        detail=None, request=None,
                        http_code=httplib.INTERNAL_SERVER_ERROR):
    response = jsonify({
        'code': code,
        'msg': msg,
        'request': request,
        'detail': detail
    })
    response.status_code = http_code
    return response


def init_exceptions(app):
    '''全局错误处理策略，在app中所有错误处理时效下，进行处理，注册到app下

        flask容易主动抛出的http错误：
            httplib.NOT_FOUND
            httplib.INTERNAL_SERVER_ERROR
        通用http错误处理：
            httplib.HTTPException
        devrest错误处理：
            httplib.DevExce
        通用RestException处理：
            RestException
        其他Python抛出的Exception处理：
            Exception
    '''

    @app.errorhandler(httplib.NOT_FOUND)
    def handle_not_found_error(error):
        logger.error('app handling unknown http not found: %s' % error)
        logger.error(traceback.format_exc())
        response = make_error_response(
            code=ERR_UNKNOWN,
            msg='http not found exception',
            http_code=httplib.NOT_FOUND)
        return response

    @app.errorhandler(httplib.INTERNAL_SERVER_ERROR)
    def handle_internal_server_error(error):
        logger.error('app handling unknown http internal error: %s' % error)
        logger.error(traceback.format_exc())
        response = make_error_response(
            code=ERR_UNKNOWN,
            msg='http intrenal server exception',
            http_code=httplib.INTERNAL_SERVER_ERROR
        )
        return response

    @app.errorhandler(HTTPException)
    def handle_abstract_http_exceptions(error):
        logger.error('app handling unknown http exception: %s' % error)
        logger.error(traceback.format_exc())
        response = make_error_response(
            code=ERR_UNKNOWN, msg='http exception',
            http_code=httplib.INTERNAL_SERVER_ERROR
        )
        return response

    @app.errorhandler(RestException)
    def handle_rest_exceptions(error):
        error_dict = error.to_dict()
        logger.error('exception: %s' % error_dict.get('msg'))
        return make_error_response(
            code=error_dict.get('code'),
            msg=error_dict.get('msg'),
            http_code=error_dict.get('status_code', 500)
        )

    @app.errorhandler(Exception)
    def handle_abstract_exceptions(error):
        logger.error('app handling unknown exception: %s' % error)
        logger.error(traceback.format_exc())
        return make_error_response()

    return app
