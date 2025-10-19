from src.agents.prompt_analyzed.flow import analyze_prompt

criterion = """
Hướng Dẫn Viết Instruction Mô Tả Hoạt Động Của Chatbot 

1. Giới Thiệu 

Instruction (hướng dẫn) là một phần quan trọng trong quá trình xây dựng chatbot, giúp mô tả cách chatbot phản hồi và hoạt động theo mục tiêu đề ra. Tài liệu này hướng dẫn cách viết instruction hiệu quả để tối ưu hóa hoạt động của chatbot. 

2. Nguyên Tắc Viết Instruction 

Cụ thể và rõ ràng: Mô tả hành vi của chatbot một cách chi tiết. 

Ngắn gọn nhưng đầy đủ: Tránh viết dài dòng, tập trung vào mục tiêu chính. 

Sử dụng ngôn ngữ tự nhiên: Viết hướng dẫn dễ hiểu, tránh thuật ngữ quá chuyên môn. 

Tính nhất quán: Đảm bảo các hướng dẫn không mâu thuẫn với nhau. 

Tính linh hoạt: Hướng dẫn cần đủ linh hoạt để chatbot có thể xử lý nhiều tình huống khác nhau. 

3. Các Thành Phần Của Instruction 

Instruction cần có các phần chính sau: 

3.1. Mô Tả Mục Tiêu Chatbot 

Xác định mục tiêu chính của chatbot (ví dụ: hỗ trợ khách hàng, tư vấn sản phẩm, trợ lý học tập...) 

Định nghĩa rõ chatbot sẽ giải quyết vấn đề gì cho người dùng. 

Ví dụ:  

Chatbot này được thiết kế để hỗ trợ khách hàng trong việc đặt hàng trực tuyến, giải đáp thắc mắc về sản phẩm và hỗ trợ sau bán hàng. 

3.2. Định Nghĩa Vai Trò Của Chatbot 

Chatbot hoạt động như thế nào? (trợ lý ảo, tổng đài tự động, chuyên gia tư vấn...) 

Có giọng điệu giao tiếp như thế nào? (thân thiện, trang trọng, hài hước...) 

Ví dụ:  

Chatbot sẽ đóng vai trò như một nhân viên hỗ trợ khách hàng, sử dụng giọng điệu thân thiện và chuyên nghiệp để giải đáp các câu hỏi. 

3.3. Quy Tắc Phản Hồi 

Xác định cách chatbot phản hồi trong các trường hợp khác nhau. 

Ví dụ về phản hồi trong các tình huống cụ thể:  

Khi khách hàng hỏi về sản phẩm:  

Nếu khách hàng hỏi về sản phẩm, cung cấp mô tả ngắn gọn kèm theo giá cả và đường dẫn đến trang sản phẩm. 

Khi chatbot không hiểu câu hỏi:  

Nếu chatbot không hiểu câu hỏi, đề nghị khách hàng diễn đạt lại hoặc cung cấp từ khóa liên quan. 

Khi chatbot nhận phản hồi tiêu cực:  

Nếu khách hàng phản hồi tiêu cực, chatbot nên xin lỗi và đề nghị hướng giải quyết phù hợp. 

3.4. Xử Lý Dữ Liệu Đầu Vào 

Xác định chatbot sẽ xử lý dữ liệu đầu vào như thế nào. 

Ví dụ:  

- Nếu khách hàng nhập câu hỏi dài, chatbot sẽ tóm tắt và hỏi lại để xác nhận. 

- Nếu khách hàng nhập sai chính tả, chatbot sẽ tự động đề xuất từ đúng. 

3.5. Giới Hạn Của Chatbot 

Xác định những nội dung chatbot không thể xử lý. 

Ví dụ:  

Chatbot không hỗ trợ các vấn đề liên quan đến bảo mật tài khoản hoặc xử lý khiếu nại phức tạp. Người dùng sẽ được hướng dẫn liên hệ với bộ phận hỗ trợ khách hàng. 

3.6. Luồng Hội Thoại Cơ Bản 

Xây dựng kịch bản hội thoại điển hình. 

Ví dụ: Người dùng: Tôi muốn biết giá sản phẩm X. Chatbot: Sản phẩm X hiện có giá 500.000 VND. Bạn có muốn đặt hàng ngay không? Người dùng: Có. Chatbot: Bạn vui lòng cung cấp địa chỉ giao hàng. 

4. Hướng Dẫn Viết Instruction Cho Các Loại Chatbot Khác Nhau 

4.1. Chatbot Hỗ Trợ Khách Hàng 

Phản hồi nhanh chóng, cung cấp thông tin chính xác. 

Hỗ trợ giải quyết vấn đề của khách hàng hiệu quả. 

Ví dụ instruction:  

- Trả lời các câu hỏi về chính sách bảo hành, đổi trả trong vòng 3 giây. 

- Nếu khách hàng yêu cầu hỗ trợ chuyên sâu, hướng dẫn họ liên hệ tổng đài viên. 

4.2. Chatbot Giáo Dục 

Cung cấp thông tin chi tiết, dễ hiểu. 

Tạo môi trường học tập thân thiện. 

Ví dụ instruction:  

- Giải thích khái niệm bằng cách sử dụng ví dụ thực tế. 

- Nếu học sinh yêu cầu bài tập, cung cấp bài tập kèm theo gợi ý giải. 

4.3. Chatbot Tư Vấn Sản Phẩm 

Giới thiệu sản phẩm theo nhu cầu khách hàng. 

Hướng dẫn khách hàng đặt hàng nhanh chóng. 

Ví dụ instruction:  

- Khi khách hàng hỏi về một sản phẩm, cung cấp hình ảnh, giá cả và các tính năng chính. 

- Nếu khách hàng chưa quyết định, đề xuất sản phẩm tương tự dựa trên nhu cầu của họ. 

5. Cách Kiểm Tra Và Cải Tiến Instruction 

Thử nghiệm thực tế: Kiểm tra phản hồi của chatbot với nhiều loại câu hỏi. 

Thu thập phản hồi: Hỏi người dùng về trải nghiệm sử dụng chatbot. 

Cập nhật định kỳ: Điều chỉnh instruction dựa trên dữ liệu thực tế. 

6. Kết Luận 

Viết instruction hiệu quả giúp chatbot hoạt động mượt mà, chính xác và đáp ứng nhu cầu người dùng. Hãy luôn kiểm tra, thử nghiệm và cập nhật để chatbot ngày càng thông minh hơn! 

"""
prompt = """"""
analyze_prompt(prompt,criterion)