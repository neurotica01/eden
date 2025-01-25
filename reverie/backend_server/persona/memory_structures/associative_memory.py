"""
Modernized memory module using SQLite and strong typing.

Author: Joon Sung Park (joonspk@stanford.edu)
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List, Set
import sqlite3
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


  def spo_summary(self): 
    return (self.subject, self.predicate, self.object)


class VectorMemory:
    """SQLite-backed memory storage with vector search capabilities"""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db = sqlite3.connect(db_path)
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
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)
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
                      embedding_pair, filling):
    # Setting up the node ID and counts.
    node_count = len(self.id_to_node.keys()) + 1
    type_count = len(self.seq_event) + 1
    node_type = "event"
    node_id = f"node_{str(node_count)}"
    depth = 0

    # Node type specific clean up. 
    if "(" in description: 
      description = (" ".join(description.split()[:3]) 
                     + " " 
                     +  description.split("(")[-1][:-1])

    # Creating the <ConceptNode> object.
    node = ConceptNode(node_id, node_count, type_count, node_type, depth,
                       created, expiration, 
                       s, p, o, 
                       description, embedding_pair[0], 
                       poignancy, keywords, filling)

    # Creating various dictionary cache for fast access. 
    self.seq_event[0:0] = [node]
    keywords = [i.lower() for i in keywords]
    for kw in keywords: 
      if kw in self.kw_to_event: 
        self.kw_to_event[kw][0:0] = [node]
      else: 
        self.kw_to_event[kw] = [node]
    self.id_to_node[node_id] = node 

    # Adding in the kw_strength
    if f"{p} {o}" != "is idle":  
      for kw in keywords: 
        if kw in self.kw_strength_event: 
          self.kw_strength_event[kw] += 1
        else: 
          self.kw_strength_event[kw] = 1

    self.embeddings[embedding_pair[0]] = embedding_pair[1]

    return node


  def add_thought(self, created, expiration, s, p, o, 
                        description, keywords, poignancy, 
                        embedding_pair, filling):
    # Setting up the node ID and counts.
    node_count = len(self.id_to_node.keys()) + 1
    type_count = len(self.seq_thought) + 1
    node_type = "thought"
    node_id = f"node_{str(node_count)}"
    depth = 1 
    try: 
      if filling: 
        depth += max([self.id_to_node[i].depth for i in filling])
    except: 
      pass

    # Creating the <ConceptNode> object.
    node = ConceptNode(node_id, node_count, type_count, node_type, depth,
                       created, expiration, 
                       s, p, o, 
                       description, embedding_pair[0], poignancy, keywords, filling)

    # Creating various dictionary cache for fast access. 
    self.seq_thought[0:0] = [node]
    keywords = [i.lower() for i in keywords]
    for kw in keywords: 
      if kw in self.kw_to_thought: 
        self.kw_to_thought[kw][0:0] = [node]
      else: 
        self.kw_to_thought[kw] = [node]
    self.id_to_node[node_id] = node 

    # Adding in the kw_strength
    if f"{p} {o}" != "is idle":  
      for kw in keywords: 
        if kw in self.kw_strength_thought: 
          self.kw_strength_thought[kw] += 1
        else: 
          self.kw_strength_thought[kw] = 1

    self.embeddings[embedding_pair[0]] = embedding_pair[1]

    return node


  def add_chat(self, created, expiration, s, p, o, 
                     description, keywords, poignancy, 
                     embedding_pair, filling): 
    # Setting up the node ID and counts.
    node_count = len(self.id_to_node.keys()) + 1
    type_count = len(self.seq_chat) + 1
    node_type = "chat"
    node_id = f"node_{str(node_count)}"
    depth = 0

    # Creating the <ConceptNode> object.
    node = ConceptNode(node_id, node_count, type_count, node_type, depth,
                       created, expiration, 
                       s, p, o, 
                       description, embedding_pair[0], poignancy, keywords, filling)

    # Creating various dictionary cache for fast access. 
    self.seq_chat[0:0] = [node]
    keywords = [i.lower() for i in keywords]
    for kw in keywords: 
      if kw in self.kw_to_chat: 
        self.kw_to_chat[kw][0:0] = [node]
      else: 
        self.kw_to_chat[kw] = [node]
    self.id_to_node[node_id] = node 

    self.embeddings[embedding_pair[0]] = embedding_pair[1]
        
    return node


  def get_summarized_latest_events(self, retention): 
    ret_set = set()
    for e_node in self.seq_event[:retention]: 
      ret_set.add(e_node.spo_summary())
    return ret_set


  def get_str_seq_events(self): 
    ret_str = ""
    for count, event in enumerate(self.seq_event): 
      ret_str += f'{"Event", len(self.seq_event) - count, ": ", event.spo_summary(), " -- ", event.description}\n'
    return ret_str


  def get_str_seq_thoughts(self): 
    ret_str = ""
    for count, event in enumerate(self.seq_thought): 
      ret_str += f'{"Thought", len(self.seq_thought) - count, ": ", event.spo_summary(), " -- ", event.description}'
    return ret_str


  def get_str_seq_chats(self): 
    ret_str = ""
    for count, event in enumerate(self.seq_chat): 
      ret_str += f"with {event.object.content} ({event.description})\n"
      ret_str += f'{event.created.strftime("%B %d, %Y, %H:%M:%S")}\n'
      for row in event.filling: 
        ret_str += f"{row[0]}: {row[1]}\n"
    return ret_str


  def retrieve_relevant_thoughts(self, s_content, p_content, o_content): 
    contents = [s_content, p_content, o_content]

    ret = []
    for i in contents: 
      if i in self.kw_to_thought: 
        ret += self.kw_to_thought[i.lower()]

    ret = set(ret)
    return ret


  def retrieve_relevant_events(self, s_content, p_content, o_content): 
    contents = [s_content, p_content, o_content]

    ret = []
    for i in contents: 
      if i in self.kw_to_event: 
        ret += self.kw_to_event[i]

    ret = set(ret)
    return ret


  def get_last_chat(self, target_persona_name): 
    if target_persona_name.lower() in self.kw_to_chat: 
      return self.kw_to_chat[target_persona_name.lower()][0]
    else: 
      return False
