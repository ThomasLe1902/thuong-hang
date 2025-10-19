import asyncio
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()
# from src.agents.primary_chatbot.flow import lesson_plan_design_agent
from src.agents.rag_agent_template.flow import rag_agent_template_agent


input_dict = {
    "messages": [
        HumanMessage(
            content="Tạo khung giáo án lớp 5, môn sử, bài Chiến thắng Bạch Đằng năm 938"
        )
    ]
}

config = {"configurable": {"thread_id": "1"}}


async def main():
    count = 0
    while True:
        if count != 0:
            human_message = input("Nhập input: ")
        else:
            human_message = "search db với 'kỳ co quy nhơn'"
        input_dict = {"messages": [HumanMessage(content=human_message)]}
        response = await rag_agent_template_agent.ainvoke(input_dict, config)
        print(response["messages"][-1].content)
        print("===============================================")
        count += 1


asyncio.run(main())
