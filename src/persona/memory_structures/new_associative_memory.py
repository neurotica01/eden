"""
author: @neurotica01
Modernized memory module using SQLite and strong typing.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List, Set
import sqlite3
import os
import numpy as np
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.types import TypeDecorator
from sqlalchemy import text
from sqlalchemy.event import listen
from sqlalchemy import event
import struct
import sqlite_vec

import json
import uuid  # Add this import at the top

# TODO: 
# (1) schema management
# (2) on retreival increase reinforcement
# (3) daily memory decay
# (4) depth / filling management (how to do this?)
# (5) persona tagging
# (6) lowercase everything


# (8) (day two) -> chat as multi-owner large description objects. maybe even copied for simplicity

MemoryType = Literal["event", "thought", "chat"]

Base = declarative_base()

def serialize_f32(vector: List[float]) -> bytes:
    """serializes a list of floats into a compact "raw bytes" format"""
    return struct.pack("%sf" % len(vector), *vector)

def load_extension(dbapi_conn, unused):
    dbapi_conn.enable_load_extension(True)
    sqlite_vec.load_extension(dbapi_conn)
    dbapi_conn.enable_load_extension(False)



class ListType(TypeDecorator):
    """Custom type for handling List fields in SQLAlchemy"""
    impl = String
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)

class MemoryNode(Base):
    """Core memory unit with SQLAlchemy ORM"""
    __tablename__ = 'memories'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False)
    subject = Column(String)
    predicate = Column(String)
    object = Column(String)
    description = Column(String)
    poignancy = Column(Float)
    reinforcement = Column(Float)
    owner = Column(String)
    depth = Column(Integer)
    filling = Column(ListType)
    created = Column(DateTime, default=datetime.now)
    last_accessed = Column(DateTime, default=datetime.now)
    expiration = Column(DateTime, nullable=True)

    def __eq__(self, other):
        if not isinstance(other, MemoryNode):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def spo_summary(self):
        return (self.subject, self.predicate, self.object)

class VectorMemory:
    """SQLAlchemy-backed memory storage with vector search capabilities"""
    
    def __init__(self, db_path: str = ":memory:"):
        if db_path == ":memory:":
            # Handle in-memory database case
            self.engine = create_engine('sqlite:///:memory:')
        else:
            # Treat db_path as the *directory* where the database file will reside
            os.makedirs(db_path, exist_ok=True)  # Create directory if needed
            # Build full path to database file
            db_file = os.path.join(db_path, "memory.db")
            # Correct connection URL (auto-handles absolute/relative paths)
            self.engine = create_engine(f'sqlite:///{db_file}', 
                                      connect_args={'check_same_thread': False})
        
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        # sqlite3.connect


        @event.listens_for(self.engine, "connect")
        def load_extensions(dbapi_connection, connection_record):
            sqlite_vec.load(dbapi_connection)


        # self.engine.raw_connection().enable_load_extension(True)
        # sqlite_vec.load(self.engine)
        # self.engine.raw_connection().enable_load_extension(False)


        self.session = Session()

        self.session.execute(text("""  
            CREATE VIRTUAL TABLE IF NOT EXISTS keyword_strengths using vec0 (
                id text primary key,
                embedding float[1536]
            )
        """))

    def add_memory(self, node: MemoryNode):
        """Store a new memory node using SQLAlchemy session"""

        embedding = self.get_embedding(node.description)

        filling_str = ",".join(node.filling) if node.filling else None
        node.filling = filling_str

        self.session.add(node)
        
        # Add embedding separately since it's in a different table
        self.session.execute(text(""" 
            INSERT INTO keyword_strengths VALUES (?, ?)
        """),
            {"id": node.id, "embedding": embedding}
        )
        
        self.session.commit()

    def get_node(self, node_id: str) -> MemoryNode:
        """Retrieve a single node using SQLAlchemy"""
        node = self.session.query(MemoryNode).filter(MemoryNode.id == node_id).first()
        if not node:
            raise ValueError(f"Node {node_id} not found")
        return node

    def get_nodes(self, node_ids: List[str]) -> List[MemoryNode]:
        """Retrieve multiple nodes using SQLAlchemy"""
        nodes = self.session.query(MemoryNode).filter(MemoryNode.id.in_(node_ids)).all()
        if not nodes:
            raise ValueError(f"Nodes {node_ids} not found")
        return nodes

    def search(self, query_embedding: List[float], type: MemoryType, top_k: int = 5) -> List[MemoryNode]:
        """Semantic search using cosine similarity"""
        # Get all stored embeddings
        cursor = self.session.query(MemoryNode).filter(MemoryNode.type == type).all()

        results = []
        for node in cursor:
            embedding = self.get_embedding(node.description)
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            )
            results.append((node, similarity))

        # Sort by similarity and get top matches (similarity > 0.7)
        results.sort(key=lambda x: x[1], reverse=True)
        top_k_results = [node for node, sim in results if sim > 0.7][:top_k]

        return top_k_results

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using the same model used for storage"""
        from src.persona.prompt_template.gpt_structure import get_embedding
        return get_embedding(text)[1]  # Returns the vector part of the embedding pair
        
    def get_summarized_latest_events(self, retention):
        """Get summaries of the most recent events"""
        cursor = self.session.query(MemoryNode).filter(MemoryNode.type == "event").order_by(MemoryNode.created.desc()).limit(retention).all()
        return {(node.subject, node.predicate, node.object) for node in cursor}

    def get_last_chat(self, target_persona_name):
        """Get the most recent chat with the target persona"""
        cursor = self.session.query(MemoryNode).filter(MemoryNode.type == "chat", MemoryNode.subject.ilike(f"%{target_persona_name.lower()}%")).order_by(MemoryNode.created.desc()).limit(1).all()
        if not cursor:
            return False
        return cursor[0]

    def add_event(self, created, expiration, owner, s, p, o,
                 description, poignancy, filling=None):
        
        if "(" in description:
            description = (" ".join(description.split()[:3]) 
                            + " " 
                            + description.split("(")[-1][:-1])

        node = MemoryNode(
            type="event",
            subject=s,
            predicate=p,
            object=o,
            owner=owner.lower(),
            description=description,
            poignancy=poignancy,
            reinforcement=0,
            depth=0,
            filling=filling,
            created=created,
            expiration=expiration
        )
        
        self.add_memory(node)
        return node


    def add_thought(self, created, expiration, owner, s, p, o,
                   description, poignancy,
                   filling=None):
        """Add a thought memory"""
        
        # Calculate depth ?????
        # depth = 1
        # if filling:
        #     # Get max depth of referenced nodes
        #     placeholders = ','.join('?' * len(filling))
        #     cursor = self.db.execute(f"""
        #         SELECT MAX(depth) FROM memories 
        #         WHERE id IN ({placeholders})
        #     """, filling)
        #     max_depth = cursor.fetchone()[0]
        #     if max_depth is not None:
        #         depth += max_depth
        
        # Create node
        node = MemoryNode(
            type="thought",
            owner=owner.lower(),
            subject=s,
            predicate=p,
            object=o,
            description=description,
            poignancy=poignancy,
            reinforcement=0,
            filling=filling,
            created=created,
            expiration=expiration,
            depth=len(filling) if filling else 0
        )
        
        # Store in database
        self.add_memory(node)
        return node


    def add_chat(self, created, expiration, owner, s, p, o,
                 description, poignancy,
                 filling=None):
        """Add a chat memory"""
        # Create node
        node = MemoryNode(
            type="chat",
            owner=owner.lower(),
            subject=s,
            predicate=p,
            object=o,
            description=description,
            poignancy=poignancy,
            reinforcement=0,
            depth=len(filling) if filling else 0,
            filling=filling,
            created=created,
            expiration=expiration
        )
        
        # Store in database
        self.add_memory(node)
        return node
