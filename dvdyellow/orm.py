"""
Here will be classes stored in database.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

Database = declarative_base()


class User(Database):
    """
    Stores data for user registration and autorization
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    password = Column(String)


class GameBoard(Database):
    """
    Stores data about game boards
    """
    __tablename__ = 'gameboards'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    author_name = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    shapestring = Column(String)

class GamePawn(Database):
    """
    Stores data about game pawns (also called figures)
    """
    __tablename__ = 'gamepawns'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    author_name = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    shapestring = Column(String)


def create_schemes(engine):
    Database.metadata.create_all(engine)