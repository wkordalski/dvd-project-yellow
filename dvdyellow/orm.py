"""
Here will be classes stored in database.
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, ForeignKey

Database = declarative_base()


class User(Database):
    """
    Stores data for user registration and autorization
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    password = Column(String)
    ranking = Column(Float)


class GameResult(Database):
    """
    Stores data about finished games
    """
    __tablename__ = "gameresults"
    id = Column(Integer, primary_key=True)
    player1 = Column(Integer, ForeignKey(User.id))
    points1 = Column (Float)
    player2 = Column(Integer, ForeignKey(User.id))
    points2 = Column (Float)
    winner = Column(Integer)


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