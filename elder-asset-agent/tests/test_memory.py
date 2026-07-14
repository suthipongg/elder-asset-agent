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

def test_tool_history_basic():
    mem = ConversationMemory(max_turns=3)
    mem.add_turn("Q1", "A1", tool_outputs={"support_case": {"case_id": "C-123", "status": "open"}})
    state = mem.get_tool_history()
    assert "support_case" in state
    assert state["support_case"]["case_id"] == "C-123"

def test_tool_history_sliding_window():
    mem = ConversationMemory(max_turns=2)
    mem.add_turn("Q1", "A1", tool_outputs={"accounts": [{"account_id": "ACC-1"}]})
    mem.add_turn("Q2", "A2", tool_outputs={"accounts": [{"account_id": "ACC-2"}]})
    mem.add_turn("Q3", "A3", tool_outputs={"accounts": [{"account_id": "ACC-3"}]})
    
    # Should only keep max_turns = 2 tool outputs (Turn 2 and Turn 3)
    state = mem.get_tool_history()
    assert "accounts" in state
    assert len(state["accounts"]) == 2
    assert state["accounts"][0]["account_id"] == "ACC-2"
    assert state["accounts"][1]["account_id"] == "ACC-3"

def test_tool_history_merge_accounts():
    mem = ConversationMemory(max_turns=3)
    # Turn 1: Account 1 with 1000 balance
    mem.add_turn("Q1", "A1", tool_outputs={"accounts": [{"account_id": "ACC-1", "balance": 1000}]})
    # Turn 2: Account 1 updated balance, Account 2 added
    mem.add_turn("Q2", "A2", tool_outputs={"accounts": [{"account_id": "ACC-1", "balance": 1500}, {"account_id": "ACC-2", "balance": 2000}]})
    
    state = mem.get_tool_history()
    assert len(state["accounts"]) == 2
    
    # Check if ACC-1 was overwritten with the latest balance
    acc_1 = next(a for a in state["accounts"] if a["account_id"] == "ACC-1")
    assert acc_1["balance"] == 1500

def test_tool_history_merge_portfolio_dict_and_list():
    mem = ConversationMemory(max_turns=3)
    # Turn 1: Single portfolio as a DICT
    mem.add_turn("Q1", "A1", tool_outputs={"portfolio": {"account_id": "ACC-1", "value": 500}})
    # Turn 2: Multiple portfolios as a LIST
    mem.add_turn("Q2", "A2", tool_outputs={"portfolio": [{"account_id": "ACC-2", "value": 1000}, {"account_id": "ACC-1", "value": 600}]})
    
    state = mem.get_tool_history()
    assert isinstance(state["portfolio"], list)
    assert len(state["portfolio"]) == 2
    
    acc_1 = next(p for p in state["portfolio"] if p["account_id"] == "ACC-1")
    assert acc_1["value"] == 600

def test_tool_history_transactions_limit_and_sort():
    mem = ConversationMemory(max_turns=3)
    
    # Generate 25 dummy transactions
    txns = [{"transaction_id": f"T-{i}", "date": f"2023-01-{i:02d}"} for i in range(1, 26)]
    
    mem.add_turn("Q1", "A1", tool_outputs={"transactions": txns})
    
    state = mem.get_tool_history()
    assert len(state["transactions"]) == 20
    
    # Should be sorted descending by date, so T-25 should be first
    assert state["transactions"][0]["transaction_id"] == "T-25"
    assert state["transactions"][-1]["transaction_id"] == "T-6"