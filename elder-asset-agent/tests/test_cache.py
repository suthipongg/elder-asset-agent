from agent.tool_executor import ToolExecutor, MAX_CACHE_SIZE

def test_tool_executor_lfu_lru_cache():
    executor = ToolExecutor(budget=100)
    
    # Fill cache up to MAX_CACHE_SIZE
    for i in range(MAX_CACHE_SIZE):
        executor._add_to_cache(("tool", i), f"data_{i}")
        
    assert len(executor._cache) == MAX_CACHE_SIZE
    
    # Simulate accessing item 0 and 1 so their frequency increases
    # We do this by manipulating the _cache dict directly for testing the eviction logic.
    
    executor._cache[("tool", 0)]["freq"] += 5
    executor._cache[("tool", 1)]["freq"] += 2
    
    # Item 2 has frequency 1 and is the oldest accessed.
    
    # Add one more item to trigger eviction
    executor._add_to_cache(("tool", MAX_CACHE_SIZE), "new_data")
    
    assert len(executor._cache) == MAX_CACHE_SIZE
    assert ("tool", MAX_CACHE_SIZE) in executor._cache
    
    # Item 2 should be evicted (freq 1, oldest)
    assert ("tool", 2) not in executor._cache
    # Item 0 and 1 should still be there because they have higher frequency
    assert ("tool", 0) in executor._cache
    assert ("tool", 1) in executor._cache
