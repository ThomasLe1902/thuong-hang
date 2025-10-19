# import os
# import asyncio
# from dotenv import load_dotenv
# from langchain_core.messages import HumanMessage
# from src.agents.primary_chatbot.flow import lesson_plan_design_agent
# from src.utils.logger import logger

# # Load environment variables
# load_dotenv()

# async def test_primary_chatbot_flow():
#     """
#     Test the primary chatbot flow with different scenarios
#     """
#     print("Testing primary chatbot flow...")
    
#     # Print the flow diagram
#     print("\n=== Flow Diagram ===")
#     print(lesson_plan_design_agent.get_graph().draw_mermaid())
    
#     # Create test cases
#     test_cases = [
#         {
#             "name": "New user query with no previous info",
#             "state": {
#                 "user_query": HumanMessage(content="Xây dựng giáo án cho bài toán cộng trừ nhân chia"),
#                 "messages_history": [],
#                 "document_id_selected": None,
#                 "topic": "",
#                 "lesson_name": "",
#                 "subject_name": "",
#                 "class_number": 0,
#                 "entry_response": "",
#                 "build_lesson_plan_response": None
#             }
#         },
#         {
#             "name": "User query with existing info",
#             "state": {
#                 "user_query": HumanMessage(content="Giúp tôi xây dựng giáo án"),
#                 "messages_history": [
#                     {"type": "human", "content": "Xin chào"},
#                     {"type": "ai", "content": "Xin chào, tôi có thể giúp gì cho bạn?"}
#                 ],
#                 "document_id_selected": None,
#                 "topic": "Toán học cơ bản",
#                 "lesson_name": "Phép cộng và phép trừ",
#                 "subject_name": "Toán",
#                 "class_number": 3,
#                 "entry_response": "",
#                 "build_lesson_plan_response": None
#             }
#         }
#     ]
    
#     # Run test cases
#     for i, test_case in enumerate(test_cases):
#         print(f"\n\n=== Test Case {i+1}: {test_case['name']} ===")
#         print(f"Input state: {test_case['state']}")
        
#         try:
#             # Execute the flow with the test state
#             result = await lesson_plan_design_agent.ainvoke(test_case['state'])
            
#             # Display the result
#             print("\nResult:")
#             for key, value in result.items():
#                 if key == "messages_history":
#                     print(f"  {key}: [... {len(value)} messages ...]")
#                 elif key == "build_lesson_plan_response" and value is not None:
#                     print(f"  {key}: {value.content[:100]}... (truncated)")
#                     if hasattr(value, "tool_calls") and value.tool_calls:
#                         print(f"  tool_calls: {value.tool_calls}")
#                 else:
#                     print(f"  {key}: {value}")
                    
#             print("\nFlow execution successful!")
#         except Exception as e:
#             print(f"Error executing flow: {e}")
    
#     print("\n=== All tests completed ===")

# async def test_specific_node():
#     """
#     Test a specific node in the flow
#     """
#     from src.agents.primary_chatbot.func import entry, build_lesson_plan
    
#     # Test the entry node
#     print("\n=== Testing entry node ===")
#     state = {
#         "user_query": HumanMessage(content="Xây dựng giáo án cho bài Phép cộng và phép trừ, môn Toán, lớp 3"),
#         "messages_history": [],
#         "document_id_selected": None,
#         "topic": "",
#         "lesson_name": "",
#         "subject_name": "",
#         "class_number": 0,
#         "entry_response": "",
#         "build_lesson_plan_response": None
#     }
    
#     try:
#         entry_result = await entry(state)
#         print("Entry node result:")
#         for key, value in entry_result.items():
#             print(f"  {key}: {value}")
#     except Exception as e:
#         print(f"Error in entry node: {e}")
    
#     # Test the build_lesson_plan node
#     print("\n=== Testing build_lesson_plan node ===")
#     state = {
#         "user_query": HumanMessage(content="Xây dựng giáo án"),
#         "messages_history": [],
#         "document_id_selected": None,
#         "topic": "Toán học cơ bản",
#         "lesson_name": "Phép cộng và phép trừ",
#         "subject_name": "Toán",
#         "class_number": 3,
#         "entry_response": "Tôi sẽ giúp bạn xây dựng giáo án",
#         "build_lesson_plan_response": None
#     }
    
#     try:
#         build_result = await build_lesson_plan(state)
#         print("Build lesson plan node result:")
#         for key, value in build_result.items():
#             print(f"  {key}: {value}")
#     except Exception as e:
#         print(f"Error in build_lesson_plan node: {e}")

# if __name__ == "__main__":
#     # You can choose which test to run:
#     # 1. Test the entire flow
#     # 2. Test specific nodes
    
#     # Run the async tests
#     print("Choose a test to run:")
#     print("1. Test the entire flow")
#     print("2. Test specific nodes")
    
#     choice = input("Enter your choice (1 or 2): ")
    
#     if choice == "1":
#         asyncio.run(test_primary_chatbot_flow())
#     elif choice == "2":
#         asyncio.run(test_specific_node())
#     else:
#         print("Invalid choice. Please run again with a valid option.")
