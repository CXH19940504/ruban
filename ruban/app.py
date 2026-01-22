#!/usr/bin/env python
# -*- coding=utf-8 -*-

from flask import Flask, g
from sqlalchemy.orm import sessionmaker, scoped_session
from . import config
from .common import exce
from .models import get_engine


app_name = getattr(config, 'APP_NAME', __name__)
app = Flask(app_name)
if config:
    for key in dir(config):
        if not key.startswith('__'):
            app.config[key] = getattr(config, key)


def before_request(*args, **kwargs):
    Session = scoped_session(sessionmaker(bind=get_engine()))
    g._session = Session()


def after_request(response):
    g._session.close()
    return response


def shutdown_session(exception=None):
    """
    请求结束之后，调用session.close归还数据库链接到链接池
    """
    session = getattr(g, '_session', None)
    if session:
        session.close()


def register_site(app):
    app.before_request(before_request)
    app.after_request(after_request)
    app.teardown_appcontext(shutdown_session)

    # 注册app全局的异常处理函数
    app = exce.init_exceptions(app)
    return app


app = register_site(app)
