import pytest
import datetime
import json
from src.persona.memory_structures.associative_memory import AssociativeMemory, ConceptNode

@pytest.fixture
def sample_memory(tmp_path):
    # Create temporary test files
    memory_dir = tmp_path
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

def test_get_summarized_latest_events(sample_memory):
    created = datetime.datetime.now()
    
    event1 = sample_memory.add_event(
        created=created,
        expiration=None,
        s="John",
        p="goes to",
        o="store",
        description="John goes to the store",
        keywords={"store"},
        poignancy=0.5,
        embedding_pair=("key8", [0.1, 0.2, 0.3]),
        filling=None
    )
    
    event2 = sample_memory.add_event(
        created=created + datetime.timedelta(minutes=5),
        expiration=None,
        s="John",
        p="buys",
        o="groceries",
        description="John buys groceries",
        keywords={"groceries"},
        poignancy=0.5,
        embedding_pair=("key9", [0.4, 0.5, 0.6]),
        filling=None
    )
    
    # Test with retention=1
    latest = sample_memory.get_summarized_latest_events(1)
    assert len(latest) == 1
    assert event2.spo_summary() in latest
    
    # Test with retention=2
    latest = sample_memory.get_summarized_latest_events(2)
    assert len(latest) == 2
    assert event1.spo_summary() in latest
    assert event2.spo_summary() in latest

def test_get_str_seq_methods(sample_memory):
    created = datetime.datetime.now()
    
    # Add event
    sample_memory.add_event(
        created=created,
        expiration=None,
        s="John",
        p="goes to",
        o="store",
        description="John goes to the store",
        keywords={"store"},
        poignancy=0.5,
        embedding_pair=("key10", [0.1, 0.2, 0.3]),
        filling=None
    )
    
    # Add thought
    sample_memory.add_thought(
        created=created,
        expiration=None,
        s="John",
        p="thinks about",
        o="dinner",
        description="John thinks about dinner",
        keywords={"dinner"},
        poignancy=0.3,
        embedding_pair=("key11", [0.4, 0.5, 0.6]),
        filling=None
    )
    
    # Add chat
    sample_memory.add_chat(
        created=created,
        expiration=None,
        s="John",
        p="talks to",
        o="Jane",
        description="Chat about weather",
        keywords={"weather"},
        poignancy=0.4,
        embedding_pair=("key12", [0.7, 0.8, 0.9]),
        filling=[("John", "Nice weather"), ("Jane", "Yes!")]
    )
    
    # Test string representations
    events_str = sample_memory.get_str_seq_events()
    assert str(('Event', 1, ': ', ('John', 'goes to', 'store'), ' -- ', 'John goes to the store')) in events_str
    
    thoughts_str = sample_memory.get_str_seq_thoughts()
    assert str(('Thought', 1, ': ', ('John', 'thinks about', 'dinner'), ' -- ', 'John thinks about dinner')) in thoughts_str
    
    chats_str = sample_memory.get_str_seq_chats()
    assert "with Jane (Chat about weather)" in chats_str
    assert "John: Nice weather" in chats_str
    assert "Jane: Yes!" in chats_str

def test_retrieve_relevant_events(sample_memory):
    created = datetime.datetime.now()
    
    # Add some test events
    event1 = sample_memory.add_event(
        created=created,
        expiration=None,
        s="John",
        p="goes to",
        o="store",
        description="John goes to the store",
        keywords={"store", "shopping", "John"},
        poignancy=0.5,
        embedding_pair=("key16", [0.1, 0.2, 0.3]),
        filling=None
    )
    
    event2 = sample_memory.add_event(
        created=created,
        expiration=None,
        s="Jane",
        p="shops at",
        o="mall",
        description="Jane shops at the mall",
        keywords={"mall", "shop", "Jane"},
        poignancy=0.5,
        embedding_pair=("key17", [0.4, 0.5, 0.6]),
        filling=None
    )
    
    # Test retrieval by subject
    relevant = sample_memory.retrieve_relevant_events("John", "","")
    assert len(relevant) == 1
    assert event1 in relevant
    
    # Test retrieval by predicate
    relevant = sample_memory.retrieve_relevant_events("", "shops at", "")
    assert len(relevant) == 1
    assert event2 in relevant
    
    # Test retrieval by object
    relevant = sample_memory.retrieve_relevant_events("", "", "store")
    assert len(relevant) == 1
    assert event1 in relevant
    
    # Test retrieval with no matches
    relevant = sample_memory.retrieve_relevant_events("Bob", "", "")
    assert len(relevant) == 0

def test_expiration(sample_memory):
    created = datetime.datetime.now()
    expiration = created + datetime.timedelta(days=1)
    
    node = sample_memory.add_event(
        created=created,
        expiration=expiration,
        s="John",
        p="goes to",
        o="store",
        description="John goes to the store",
        keywords={"store"},
        poignancy=0.5,
        embedding_pair=("key18", [0.1, 0.2, 0.3]),
        filling=None
    )
    
    assert node.expiration == expiration
    assert node.expiration > node.created

def test_thought_depth(sample_memory):
    created = datetime.datetime.now()
    
    # Add base thought
    thought1 = sample_memory.add_thought(
        created=created,
        expiration=None,
        s="John",
        p="thinks about",
        o="dinner",
        description="Base thought about dinner",
        keywords={"dinner"},
        poignancy=0.3,
        embedding_pair=("key19", [0.1, 0.2, 0.3]),
        filling=None
    )
    assert thought1.depth == 1  # Base depth
    
    # Add thought that references first thought
    thought2 = sample_memory.add_thought(
        created=created,
        expiration=None,
        s="John",
        p="plans",
        o="cooking",
        description="Planning based on dinner thought",
        keywords={"cooking"},
        poignancy=0.3,
        embedding_pair=("key20", [0.4, 0.5, 0.6]),
        filling=[thought1.node_id]
    )
    assert thought2.depth == 2  # Depth should increase

def test_keyword_strength(sample_memory):
    created = datetime.datetime.now()
    
    # Add events with same keywords
    sample_memory.add_event(
        created=created,
        expiration=None,
        s="John",
        p="goes to",
        o="store",
        description="John goes to the store",
        keywords={"store", "shopping"},
        poignancy=0.5,
        embedding_pair=("key13", [0.1, 0.2, 0.3]),
        filling=None
    )
    
    sample_memory.add_event(
        created=created,
        expiration=None,
        s="Jane",
        p="visits",
        o="store",
        description="Jane visits the store",
        keywords={"store", "shopping"},
        poignancy=0.5,
        embedding_pair=("key14", [0.4, 0.5, 0.6]),
        filling=None
    )
    
    # Check keyword strengths
    assert sample_memory.kw_strength_event["store"] == 2
    assert sample_memory.kw_strength_event["shopping"] == 2
    
    # Add thought with keywords
    sample_memory.add_thought(
        created=created,
        expiration=None,
        s="John",
        p="thinks about",
        o="shopping",
        description="John thinks about shopping",
        keywords={"shopping", "planning"},
        poignancy=0.3,
        embedding_pair=("key15", [0.7, 0.8, 0.9]),
        filling=None
    )
    
    assert sample_memory.kw_strength_thought["shopping"] == 1
    assert sample_memory.kw_strength_thought["planning"] == 1
