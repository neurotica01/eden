import pytest
import datetime
import json
from src.persona.memory_structures.associative_memory import AssociativeMemory, ConceptNode

@pytest.fixture
def sample_memory(tmp_path):
    # Create temporary test files
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    
    # Create empty initial files
    embeddings = {}
    nodes = {}
    kw_strength = {"kw_strength_event": {}, "kw_strength_thought": {}}
    
    (memory_dir / "embeddings.json").write_text(json.dumps(embeddings))
    (memory_dir / "nodes.json").write_text(json.dumps(nodes))
    (memory_dir / "kw_strength.json").write_text(json.dumps(kw_strength))
    
    return AssociativeMemory(str(memory_dir))

def test_add_event(sample_memory):
    created = datetime.datetime.now()
    expiration = created + datetime.timedelta(days=1)
    
    node = sample_memory.add_event(
        created=created,
        expiration=expiration,
        s="John",
        p="walks to",
        o="store",
        description="John is walking to the store",
        keywords={"walk", "store", "John"},
        poignancy=0.5,
        embedding_pair=("key1", [0.1, 0.2, 0.3]),
        filling=None
    )
    
    assert node.node_count == 1
    assert node.type_count == 1
    assert node.type == "event"
    assert node.subject == "John"
    assert node.predicate == "walks to"
    assert node.object == "store"
    assert len(sample_memory.seq_event) == 1
    assert "walk" in sample_memory.kw_to_event
    assert "store" in sample_memory.kw_to_event
    assert "john" in sample_memory.kw_to_event

def test_add_thought(sample_memory):
    created = datetime.datetime.now()
    
    node = sample_memory.add_thought(
        created=created,
        expiration=None,
        s="John",
        p="thinks about",
        o="dinner",
        description="John is thinking about what to eat",
        keywords={"dinner", "food", "John"},
        poignancy=0.3,
        embedding_pair=("key2", [0.4, 0.5, 0.6]),
        filling=None
    )
    
    assert node.node_count == 1
    assert node.type_count == 1
    assert node.type == "thought"
    assert len(sample_memory.seq_thought) == 1
    assert "dinner" in sample_memory.kw_to_thought
    assert "food" in sample_memory.kw_to_thought

def test_add_chat(sample_memory):
    created = datetime.datetime.now()
    
    node = sample_memory.add_chat(
        created=created,
        expiration=None,
        s="John",
        p="talks to",
        o="Jane",
        description="Conversation about weather",
        keywords={"weather", "Jane", "conversation"},
        poignancy=0.4,
        embedding_pair=("key3", [0.7, 0.8, 0.9]),
        filling=[("John", "Nice weather today"), ("Jane", "Yes, it is!")]
    )
    
    assert node.node_count == 1
    assert node.type_count == 1
    assert node.type == "chat"
    assert len(sample_memory.seq_chat) == 1
    assert "jane" in sample_memory.kw_to_chat
    assert "weather" in sample_memory.kw_to_chat

def test_retrieve_relevant_thoughts(sample_memory):
    # Add some thoughts first
    created = datetime.datetime.now()
    
    thought1 = sample_memory.add_thought(
        created=created,
        expiration=None,
        s="John",
        p="thinks about",
        o="dinner",
        description="Thinking about dinner",
        keywords={"dinner", "food"},
        poignancy=0.3,
        embedding_pair=("key4", [0.1, 0.2, 0.3]),
        filling=None
    )
    
    thought2 = sample_memory.add_thought(
        created=created,
        expiration=None,
        s="John",
        p="thinks about",
        o="work",
        description="Thinking about work",
        keywords={"work", "job"},
        poignancy=0.3,
        embedding_pair=("key5", [0.4, 0.5, 0.6]),
        filling=None
    )
    
    # Test retrieval
    relevant = sample_memory.retrieve_relevant_thoughts("dinner", "thinks about", "food")
    assert len(relevant) == 1
    assert thought1 in relevant
    
    relevant = sample_memory.retrieve_relevant_thoughts("work", "thinks about", "job")
    assert len(relevant) == 1
    assert thought2 in relevant

def test_get_last_chat(sample_memory):
    created = datetime.datetime.now()
    
    chat1 = sample_memory.add_chat(
        created=created,
        expiration=None,
        s="John",
        p="talks to",
        o="Jane",
        description="First chat",
        keywords={"Jane"},
        poignancy=0.4,
        embedding_pair=("key6", [0.1, 0.2, 0.3]),
        filling=[("John", "Hi"), ("Jane", "Hello")]
    )
    
    chat2 = sample_memory.add_chat(
        created=created + datetime.timedelta(hours=1),
        expiration=None,
        s="John",
        p="talks to",
        o="Jane",
        description="Second chat",
        keywords={"Jane"},
        poignancy=0.4,
        embedding_pair=("key7", [0.4, 0.5, 0.6]),
        filling=[("John", "Bye"), ("Jane", "Goodbye")]
    )
    
    last_chat = sample_memory.get_last_chat("Jane")
    assert last_chat == chat2
    
    # Test non-existent chat
    assert sample_memory.get_last_chat("Bob") == False
