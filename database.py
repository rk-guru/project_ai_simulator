import os
import json
from sqlalchemy import create_engine, Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DB_FILE = "projects_v2.db"
engine = create_engine(f"sqlite:///{DB_FILE}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="project", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="project", cascade="all, delete-orphan")
    files = relationship("File", back_populates="project", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"))
    role = Column(String)  # 'user' or 'ai'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="messages")

class Simulation(Base):
    __tablename__ = "simulations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"))
    config_json = Column(Text)    # The simulation parameters/nodes/edges
    results_json = Column(Text)   # The result table data
    timestamp = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="simulations")

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"))
    filename = Column(String)
    filepath = Column(String)

    project = relationship("Project", back_populates="files")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
