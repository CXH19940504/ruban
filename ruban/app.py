#!/usr/bin/env python
# -*- coding=utf-8 -*-
import importlib
import pkgutil
import traceback

from flask import Flask, g, Blueprint
from sqlalchemy.orm import sessionmaker, scoped_session
from . import config
from .common import exce
from .models import get_engine


def before_request(*args, **kwargs):
    Session = scoped_session(sessionmaker(bind=get_engine()))
    g._session = Session()


def after_request(response):
    if g._session:
        if response.status_code // 100 == 2:
            g._session.commit()
        else:
            g._session.rollback()
    return response


def shutdown_session(exception=None):
    """
    请求结束之后，调用session.close归还数据库链接到链接池
    """
    session = getattr(g, '_session', None)
    if session:
        session.close()


def register_site(app=None):
    if app is None:
        app = Flask(__name__)
    if config:
        for key in dir(config):
            if not key.startswith('__'):
                app.config[key] = getattr(config, key)
    app.before_request(before_request)
    app.after_request(after_request)
    app.teardown_appcontext(shutdown_session)

    # 注册app全局的异常处理函数
    app = exce.init_exceptions(app)
    return app


def init_blueprints(app, packages):
    for _name in packages:
        _package = __import__(_name, globals(), locals(), ['object'], 0)
        for importer, modname, ispkg in pkgutil.iter_modules(_package.__path__):
            if ispkg:
                continue
            full_modname = '.'.join([_package.__name__, modname])
            try:
                _module = importlib.import_module(full_modname)
                # 遍历模块的所有属性名
                for attr_name in dir(_module):
                    # 获取属性值
                    attr = getattr(_module, attr_name)
                    # 判断是否是Blueprint实例
                    if isinstance(attr, Blueprint):
                        app.register_blueprint(attr)
            except Exception as err:
                print("error:%r, traceback:%r", err, traceback.print_exc())


ruban_app = register_site()
