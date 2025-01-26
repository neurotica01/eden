"""
Modernized memory module using SQLite and strong typing.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List, Set
import sqlite3
import os
import numpy as np

MemoryType = Literal["event", "thought", "chat"]

@dataclass
class MemoryNode:
    """Core memory unit with strong typing and validation"""
    id: str
    type: MemoryType
    subject: str
    predicate: str
    object: str
    description: str
    embedding: List[float]
    poignancy: float
    keywords: Set[str]
    filling: Optional[List[str]] = None
    created: datetime = datetime.now()
    last_accessed: datetime = datetime.now()
    expiration: Optional[datetime] = None


    def __eq__(self, other):                                                                                                           
        """Allow direct comparison of MemoryNodes"""                                                                                   
        if not isinstance(other, MemoryNode):                                                                                          
            return False                                                                                                               
        return self.id == other.id                                                                                                     
                                                                                                                                        
    def __hash__(self):                                                                                                                
        """Allow MemoryNodes to be used in sets"""                                                                                     
        return hash(self.id)   

    def spo_summary(self): 
      return (self.subject, self.predicate, self.object)


class VectorMemory:
    """SQLite-backed memory storage with vector search capabilities"""
    
    def __init__(self, db_path: str = ":memory:"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = sqlite3.connect(db_path + '/memory.db')
        self._init_schema()
        
    def _init_schema(self):
        """Initialize database schema"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                subject TEXT,
                predicate TEXT,
                object TEXT,
                description TEXT,
                embedding BLOB,
                poignancy REAL,
                keywords TEXT,
                filling TEXT,
                created TIMESTAMP,
                last_accessed TIMESTAMP,
                expiration TIMESTAMP
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS keyword_strengths (
                keyword TEXT,
                strength INTEGER,
                type TEXT,
                PRIMARY KEY (keyword, type)
            )
        """)
        
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_keywords ON memories(keywords)
        """)
        self.db.commit()
        
    def add_memory(self, node: MemoryNode):
        """Store a new memory node"""
        embedding_bytes = np.asarray(node.embedding).tobytes()
        keywords_str = ",".join(node.keywords)
        filling_str = ",".join(node.filling) if node.filling else None
        
        self.db.execute(
            """
            INSERT INTO memories VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                node.id,
                node.type,
                node.subject,
                node.predicate,
                node.object,
                node.description,
                embedding_bytes,
                node.poignancy,
                keywords_str,
                filling_str,
                node.created.isoformat(),
                node.last_accessed.isoformat(),
                node.expiration.isoformat() if node.expiration else None
            )
        )
        self.db.commit()

    
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[MemoryNode]:
        """Semantic search using cosine similarity"""
        # Get all stored embeddings
        cursor = self.db.execute("SELECT id, embedding FROM memories")
        results = []
        
        for row in cursor:
            node_id, embedding_bytes = row
            stored_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            
            # Calculate cosine similarity
            similarity = np.dot(query_embedding, stored_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
            )
            results.append((node_id, similarity))
            
        # Sort by similarity and get top_k
        results.sort(key=lambda x: x[1], reverse=True)
        top_ids = [x[0] for x in results[:top_k]]
        
        # Retrieve full nodes
        return [self.get_node(node_id) for node_id in top_ids]
        
    def get_node(self, node_id: str) -> MemoryNode:
        """Retrieve a memory node by ID"""
        cursor = self.db.execute(
            "SELECT * FROM memories WHERE id = ?", (node_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            raise ValueError(f"Node {node_id} not found")
            
        # Convert SQLite row to MemoryNode
        return MemoryNode(
            id=row[0],
            type=row[1],
            subject=row[2],
            predicate=row[3],
            object=row[4],
            description=row[5],
            embedding=np.frombuffer(row[6], dtype=np.float32).tolist(),
            poignancy=row[7],
            keywords=set(row[8].split(",")) if row[8] else set(),
            filling=row[9].split(",") if row[9] else None,
            created=datetime.fromisoformat(row[10]),
            last_accessed=datetime.fromisoformat(row[11]),
            expiration=datetime.fromisoformat(row[12]) if row[12] else None
        )


    def add_event(self, created, expiration, s, p, o,
                 description, keywords, poignancy,
                 embedding_pair, filling=None):
        """Add an event memory"""
        # Get current counts
        cursor = self.db.execute("SELECT COUNT(*) FROM memories")
        total_count = cursor.fetchone()[0] + 1
        
        cursor = self.db.execute("SELECT COUNT(*) FROM memories WHERE type='event'")
        type_count = cursor.fetchone()[0] + 1
        
        node_id = f"node_{str(total_count)}"
        
        # Clean up description
        if "(" in description:
            description = (" ".join(description.split()[:3]) 
                         + " " 
                         + description.split("(")[-1][:-1])
        
        # Create node
        node = MemoryNode(
            id=node_id,
            type="event",
            subject=s,
            predicate=p,
            object=o,
            description=description,
            embedding=embedding_pair[1],
            poignancy=poignancy,
            keywords=set(k.lower() for k in keywords),
            filling=filling,
            created=created,
            expiration=expiration
        )
        
        # Store in database
        self.add_memory(node)
        
        # Update keyword strengths if not idle
        if f"{p} {o}" != "is idle":
            for kw in node.keywords:
                self.db.execute("""
                    INSERT OR REPLACE INTO keyword_strengths (keyword, strength, type)
                    VALUES (?, COALESCE(
                        (SELECT strength + 1 FROM keyword_strengths 
                         WHERE keyword=? AND type='event'), 1
                    ), 'event')
                """, (kw, kw))
        
        self.db.commit()
        return node


    def add_thought(self, created, expiration, s, p, o,
                   description, keywords, poignancy,
                   embedding_pair, filling=None):
        """Add a thought memory"""
        # Get current counts
        cursor = self.db.execute("SELECT COUNT(*) FROM memories")
        total_count = cursor.fetchone()[0] + 1
        
        cursor = self.db.execute("SELECT COUNT(*) FROM memories WHERE type='thought'")
        type_count = cursor.fetchone()[0] + 1
        
        node_id = f"node_{str(total_count)}"
        
        # Calculate depth
        depth = 1
        if filling:
            # Get max depth of referenced nodes
            placeholders = ','.join('?' * len(filling))
            cursor = self.db.execute(f"""
                SELECT MAX(depth) FROM memories 
                WHERE id IN ({placeholders})
            """, filling)
            max_depth = cursor.fetchone()[0]
            if max_depth is not None:
                depth += max_depth
        
        # Create node
        node = MemoryNode(
            id=node_id,
            type="thought",
            subject=s,
            predicate=p,
            object=o,
            description=description,
            embedding=embedding_pair[1],
            poignancy=poignancy,
            keywords=set(k.lower() for k in keywords),
            filling=filling,
            created=created,
            expiration=expiration
        )
        
        # Store in database
        self.add_memory(node)
        
        # Update keyword strengths if not idle
        if f"{p} {o}" != "is idle":
            for kw in node.keywords:
                self.db.execute("""
                    INSERT OR REPLACE INTO keyword_strengths (keyword, strength, type)
                    VALUES (?, COALESCE(
                        (SELECT strength + 1 FROM keyword_strengths 
                         WHERE keyword=? AND type='thought'), 1
                    ), 'thought')
                """, (kw, kw))
        
        self.db.commit()
        return node


    def add_chat(self, created, expiration, s, p, o,
                 description, keywords, poignancy,
                 embedding_pair, filling=None):
        """Add a chat memory"""
        # Get current counts
        cursor = self.db.execute("SELECT COUNT(*) FROM memories")
        total_count = cursor.fetchone()[0] + 1
        
        cursor = self.db.execute("SELECT COUNT(*) FROM memories WHERE type='chat'")
        type_count = cursor.fetchone()[0] + 1
        
        node_id = f"node_{str(total_count)}"
        
        # Create node
        node = MemoryNode(
            id=node_id,
            type="chat",
            subject=s,
            predicate=p,
            object=o,
            description=description,
            embedding=embedding_pair[1],
            poignancy=poignancy,
            keywords=set(k.lower() for k in keywords),
            filling=filling,
            created=created,
            expiration=expiration
        )
        
        # Store in database
        self.add_memory(node)
        self.db.commit()
        return node


    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using the same model used for storage"""
        from src.persona.prompt_template.gpt_structure import get_embedding
        return get_embedding(text)[1]  # Returns the vector part of the embedding pair
        
    def get_summarized_latest_events(self, retention):
        """Get summaries of the most recent events"""
        cursor = self.db.execute("""
            SELECT subject, predicate, object 
            FROM memories 
            WHERE type = 'event'
            ORDER BY created DESC
            LIMIT ?
        """, (retention,))
        
        return {(row[0], row[1], row[2]) for row in cursor.fetchall()}


    def get_str_seq_events(self):
        """Get string representation of all events"""
        cursor = self.db.execute("""
            SELECT subject, predicate, object, description
            FROM memories 
            WHERE type = 'event'
            ORDER BY created DESC
        """)
        rows = cursor.fetchall()
        
        ret_str = ""
        for count, row in enumerate(rows):
            ret_str += f'{"Event", len(rows) - count, ": ", (row[0], row[1], row[2]), " -- ", row[3]}\n'
        return ret_str


    def get_str_seq_thoughts(self):
        """Get string representation of all thoughts"""
        cursor = self.db.execute("""
            SELECT subject, predicate, object, description
            FROM memories 
            WHERE type = 'thought'
            ORDER BY created DESC
        """)
        rows = cursor.fetchall()
        
        ret_str = ""
        for count, row in enumerate(rows):
            ret_str += f'{"Thought", len(rows) - count, ": ", (row[0], row[1], row[2]), " -- ", row[3]}'
        return ret_str


    def get_str_seq_chats(self):
        """Get string representation of all chats"""
        cursor = self.db.execute("""
            SELECT object, description, created, filling
            FROM memories 
            WHERE type = 'chat'
            ORDER BY created DESC
        """)
        rows = cursor.fetchall()
        
        ret_str = ""
        for row in rows:
            ret_str += f"with {row[0]} ({row[1]})\n"
            created_dt = datetime.fromisoformat(row[2])
            ret_str += f'{created_dt.strftime("%B %d, %Y, %H:%M:%S")}\n'
            if row[3]:  # filling contains the chat messages
                for msg in row[3].split(','):
                    speaker, text = msg.split(':', 1)
                    ret_str += f"{speaker}: {text}\n"
        return ret_str


    def retrieve_relevant_thoughts(self, s_content, p_content, o_content):
        """Retrieve thoughts based on semantic similarity to the query"""
        # Combine the search terms into a single query string
        query = " ".join(filter(None, [s_content, p_content, o_content]))
        if not query:
            return set()
            
        # Get query embedding from the combined text
        query_embedding = self.get_embedding(query)
        
        # Get all thought nodes with their embeddings
        cursor = self.db.execute("""
            SELECT id, embedding FROM memories 
            WHERE type = 'thought'
        """)
        
        results = []
        for row in cursor:
            node_id, embedding_bytes = row
            stored_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            
            # Calculate cosine similarity
            similarity = np.dot(query_embedding, stored_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
            )
            results.append((node_id, similarity))
        
        # Sort by similarity and get top matches (similarity > 0.7)
        results.sort(key=lambda x: x[1], reverse=True)
        relevant_ids = [id for id, sim in results if sim > 0.7]
        
        return {self.get_node(node_id) for node_id in relevant_ids}


    def retrieve_relevant_events(self, s_content, p_content, o_content):
        """Retrieve events based on semantic similarity to the query"""
        # Combine the search terms into a single query string
        query = " ".join(filter(None, [s_content, p_content, o_content]))
        if not query:
            return set()
            
        # Get query embedding from the combined text
        query_embedding = self.get_embedding(query)
        
        # Get all event nodes with their embeddings
        cursor = self.db.execute("""
            SELECT id, embedding FROM memories 
            WHERE type = 'event'
        """)
        
        results = []
        for row in cursor:
            node_id, embedding_bytes = row
            stored_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            
            # Calculate cosine similarity
            similarity = np.dot(query_embedding, stored_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
            )
            results.append((node_id, similarity))
        
        # Sort by similarity and get top matches (similarity > 0.7)
        results.sort(key=lambda x: x[1], reverse=True)
        relevant_ids = [id for id, sim in results if sim > 0.7]
        
        return {self.get_node(node_id) for node_id in relevant_ids}


    def get_last_chat(self, target_persona_name):
        """Get the most recent chat with the target persona"""
        cursor = self.db.execute("""
            SELECT * FROM memories 
            WHERE type = 'chat'
            AND keywords LIKE ?
            ORDER BY created DESC
            LIMIT 1
        """, (f"%{target_persona_name.lower()}%",))
        
        row = cursor.fetchone()
        if not row:
            return False
            
        return self.get_node(row[0])
