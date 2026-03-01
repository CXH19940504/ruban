from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.orm import mapped_column

from ruban.models import BaseModel


# 厂商模型（对应 webhook 表）
class Webhook(BaseModel):
    __tablename__ = 'webhook'
    __key_field__ = 'id'

    id = mapped_column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    name = mapped_column(String(25), nullable=False, unique=True, comment='名称')
    url = mapped_column(String(255), nullable=False, comment='地址')
    monitor_status = mapped_column(Integer, nullable=False, comment='监控类型，0:粗略监控，2:精细监控，3:运维监控')
    update_time = mapped_column(DateTime, nullable=True, comment='更新时间')
    is_deleted = mapped_column(Boolean, nullable=False, default=False, comment='是否删除(0-未删,1-已删)')
