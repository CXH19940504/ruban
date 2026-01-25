from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from ruban.config import SQLALCHEMY_DATABASE_URI

SQLALCHEMY_DATABASE_URI = "mysql+pymysql://api_test:APItest123@rm-bp1l6ove2344qcbw5eo.mysql.rds.aliyuncs.com:3306/digikey_db"
# an Engine, which the Session will use for connection
# resources
engine = create_engine(SQLALCHEMY_DATABASE_URI)

# create session and add objects
with Session(engine) as session:
    res = session.execute(text("select * from api_conf"))
    session.commit()
    print(res)
