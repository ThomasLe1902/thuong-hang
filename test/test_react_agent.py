
from src.agents.custom_chatbot.flow import custom_chatbot
config = {"configurable": {"thread_id": "2"}}

async def main():
    while True:
        message_input=input(">>")
        res = await custom_chatbot.ainvoke(
            {"messages": [{"role": "user", "content": message_input}]},
            config=config
        )
        print(res.get("messages")[-1].content)
        
        
import asyncio
asyncio.run(main())