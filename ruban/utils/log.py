#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FileName:   log.py
"""

import os
import sys
import json
import logging
from six import string_types
from flask import request
from logging.handlers import TimedRotatingFileHandler

from colorama import Fore, Back, Style
from collections import OrderedDict

from .util import first_or_none, get_program_name, ensure_dir
from ruban.config import APP_NAME


# 默认日志格式
DEFAULT_LOG_FORMAT = '''
%(asctime)s %(levelname) 8s: [%(filename)s:%(lineno)d]
[%(processName)s:%(process)d %(threadName)s] - %(message)s
'''.replace('\n', '').strip()

WEB_LOG_FORMAT = '''
{\"ts\": \"%(asctime)s\", \"proj\": \"%(app_name)s\", \"loglv\": \"%(levelname)s\",
\"fname\": \"%(filename)s\", \"lineno\":\"%(lineno)s\",
\"message\":%(message)s,}
'''.replace('\n', '').replace('%(app_name)s', APP_NAME).strip()

# 默认时间格式
DEFAULT_DATE_FORMAT = '[%Y-%m-%d %H:%M:%S]'


LEVEL_COLOR = {
    logging.DEBUG: Fore.CYAN,
    logging.INFO: Fore.GREEN,
    logging.WARN: Fore.YELLOW,
    logging.ERROR: Fore.RED,
    logging.FATAL: Fore.MAGENTA,
    logging.NOTSET: Fore.BLUE,
}

COLORS = [
    Back.WHITE,
    Fore.RED,
    Fore.GREEN,
    Fore.YELLOW,
    Fore.BLUE,
    Fore.MAGENTA,
    Fore.CYAN,
    Back.RED,
    Back.GREEN,
    Back.YELLOW,
    Back.BLUE,
    Back.MAGENTA,
    Back.CYAN,
]


def web_context(name, default=''):
    try:
        fields = name.split('.')
        value = request
        for field in fields:
            if isinstance(value, dict):
                value = value.get(field)
            else:
                value = getattr(value, field, None)
            if value is None:
                return default
        return value
    except RuntimeError:
        return default


class JsonifiedLogFilter(logging.Filter):

    def filter(self, record):
        # 日志消息
        msg = record.msg

        # 字符串日志
        if isinstance(msg, string_types):
            record.msg = "\"" + record.msg + "\""
            return True

        # 字典日志
        if isinstance(msg, dict):
            record.msg = json.dumps(msg, ensure_ascii=False, default=str)
            record.args = ()
            return True

        if isinstance(msg, (list, tuple)):
            first = first_or_none(msg)
            # 列表日志
            if isinstance(first, (list, tuple)):
                data = OrderedDict(msg)
                record.msg = json.dumps(data, ensure_ascii=False, default=str)
                record.args = ()
                return True

            data = OrderedDict([msg])
            args = record.args
            if args:
                data.update(args)
            record.msg = json.dumps(data, ensure_ascii=False, default=str)
            record.args = ()
            return True

        return True


class LevelFilter(logging.Filter):

    def __init__(self, lower=None, upper=None,
                 lower_included=False,
                 upper_included=False):

        self.lower = lower
        self.upper = upper

        self.lower_included = lower_included
        self.upper_included = upper_included

    def filter(self, record):
        levelno = record.levelno

        if self.lower:
            if levelno < self.lower:
                return False
            if not self.lower_included and levelno == self.lower:
                return False

        if self.upper:
            if levelno > self.upper:
                return False
            if not self.upper_included and levelno == self.upper:
                return False

        return True


class LoggerMaintainer(object):

    log_format = DEFAULT_LOG_FORMAT

    maintainers = {}
    root_logger = logging.getLogger()

    jsonified_log_filter = JsonifiedLogFilter()

    @classmethod
    def create(cls, logger=None, *args, **kwargs):
        if logger is None or logger == logging.getLogger():
            name = None
        elif isinstance(logger, string_types):
            name = logger
        else:
            name = logger.name

        maintainer = cls.maintainers.get(name)
        if maintainer is not None:
            return maintainer

        logger = logging.getLogger(name)
        maintainer = cls.maintainers[name] = LoggerMaintainer(
            logger, *args, **kwargs)
        return maintainer

    @classmethod
    def create_logger(cls, name, *args, **kwargs):
        maintainer = cls.create(name, *args, **kwargs)
        return maintainer.logger

    def __init__(self, logger):
        self.logger = logger
        self.logger.addFilter(self.jsonified_log_filter)
        self.formatter = logging.Formatter(self.log_format)
        self.stdout_handler = None
        self.stderr_handler = None
        self.file_handlers = {}
        for handler in self.logger.handlers:
            handler.setFormatter(self.formatter)

    def add_handler(self, handler):
        handler.setFormatter(self.formatter)
        self.logger.addHandler(handler)

    def add_file_handler(self, path, name, level=None):
        levelname = logging.getLevelName(level) if level is not None \
                else 'DEFAULT'

        filename = '{path}/{name}.{level}.log'.format(
                path=os.path.abspath(path), name=name,
                level=levelname)

        if filename not in self.file_handlers:
            file_handler = TimedRotatingFileHandler(
                filename, when='D', interval=1, backupCount=30, encoding='utf-8', delay=True
            )

            self.file_handlers[filename] = file_handler

            if level is not None:
                file_handler.setLevel(level)

            self.add_handler(file_handler)

    def add_stdout_handler(self, level=None):
        if not self.stdout_handler:
            self.stdout_handler = logging.StreamHandler(sys.stdout)
            self.add_handler(self.stdout_handler)

        self.stdout_handler.setFormatter(self.formatter)
        self.stdout_handler.setLevel(level=level)

    def add_stderr_handler(self, level=None):
        if not self.stderr_handler:
            self.stderr_handler = logging.StreamHandler(sys.stderr)
            self.add_handler(self.stderr_handler)

        self.stderr_handler.setFormatter(self.formatter)
        self.stderr_handler.setLevel(level=level)

    def basic_setup(self, use_stdout=True, use_stderr=True, path=None,
                    filename=None, level=logging.DEBUG, stdout_level=None,
                    stderr_level=logging.ERROR, split_std_stream=True,
                    file_level=None, format=None, reset=True):

        if reset:
            self.stdout_handler = None
            self.file_handlers = {}
            self.logger.handlers = []

        if format:
            self.formatter = logging.Formatter(format)
            for handler in self.logger.handlers:
                handler.setFormatter(self.formatter)

        if stdout_level is None:
            stdout_level = level

        if file_level is None:
            file_level = level

        # 日志级别
        self.logger.setLevel(level)

        # 输出到标准输出
        if use_stdout:
            self.add_stdout_handler(level=stdout_level)

        # 输出到标准出错
        if use_stderr:
            self.add_stderr_handler(level=stderr_level)
            if split_std_stream:
                self.stdout_handler.addFilter(
                    LevelFilter(upper=stderr_level, upper_included=False)
                    )

        program_name = get_program_name() or 'unknown'
        default_name = ('%s-%s' % (program_name, self.logger.name)
                        if self.logger.name else program_name)
        name = filename or default_name

        # 输出到文件
        if path:
            path = os.path.abspath(path)
            ensure_dir(path)
            self.add_file_handler(path, name, level=file_level)

        return self.logger


class FlaskLogFilter(logging.Filter):

    def filter(self, record):
        record.levelcolor = LEVEL_COLOR[record.levelno]
        record.color_reset = Style.RESET_ALL
        record.method = web_context('method')
        record.path = web_context('path')
        record.ip = (web_context('headers.X-Forwarded-For') or
                     web_context('remote_addr'))

        return True


flask_log_filter = FlaskLogFilter()


def get_logger(logger, level=logging.INFO, path=None, filename=None):
    lm = LoggerMaintainer.create(logger)
    lm.logger.addFilter(flask_log_filter)
    lm.logger.propagate = False
    lm.basic_setup(level=level, format=WEB_LOG_FORMAT, path=path,
                   filename=filename)
    return lm.logger
