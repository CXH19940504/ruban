import configparser
import logging
from typing import Dict, Any
import requests
import json
import time

from requests.adapters import HTTPAdapter
from urllib3 import Retry
from urllib3.exceptions import ResponseError

from digikey_spider.models import BaseMap
from ruban.models.models import Webhook
from ruban import config, get_logger, get_session

alert_logger = get_logger(
    'alert', level=logging.INFO, path=config.LOGGER_PATH, filename='alert')


class WebhookMap(BaseMap):
    item_cls = Webhook
    map_key = 'monitor_status'
    sub_map = None


class ConditionType:

    @classmethod
    def match_value(cls, x0, old_values, *args):
        if old_values is None:
            return True
        elif isinstance(old_values, list):
            return x0 in old_values
        else:
            return x0 == old_values

    @classmethod
    def match(cls, x0, x1, old_value, new_value, *args):
        res = True
        if old_value is not None:
            res = cls.match_value(x0, old_value)
        return res and cls.match_value(x1, new_value)

    @classmethod
    def change_from_to(cls, x0, x1, old_value, new_value, *args):
        if x0 == x1:
            return False
        return cls.match_value(x0, old_value) and cls.match_value(x1, new_value)

    @classmethod
    def increase(cls, x0, x1, old_value, new_value, compare_value):
        if not cls.match_value(x0, old_value) or not cls.match_value(x1, new_value):
            return False
        if not compare_value:
            return x0 < x1
        else:
            return x1 - x0 > compare_value

    @classmethod
    def decrease(cls, x0, x1, old_value, new_value, compare_value):
        if not cls.match_value(x0, old_value) or not cls.match_value(x1, new_value):
            return False
        if not compare_value:
            return x0 > x1
        else:
            return x0 - x1 > compare_value


class Condition:
    """触发条件"""

    def __init__(self, conf):
        self.target_field = conf.get("target_field")  # 监控的字段（last_uantity/status）
        if not self.target_field:
            return
        self.condition_type = conf.get('condition_type')
        self.old_value = self._convert_value(conf.get("old_value"))
        self.new_value = self._convert_value(conf.get("new_value"))
        self.compare_value = self._convert_value(conf.get("compare_value"))

    def _convert_value(self, value: str) -> Any:
        """将配置文件中的字符串值转换为对应类型（int/float/str）"""
        if value is None:
            return None
        if ',' in value:
            return [self._convert_value(v.strip()) for v in value.split(",")]
        else:
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return value

    def is_matched(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> bool:
        """
        判断当前条件是否满足
        :param old_data:
        :param new_data:
        :return:
        """
        # 检查目标字段是否存在于新旧数据中
        if self.target_field not in old_data or self.target_field not in new_data:
            return False
        old_val = old_data[self.target_field]
        new_val = new_data[self.target_field]
        _func = getattr(ConditionType, self.condition_type)
        try:
            return _func(old_val, new_val, self.old_value, self.new_value, self.compare_value)
        except Exception as err:
            alert_logger.error(
                '条件检查异常:%s, %s, %s->%s',
                repr(err), (self.target_field, self.condition_type, self.old_value, self.new_value),
                old_val, new_val)
            return False


class AlertRule:
    """告警规则类，封装单条规则的属性和匹配逻辑"""

    def __init__(self, rule_id: str, conf: Dict[str, str]):
        self.rule_id = rule_id  # 规则ID（如 rule_1）
        self.name = conf["name"].strip()  # 规则名称
        self.description = conf["description"].strip()  # 告警描述
        self.webhook = conf.get("webhook", '').strip()  # webhook
        self.monitor_status = int(conf["monitor_status"].strip())  # 告警类型
        self.conditions = []  # 条件类型
        self.add_condition(conf)
        self.session = self._create_retry_session()

    def _create_retry_session(self):
        """创建带重试 + 连接池的 requests Session"""
        session = requests.Session()
        # 重试策略
        retry_strategy = Retry(
            total=3,  # 总共重试 3 次
            backoff_factor=1,  # 重试间隔：1s → 2s → 4s 指数退避
            allowed_methods=["POST"],  # 允许 POST 重试
            # 需要重试的状态码
            status_forcelist=[429, 500, 502, 503, 504],
            connect=2,  # 连接超时重试次数
            backoff_jitter=3,
            retry_after_max=300
        )
        # 连接池配置（高并发不报错）
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # 连接池数量
            pool_maxsize=100  # 每个域名最大连接数
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def add_condition(self, cond_conf: Dict[str, str]):
        _condition = Condition(cond_conf)
        if _condition.target_field:
            self.conditions.append(_condition)

    def is_triggered(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> bool:
        """
        判断当前规则是否被触发
        :param old_data: 变化前的字段值（如 {"quantity":0, "status":0}）
        :param new_data: 变化后的字段值（如 {"quantity":10, "status":3}）
        :return: 是否触发告警
        """
        if not self.monitor_status == old_data['monitor_status']:
            return False
        for _condition in self.conditions:
            _matched = _condition.is_matched(old_data, new_data)
            if not _matched:
                return False
        return True

    def send_msg(self, msg):
        # Webhook和secret
        # 生成签名（如启用加签）
        if not self.webhook:
            alert_logger.info('发送告警成功：\n%s', msg)
            return
        timestamp = round(time.time() * 1000)
        url = f"{self.webhook}&timestamp={timestamp}"
        # 消息内容
        data = {
            "msgtype": "text",
            "text": {"content": msg},
            "at": {"isAtAll": False}
        }
        # 发送请求
        headers = {"Content-Type": "application/json"}
        try:

            # 使用带连接池的 session 发送
            res = self.session.post(
                url,
                data=json.dumps(data),
                headers=headers,
                timeout=(5, 15)  # 连接超时5s，读取超时15s
            )
            # 处理 429 / 504 等 HTTP 状态码
            if res.status_code == 429 or res.status_code >= 500:
                raise ResponseError(res.status_code)
            data = res.json()
            if data.get('errcode'):
                raise ResponseError(data['errmsg'])
            else:
                alert_logger.info('发送告警成功：%s\n%s', res.status_code, msg)
        except Exception as e:
            alert_logger.error('发送告警失败：%s\n%s', repr(e), msg)
            raise


class AlertTrigger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            _config = configparser.ConfigParser()
            _config.read(config.ALERT_CONF, encoding="utf-8")

            cls._instance.alert_rules = {}
            # 遍历所有规则分段（以 rule_ 开头）
            for section in _config.sections():
                if section.startswith("rule_"):
                    split_con = section.split('|')
                    if len(split_con) == 1:
                        try:
                            rule = AlertRule(section, dict(_config[section]))
                            cls._instance.alert_rules[section] = rule
                        except Exception as e:
                            alert_logger.info(f"{section}配置解析失败：{repr(e)}")
                    else:
                        rule_id = split_con[0]
                        cls._instance.alert_rules[rule_id].add_condition(dict(_config[section]))
            with get_session(False) as db_session:
                rows = db_session.query(Webhook).filter_by(is_deleted=0).all()
                webhook_dict = WebhookMap.get_map(rows)
                for role in cls._instance.alert_rules.values():
                    if not role.webhook and webhook_dict[role.monitor_status]:
                        role.webhook = webhook_dict[role.monitor_status].url

        return cls._instance

    def check_alerts(self, old_data: Dict[str, Any], new_data: Dict[str, Any]):
        """检查所有规则，返回触发的告警列表"""
        for rule in self.alert_rules.values():
            if rule.is_triggered(old_data, new_data):
                alert_logger.info('触发告警：%s, %s -> %s', rule.name, old_data, new_data)
                return rule


alert_trigger = AlertTrigger()
