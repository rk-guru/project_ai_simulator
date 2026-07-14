from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()


class Project(Base):
    __tablename__ = 'projects'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    nodes = relationship("Node", back_populates="project", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="project", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")
    results = relationship("SimulationResult", back_populates="project", cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="project", cascade="all, delete-orphan")


class Node(Base):
    __tablename__ = 'nodes'

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False)
    type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    x = Column(Float, default=0)
    y = Column(Float, default=0)
    properties = Column(JSON, default=dict)

    project = relationship("Project", back_populates="nodes")


class Edge(Base):
    __tablename__ = 'edges'

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False)
    from_node = Column(String(36), nullable=False)
    to_node = Column(String(36), nullable=False)

    project = relationship("Project", back_populates="edges")


class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(String(36), primary_key=True)
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False)
    sender = Column(String(10), nullable=False)  # 'user' or 'ai'
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="messages")


class SimulationResult(Base):
    __tablename__ = 'simulation_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False)
    parameter = Column(String(255), nullable=False)
    value = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="results")


class UploadedFile(Base):
    __tablename__ = 'uploaded_files'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="uploaded_files")


class Chemical(Base):
    __tablename__ = 'chemicals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    formula = Column(String(100))
    cas_number = Column(String(50))
    molecular_weight = Column(Float)


# Database initialization
def init_db(db_url='sqlite:///chemical_sim.db'):
    engine = create_engine(db_url, echo=True)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()
