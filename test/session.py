from sqlalchemy import create_engine, text, URL
from sqlalchemy.orm import Session
from config import SQLALCHEMY_DATABASE_URI

# an Engine, which the Session will use for connection
# resources
engine = create_engine(SQLALCHEMY_DATABASE_URI)

# create session and add objects
with Session(engine) as session:
    res = session.execute(text("select * from dk_client"))
    session.commit()
    print(res)
