from sqlalchemy import Integer, String, Date, insert
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Session
from ruban.models.base import BaseModel, get_engine
from flask import g


# 客户端配置模型（对应 dk_client 表）
class DkClient(BaseModel):
    __tablename__ = 'dk_client'
    __key_field__ = 'name'
    __search_key__ = {'name'}

    id = mapped_column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    name = mapped_column(String(255), nullable=False, comment='名称')
    s_name = mapped_column(String(10), nullable=False, unique=True, comment='节点名称')
    client_id = mapped_column(String(50), nullable=False, unique=True, comment='得捷配置')
    client_secret = mapped_column(String(65), nullable=False, comment='得捷配置')
    status = mapped_column(Integer, nullable=False, comment='枚举值client_status')

    
if __name__ == '__main__':
    db = "mysql+pymysql://api_test:APItest123@rm-bp1l6ove2344qcbw5eo.mysql.rds.aliyuncs.com:3306/digikey_db"
    with Session(get_engine(db)) as session:
        ins_stat = insert(DkClient).values(
            name='test1',s_name='s1',client_id="ervghfehorfhuiq",client_secret='afvwefaef',status=1)
        session.execute(ins_stat)
        session.commit()
