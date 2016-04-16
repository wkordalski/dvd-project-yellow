"""
Here will be classes stored in database.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

Database = declarative_base()


class User(Database):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    fullname = Column(String)
    password = Column(String)
