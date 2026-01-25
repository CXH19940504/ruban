import inspect
import re
import traceback
from sqlalchemy import Date, DateTime, Numeric, create_engine, desc, asc, or_, and_, not_, column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.mysql import insert
from flask import g

from ruban import config
from ruban.utils.log import get_logger
from ruban.utils.util import pop_key_default
from ruban.common import exce


logger = get_logger(__name__)


def get_engine(db=None):
    db = db or getattr(config,
                       'SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')
    echo = True if config.SQL_DEBUG else False
    engine = create_engine(db, echo=echo, pool_recycle=3600)
    return engine


def get_session():
    return g._session


class BaseModel(DeclarativeBase):
    # 中文乱码
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'mysql_charset': 'utf8',
        'mysql_collate': 'utf8_bin',
        'keep_existing': True,
    }
    __json_keys__ = set()

    def as_dict_get_value__(self, attr):
        return getattr(self, attr, None)

    def value_field_output_convert(self, columns, attr, value):
        """
        将资源对象转换为json的格式输出
        """
        try:
            if value is None:
                return value
            ins_type = columns[attr].columns[0].type
            if isinstance(ins_type, DateTime):
                return value.strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(ins_type, (Date, Numeric)):
                return str(value)
        except Exception as e:
            logger.warn("exception e:%r", e)
        return value

    def as_dict(self):
        """
        转换db对象为dict
        """
        ins = inspect(self).mapper
        columns = ins.column_attrs
        dict_data = {}
        for attr in columns.keys():
            value = self.as_dict_get_value__(attr)
            value = self.value_field_output_convert(columns, attr, value)
            dict_data[attr] = value
        return dict_data

    @classmethod
    def get_by_id(cls, id, session=None):
        session = get_session()
        return session.query(cls).get(id)

    @classmethod
    def get_by_key(cls, key):
        if not getattr(cls, '__key_field__', None):
            raise Exception('{} model has no key field'.format(cls.__name__))
        session = get_session()
        return session.query(cls).filter(
            getattr(cls, cls.__key_field__) == key
        ).first()

    @classmethod
    def get_one(cls, key, depth=0):
        obj = cls.get_one_obj(str(key))
        return obj.as_dict(depth)

    @classmethod
    def sort_by(cls, rows, _sort, _direction):
        sort_list = _sort.split(',')
        columns = inspect(cls).mapper.column_attrs
        order_fields = []
        for field in sort_list:
            if field.startswith('-'):
                direction = desc if _direction == 'asc' else asc
                field = field[1:]
            else:
                direction = asc if _direction == 'asc' else desc
            if field not in columns.keys():
                raise exce.ParamsError(msg=u'排序参数%s错误' % field)
            order_fields.append(direction(getattr(cls, field)))
        return rows.order_by(*order_fields)

    @classmethod
    def parse_params_list(cls, data):
        params = {}
        reg = r'^(?P<key>[^\[]+)\[\d+\]$'
        for key, value in data.items():
            kmatch = re.match(reg, key)
            if not kmatch:
                params[key] = value
                continue
            key = kmatch.group('key')
            if key not in params:
                params[key] = []
            else:
                if not isinstance(params[key], (tuple, list)):
                    params[key] = [params[key]]
            params[key].append(value)
        return params

    @classmethod
    def format_filter_params(cls, data):
        filter_ = []
        params = cls.parse_params_list(data)
        reg = r'^(?P<key>.+)__(lt(e)?|gt(e)?|in)$'
        for key, value in params.items():
            if key == 'and':
                and_filter = cls.format_filter_params(value)
                filter_.extend(and_filter)
                continue
            if key == 'or':
                if isinstance(value, dict):
                    or_filter = cls.format_filter_params(value)
                    filter_ = [or_(and_(*filter_), and_(*or_filter))]
                elif isinstance(value, list):
                    or_filter = []
                    for f in value:
                        or_filter.append(*cls.format_filter_params(f))
                    filter_.append(or_(*or_filter))
                continue
            if key == 'not':
                if isinstance(value, dict):
                    not_filter = cls.format_filter_params(value)
                    filter_ = [not_(*not_filter)]
                elif isinstance(value, list):
                    not_filter = []
                    for f in value:
                        not_filter.append(*cls.format_filter_params(f))
                    filter_.append(not_(and_(*not_filter)))
                continue
            kmatch = re.match(reg, key)
            if kmatch:
                key = kmatch.group('key')
            try:
                key_attr = getattr(cls, key)
            except:
                raise exce.ParamsError(
                    msg=u'查询参数%s错误' % key)
            if key.endswith('__lt'):
                filter_.append(key_attr < value)
                continue
            if key.endswith('__lte'):
                filter_.append(key_attr <= value)
                continue
            if key.endswith('__gt'):
                filter_.append(key_attr > value)
                continue
            if key.endswith('__gte'):
                filter_.append(key_attr >= value)
                continue
            if key.endswith('__in'):
                filter_.append(key_attr.in_(value))
                continue
            if isinstance(value, str) and value.startswith('!'):
                value = value[1:]
                fvalue = value
                if not value or value == 'null' or value == 'None':
                    fvalue = None
                filter_.append(key_attr != fvalue)
                continue
            if isinstance(value, dict) and 'like' in value:
                filter_.append(key_attr.like(value['like']))
                continue
            if isinstance(value, int):
                filter_.append(key_attr == value)
                continue
            if not value or value == 'null' or value == 'None':
                filter_.append(key_attr == None)
                continue
            if isinstance(value, dict) and 'in' in value:
                filter_.append(key_attr.in_(value.get('in', [])))
                continue
            if isinstance(value, (tuple, list)):
                filter_.append(key_attr.in_(value))
                continue
            filter_.append(key_attr == value)
        return filter_

    @classmethod
    def get_all(cls, params):
        logger.debug('get_all: %r', params)
        depth = pop_key_default(params, '_expand', 0, int)
        _num = pop_key_default(params, '_num', 10, int)
        _page = pop_key_default(params, '_page', 1, int)
        _direction = pop_key_default(params, '_direction', 'asc', str)
        _sort = pop_key_default(params, '_sort', '')
        _search_key = pop_key_default(params, '_search_key', '', str)

        session = get_session()

        filter_ = cls.format_filter_params(params)
        if _search_key:
            if not getattr(cls, '__search_key__', None):
                raise exce.ParamsError(
                    msg=u'{} model has no search_key'.format(cls.__name__)
                )
            like_filter = []
            for _field in cls.__search_key__:
                like_filter.append(column(_field).like('%'+_search_key+'%'))
            filter_.append(or_(*like_filter))
        rows = session.query(cls).filter(*filter_)

        result = {
            'total': rows.count(),
            'items': []
        }
        if not _sort:
            if hasattr(cls, 'modified'):
                _sort = 'modified'
                _direction = 'desc'
        if _sort:
            # 排序
            rows = cls.sort_by(rows, _sort, _direction)

        logger.debug(str(rows))

        start = (_page - 1) * _num
        end = result['total']
        if _num != -1:
            end = start + _num
        result['items'] = [
            item.as_dict(depth=depth)
            for item in rows[start: end]
        ]
        return result

    @classmethod
    def config_obj_attr(cls, obj, data):
        '''
        :set or update specific object(obj) attributes
        :rtype object
        '''
        ins = inspect(obj).mapper
        columns = ins.column_attrs.keys()
        for col in columns:
            if col in data:
                obj.__setattr__(col, data.get(col))
        return obj

    @classmethod
    def upsert(cls, value, session=None):
        try:
            if session is None:
                session = get_session()
            insert_stmt = insert(cls).values(value)
            on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(value)
            session.execute(on_duplicate_key_stmt)
            session.commit()
        except Exception as e:
            logger.error(
                    "exception:%r, traceback:%r",
                    e, traceback.format_exc())
            raise exce.InterDatabaseError

    @classmethod
    def insert_data(cls, params):
        '''get_engine
        :insert data into table with relationships update
        '''
        try:
            print("添加数据 %s: %s" %(cls.__tablename__, str(params)))
            session = get_session()
            if not isinstance(params, (dict, tuple, list)):
                raise exce.ParamsError(
                    msg=u'参数类型不对，仅支持dict、list、tuple')
            # querydict: key is id and value is the depth
            if isinstance(params, dict):
                params = [params]
            # insert records
            for param in params:
                pret = cls.config_obj_attr(cls(), params)
                session.add(pret)
            session.commit()
        except Exception as e:
            logger.error("e:%r, traceback:%r", e, traceback.print_exc())
            session.rollback()
            raise
        return len(params)

    @classmethod
    def delete_one(cls, key):
        '''
        :delete record
        '''
        try:
            session = get_session()
            obj = cls.get_one_obj(key, session)
            session.delete(obj)
            session.commit()
        except Exception as e:
            logger.error("e:%r, traceback:%r", e, traceback.print_exc())
            session.rollback()
            raise
        return obj.as_dict()

    @classmethod
    def get_one_obj(cls, key, session=None, flag=True):
        '''
        :get object
        '''
        if not session:
            # if session is None, create a new session
            session = get_session()
        filters = {}
        if key.isdigit():
            filters = {'id': key}
        else:
            if not key.startswith('@'):
                raise exce.UrlParamsError()
            key_field = cls.__key_field__
            filters = {key_field: key[1:]}
        obj = session.query(cls).filter_by(**filters).first()
        if not obj:
            raise exce.RecordNotFound(msg='{}({})'.format(cls.__tablename__, key))
        return obj


