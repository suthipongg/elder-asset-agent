from agent.memory import ConversationMemory

def test_conversation_memory_add_turn():
    mem = ConversationMemory(max_turns=3)
    mem.add_turn("Hello", "Hi there")
    
    history = mem.get_history()
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1] == {"role": "assistant", "content": "Hi there"}

def test_conversation_memory_sliding_window():
    mem = ConversationMemory(max_turns=2)
    # Turn 1
    mem.add_turn("Q1", "A1")
    # Turn 2
    mem.add_turn("Q2", "A2")
    # Turn 3
    mem.add_turn("Q3", "A3")
    
    history = mem.get_history()
    # Should only keep max_turns * 2 = 4 messages (Turns 2 and 3)
    assert len(history) == 4
    assert history[0]["content"] == "Q2"
    assert history[1]["content"] == "A2"
    assert history[2]["content"] == "Q3"
    assert history[3]["content"] == "A3"

def test_conversation_memory_clear():
    mem = ConversationMemory(max_turns=3)
    mem.add_turn("Q1", "A1")
    mem.clear()
    assert len(mem.get_history()) == 0

def test_conversation_memory_add_individual():
    mem = ConversationMemory(max_turns=1)
    mem.add_user_message("Q1")
    mem.add_assistant_message("A1")
    
    history = mem.get_history()
    assert len(history) == 2
    
    # Adding one more message should trigger sliding window (max 2 messages)
    mem.add_user_message("Q2")
    history2 = mem.get_history()
    assert len(history2) == 2
    assert history2[0]["content"] == "A1"
    assert history2[1]["content"] == "Q2"
