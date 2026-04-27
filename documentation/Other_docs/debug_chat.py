import asyncio
import json
from packages.memory.memory_service import build_context
from packages.model_gateway.client import chat

async def test_smart_chat():
    messages = [{"role": "user", "content": "What are the main findings in the research document?"}]
    context_prefix = await build_context("What are the main findings in the research document?", user_id="default")
    
    print("----- CONTEXT EXTRACTED -----")
    print(context_prefix)
    print("-----------------------------\n")

    if context_prefix:
        augmented_messages = [
            {"role": "system", "content": context_prefix},
            {"role": "user", "content": messages[0]["content"]},
        ]
    else:
        augmented_messages = messages
        
    print("----- MESSAGES SENT TO LLM -----")
    print(json.dumps(augmented_messages, indent=2))
    print("--------------------------------\n")
    
    response = await chat(augmented_messages, model="active", temperature=0.7)
    
    print("----- LLM RESPONSE -----")
    print(response)
    print("------------------------")

if __name__ == "__main__":
    asyncio.run(test_smart_chat())
