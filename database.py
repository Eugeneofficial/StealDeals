from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()

class Genre(Base):
    __tablename__ = 'genres'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    
    def __repr__(self):
        return f"<Genre {self.name}>"

# Таблица связи пользователей и жанров
user_genres = Table(
    'user_genres', 
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genres.id', ondelete='CASCADE'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    notify_sales = Column(Boolean, default=True)
    notify_free = Column(Boolean, default=True)
    min_discount = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь с жанрами
    preferred_genres = relationship('Genre', secondary=user_genres, backref='users')
    
    def __repr__(self):
        return f"<User {self.username}>"

class Game(Base):
    __tablename__ = 'games'
    
    id = Column(Integer, primary_key=True)
    title = Column(String)
    platform = Column(String)  # steam, epic, gog
    store_id = Column(String)
    current_price = Column(Float)
    original_price = Column(Float)
    discount_percent = Column(Integer)
    is_free = Column(Boolean, default=False)
    url = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Game {self.title}>"

# Создание движка базы данных
engine = create_engine(DATABASE_URL)

# Удаляем старые таблицы и создаем новые
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

# Создание сессии
Session = sessionmaker(bind=engine)

def get_session():
    return Session() 