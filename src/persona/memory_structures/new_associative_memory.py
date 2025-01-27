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

# TODO: 
# (1) schema management
# (2) ORM
# (3) on retreival increase reinforcement
# (4) daily memory decay
# (5) depth / filling management (how to do this?)
# (6) persona tagging
# (7) lowercase everything


# (8) (day two) -> chat as multi-owner large description objects. maybe even copied for simplicity

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
    poignancy: float
    reinforcement: float
    depth: int
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
                id TEXT PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                owner TEXT,
                subject TEXT,
                predicate TEXT,
                object TEXT,
                description TEXT,
                poignancy REAL,
                reinforcement REAL,
                filling TEXT,
                created TIMESTAMP,
                last_accessed TIMESTAMP,
                expiration TIMESTAMP
            )
        """)

        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_owner ON memories(owner)
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS keyword_strengths using vector(
                id text primary key,
                embedding vector(1536)
            )
        """)

        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)
        """)
        self.db.commit()
    
    def search(self, query_embedding: List[float], type: MemoryType, top_k: int = 5) -> List[MemoryNode]:
        """Semantic search using cosine similarity"""
        # Get all stored embeddings
        cursor = self.db.execute("""
            select rowid, distance
            from keyword_strengths
            where embedding match ?
            and (type is NULL or type = ?)
            order by distance
            limit ?;
        """, (query_embedding, top_k))

        top_k_ids = [row[0] for row in cursor.fetchall()]

        # Retrieve full nodes
        return self.get_nodes(top_k_ids)

    def get_node(self, node_id: str) -> MemoryNode:
        nodes = self.get_nodes([node_id])
        if not nodes:
            raise ValueError(f"Node {node_id} not found")
        return nodes[0]
        
    def get_nodes(self, node_ids: List[str]) -> List[MemoryNode]:
        """Retrieve a memory node by ID"""
        cursor = self.db.execute(
            "SELECT * FROM memories WHERE id IN (?)", (node_ids,)
        )
        rows = cursor.fetchall()
        
        if not rows:
            raise ValueError(f"Node {node_ids} not found")
            
        res = []
        for row in rows:
            # Convert SQLite row to MemoryNode
            res.append(MemoryNode(
                id=row[0],
            type=row[1],
            subject=row[2],
            predicate=row[3],
            object=row[4],
            description=row[5],
            poignancy=row[7],
            reinforcement=row[8],
            filling=row[9].split(",") if row[9] else None,
            created=datetime.fromisoformat(row[10]),
            last_accessed=datetime.fromisoformat(row[11]),
                expiration=datetime.fromisoformat(row[12]) if row[12] else None
                ))
        return res

    def add_memory(self, node: MemoryNode, embedding: List[float]):
        """Store a new memory node"""
   
        filling_str = ",".join(node.filling) if node.filling else None
        
        self.db.execute(
            """
            INSERT INTO memories VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                node.id, # I want auto incrementing ids, how do i do this?
                node.type,
                node.subject,
                node.predicate,
                node.object,
                node.description,
                node.poignancy,
                node.reinforcement,
                filling_str,
                node.created.isoformat(),
                node.last_accessed.isoformat(),
                node.expiration.isoformat() if node.expiration else None
            )
        )

        self.db.execute("""
            INSERT INTO keyword_strengths VALUES (?, ?)
        """, (self.db.lastrowid, embedding))

        self.db.commit()

    def add_event(self, created, expiration, owner, s, p, o,
                 description, poignancy,
                 embedding_pair, filling=None):
        
        if "(" in description:
            description = (" ".join(description.split()[:3]) 
                              + " " 
                              + description.split("(")[-1][:-1])

        node = MemoryNode(
            id=node_id,
            type="event",
            owner=owner.lower(),
            subject=s,
            predicate=p,
            object=o,
            description=description,
            poignancy=poignancy,
            reinforcement=0,
            depth=0,
            filling=filling,
            created=created,
            expiration=expiration
        )
        
        # Store in database
        self.add_memory(node, embedding=embedding_pair[1])
        self.db.commit()
        return node


    def add_thought(self, created, expiration, owner, s, p, o,
                   description, poignancy,
                   embedding_pair, filling=None):
        """Add a thought memory"""
        
        # Calculate depth ?????
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
            depth=depth
        )
        
        # Store in database
        self.add_memory(node, embedding=embedding_pair[1])
        self.db.commit()
        return node


    def add_chat(self, created, expiration, owner, s, p, o,
                 description, poignancy,
                 embedding_pair, filling=None):
        """Add a chat memory"""
        # Get current counts

        
        # Create node
        node = MemoryNode(
            id=node_id,
            type="chat",
            owner=owner.lower(),
            subject=s,
            predicate=p,
            object=o,
            description=description,
            poignancy=poignancy,
            reinforcement=0,
            depth=0,
            filling=filling,
            created=created,
            expiration=expiration
        )
        
        # Store in database
        self.add_memory(node, embedding=embedding_pair[1])
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

    # TODO fix
    def get_last_chat(self, target_persona_name):
        """Get the most recent chat with the target persona"""
        cursor = self.db.execute("""
            SELECT * FROM memories 
            WHERE type = 'chat' 
            AND owner = ?
            ORDER BY created DESC
            LIMIT 1
        """, (f"%{target_persona_name.lower()}%",))
        
        row = cursor.fetchone()
        if not row:
            return False
            
        return self.get_node(row[0])


    # def get_str_seq_events(self):
    #     """Get string representation of all events"""
    #     cursor = self.db.execute("""
    #         SELECT subject, predicate, object, description
    #         FROM memories 
    #         WHERE type = 'event'
    #         ORDER BY created DESC
    #     """)
    #     rows = cursor.fetchall()
        
    #     ret_str = ""
    #     for count, row in enumerate(rows):
    #         ret_str += f'{"Event", len(rows) - count, ": ", (row[0], row[1], row[2]), " -- ", row[3]}\n'
    #     return ret_str


    # def get_str_seq_thoughts(self):
    #     """Get string representation of all thoughts"""
    #     cursor = self.db.execute("""
    #         SELECT subject, predicate, object, description
    #         FROM memories 
    #         WHERE type = 'thought'
    #         ORDER BY created DESC
    #     """)
    #     rows = cursor.fetchall()
        
    #     ret_str = ""
    #     for count, row in enumerate(rows):
    #         ret_str += f'{"Thought", len(rows) - count, ": ", (row[0], row[1], row[2]), " -- ", row[3]}'
    #     return ret_str


    # def get_str_seq_chats(self):
    #     """Get string representation of all chats"""
    #     cursor = self.db.execute("""
    #         SELECT object, description, created, filling
    #         FROM memories 
    #         WHERE type = 'chat'
    #         ORDER BY created DESC
    #     """)
    #     rows = cursor.fetchall()
        
    #     ret_str = ""
    #     for row in rows:
    #         ret_str += f"with {row[0]} ({row[1]})\n"
    #         created_dt = datetime.fromisoformat(row[2])
    #         ret_str += f'{created_dt.strftime("%B %d, %Y, %H:%M:%S")}\n'
    #         if row[3]:  # filling contains the chat messages
    #             for msg in row[3].split(','):
    #                 speaker, text = msg.split(':', 1)
    #                 ret_str += f"{speaker}: {text}\n"
    #     return ret_str


    # def retrieve_relevant_thoughts(self, s_content, p_content, o_content):
    #     """Retrieve thoughts based on semantic similarity to the query"""
    #     # Combine the search terms into a single query string
    #     query = " ".join(filter(None, [s_content, p_content, o_content]))
    #     if not query:
    #         return set()
            
    #     # Get query embedding from the combined text
    #     query_embedding = self.get_embedding(query)
        
    #     # Get all thought nodes with their embeddings
    #     cursor = self.db.execute("""
    #         SELECT id, embedding FROM memories 
    #         WHERE type = 'thought'
    #     """)
        
    #     results = []
    #     for row in cursor:
    #         node_id, embedding_bytes = row
    #         stored_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            
    #         # Calculate cosine similarity
    #         similarity = np.dot(query_embedding, stored_embedding) / (
    #             np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
    #         )
    #         results.append((node_id, similarity))
        
    #     # Sort by similarity and get top matches (similarity > 0.7)
    #     results.sort(key=lambda x: x[1], reverse=True)
    #     relevant_ids = [id for id, sim in results if sim > 0.7]
        
    #     return {self.get_node(node_id) for node_id in relevant_ids}


    # def retrieve_relevant_events(self, s_content, p_content, o_content):
    #     """Retrieve events based on semantic similarity to the query"""
    #     # Combine the search terms into a single query string
    #     query = " ".join(filter(None, [s_content, p_content, o_content]))
    #     if not query:
    #         return set()
            
    #     # Get query embedding from the combined text
    #     query_embedding = self.get_embedding(query)
        
    #     # Get all event nodes with their embeddings
    #     cursor = self.db.execute("""
    #         SELECT id, embedding FROM memories 
    #         WHERE type = 'event'
    #     """)
        
    #     results = []
    #     for row in cursor:
    #         node_id, embedding_bytes = row
    #         stored_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            
    #         # Calculate cosine similarity
    #         similarity = np.dot(query_embedding, stored_embedding) / (
    #             np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
    #         )
    #         results.append((node_id, similarity))
        
    #     # Sort by similarity and get top matches (similarity > 0.7)
    #     results.sort(key=lambda x: x[1], reverse=True)
    #     relevant_ids = [id for id, sim in results if sim > 0.7]
        
    #     return {self.get_node(node_id) for node_id in relevant_ids}
