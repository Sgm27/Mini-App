#!/bin/bash
# Seed script - insert categories and articles into Mini App Storage

BASE="https://maxflow.ai/api/app/ybG2ZuM1/db"
TOKEN="Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJuaHVuZ3RydW9uZ0BtYXhmbG93dGVjaC5jb20iLCJpYXQiOjE3NzQwMTM5MzQsIm5iZiI6MTc3NDAxMzkzNCwianRpIjoiYWQ4MmQ0YTQtZTlkZC00YzRjLTkzYjktYjk1MDMxODI2NGY4IiwiZXhwIjoxODA1NTQ5OTM0LCJ0eXBlIjoiYWNjZXNzIiwiZnJlc2giOmZhbHNlLCJpZGVudGl0eSI6Im5odW5ndHJ1b25nQG1heGZsb3d0ZWNoLmNvbSJ9.UiYwjCkQDG4_Si6baVFxB2dsXanXW0gL2IU0FzkvCCgzmO4XROPedhqsCZlFuCV7vascP0AEQfbz4idxehKSRoLIHODfCzmzw5GRYYSWiqfH7RmiAECHLcQxcMbDnUuzmSpQe3XPd7wNGzqSv7XoFoL6z0K-3CrbxLzgHYs0leQ"
CAT_STORAGE=59
ART_STORAGE=58

post() {
  curl -s -X POST "$1" -H "Content-Type: application/json" -H "Authorization: $TOKEN" -d "$2"
}

echo "=== Creating categories ==="

CAT1=$(post "$BASE/$CAT_STORAGE/insert" '{"documents":{"name":"Công nghệ","description":"Tin tức công nghệ, AI, bán dẫn, chuyển đổi số","order":1}}')
echo "Cong nghe: $CAT1"
CAT1_ID=$(echo "$CAT1" | python3 -c "import sys,json; print(json.load(sys.stdin)['inserted_id'])")

CAT2=$(post "$BASE/$CAT_STORAGE/insert" '{"documents":{"name":"Kinh tế","description":"Tin tức kinh tế, tài chính, đầu tư, doanh nghiệp","order":2}}')
echo "Kinh te: $CAT2"
CAT2_ID=$(echo "$CAT2" | python3 -c "import sys,json; print(json.load(sys.stdin)['inserted_id'])")

CAT3=$(post "$BASE/$CAT_STORAGE/insert" '{"documents":{"name":"Thể thao","description":"Tin tức thể thao trong và ngoài nước","order":3}}')
echo "The thao: $CAT3"
CAT3_ID=$(echo "$CAT3" | python3 -c "import sys,json; print(json.load(sys.stdin)['inserted_id'])")

echo ""
echo "Category IDs: $CAT1_ID, $CAT2_ID, $CAT3_ID"
echo ""
echo "=== Creating articles ==="

# Article 1 - Cong nghe
post "$BASE/$ART_STORAGE/insert" "$(cat <<ENDJSON
{"documents":{
  "title":"Xu hướng trí tuệ nhân tạo năm 2026: Từ tạo sinh đến thực hiện",
  "summary":"AI đang chuyển từ mô hình tạo sinh sang hệ thống hành động tự động, với Large Action Models (LAM) thay thế Large Language Models (LLM), đánh dấu bước chuyển mình lớn trong công nghệ AI năm 2026.",
  "content":"<p>AI đã vượt ra ngoài các tác vụ hỏi đáp đơn giản để tự động xử lý các hoạt động phức tạp dựa trên lý luận và dữ liệu cá nhân hóa.</p><h2>Large Action Models thay thế LLM</h2><p>Sự chuyển đổi tập trung vào Large Action Models (LAM) thay thế Large Language Models (LLM). Ví dụ, thay vì chỉ liệt kê các chuyến bay khi được hỏi 'Tìm chuyến bay đến Osaka,' trợ lý AI sẽ kiểm tra lịch trình, chọn ghế ưa thích, hoàn tất thanh toán và xác nhận đặt chỗ.</p><h2>Bảo vệ dữ liệu cá nhân</h2><p>Một trọng tâm quan trọng xuất hiện xung quanh bảo vệ dữ liệu cá nhân, khi lợi thế cạnh tranh giờ đây phụ thuộc vào xử lý dữ liệu an toàn thay vì trí thông minh thô. Samsung và các công ty Hàn Quốc đang phát triển giải pháp 'AI trên thiết bị' để ngăn rò rỉ thông tin nhạy cảm qua điện toán đám mây.</p><p>Các công ty công nghệ Hàn Quốc đang định vị mình bằng cách kết hợp khả năng sản xuất phần cứng với dịch vụ AI, nhắm đến tích hợp liền mạch vào các ứng dụng hàng ngày.</p>",
  "author":"Khánh Vân - VietnamPlus",
  "thumbnail":"https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&q=80",
  "category_id":"$CAT1_ID",
  "status":"published",
  "created_at":"2026-03-26T08:00:00Z",
  "updated_at":"2026-03-26T08:00:00Z"
}}
ENDJSON
)"
echo ""
echo "1/10 - Xu huong AI 2026"

# Article 2 - Cong nghe
post "$BASE/$ART_STORAGE/insert" "$(cat <<ENDJSON
{"documents":{
  "title":"Luật Trí tuệ nhân tạo 2025: Khung pháp lý mới cho phát triển AI an toàn và bền vững",
  "summary":"Quốc hội Việt Nam thông qua Luật số 134/2025/QH15 về AI, có hiệu lực từ ngày 1/3/2026, là văn bản pháp lý chuyên ngành đầu tiên điều chỉnh toàn diện hoạt động AI tại Việt Nam.",
  "content":"<p>Quốc hội Việt Nam đã thông qua Luật số 134/2025/QH15 về AI, có hiệu lực từ ngày 1/3/2026. Đây được mô tả là 'văn bản pháp lý chuyên ngành đầu tiên điều chỉnh toàn diện hoạt động nghiên cứu, phát triển, cung cấp và sử dụng AI,' đại diện cho bước tiến thể chế quan trọng trong chuyển đổi số.</p><h2>Quản lý dựa trên rủi ro</h2><p>Khung pháp lý thực hiện quản lý AI dựa trên rủi ro, phân loại hệ thống theo mức độ tác động. Các tổ chức phải đảm bảo minh bạch về nội dung do AI tạo ra và thông báo cho người dùng khi tương tác với hệ thống AI.</p><p>Các hệ thống rủi ro cao yêu cầu đánh giá và chứng nhận trước khi triển khai chính thức, cùng với giám sát hoạt động liên tục.</p><h2>Cấm sử dụng sai mục đích</h2><p>Luật thiết lập cơ chế báo cáo sự cố và cấm sử dụng AI sai mục đích cho vi phạm quyền riêng tư, thao túng hành vi và tung tin sai lệch. Đồng thời thúc đẩy phát triển hệ sinh thái thông qua hỗ trợ hạ tầng dữ liệu, cơ chế thử nghiệm có kiểm soát và khuyến khích nghiên cứu.</p>",
  "author":"Trung tâm KH&CN Thái Nguyên",
  "thumbnail":"https://images.unsplash.com/photo-1589254065878-42c014e36a44?w=800&q=80",
  "category_id":"$CAT1_ID",
  "status":"published",
  "created_at":"2026-03-25T14:00:00Z",
  "updated_at":"2026-03-25T14:00:00Z"
}}
ENDJSON
)"
echo ""
echo "2/10 - Luat AI 2025"

# Article 3 - Cong nghe
post "$BASE/$ART_STORAGE/insert" "$(cat <<ENDJSON
{"documents":{
  "title":"AI tái định hình xu hướng tuyển dụng 2026 tại Việt Nam",
  "summary":"Trí tuệ nhân tạo đang thay đổi căn bản thị trường lao động Việt Nam, doanh nghiệp chuyển từ tuyển dụng số lượng sang ưu tiên chất lượng và năng lực AI trở thành tiêu chuẩn mới.",
  "content":"<p>Trí tuệ nhân tạo đang thay đổi căn bản thị trường lao động Việt Nam. Thay vì tuyển dụng ồ ạt, doanh nghiệp giờ đây ưu tiên 'chất lượng và chọn lọc,' tập trung vào các vị trí then chốt và nhân sự trình độ cao.</p><h2>Báo cáo xu hướng tuyển dụng 2026</h2><p>Theo Báo cáo Xu hướng Tuyển dụng 2026 của TopCV, các công ty đang chuyển từ tuyển dụng theo số lượng sang chiến lược 'duy trì quy mô nhân sự đồng thời tối ưu hiệu suất.' Báo cáo phân tích phản hồi từ hơn 3.000 đại diện tuyển dụng và gần 300.000 tin tuyển dụng từ quý 3/2025.</p><h2>Nhu cầu tuyển dụng hàng đầu</h2><p>Nhu cầu tuyển dụng hàng đầu bao gồm Kinh doanh/Bán hàng (47,5%), CNTT-Phần mềm (8,64%), Marketing/Truyền thông (8,22%), Dịch vụ khách hàng (6,1%) và R&D (4,14%). Trong lĩnh vực CNTT, vị trí lập trình viên web, kỹ sư backend và kỹ sư AI được tìm kiếm nhiều nhất.</p><blockquote>AI không còn được xem là công cụ hỗ trợ riêng lẻ mà là năng lực tổ chức cốt lõi, đòi hỏi đầu tư hệ thống vào phát triển và đào tạo lực lượng lao động.</blockquote>",
  "author":"Tạp chí KH&CN Việt Nam",
  "thumbnail":"https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=800&q=80",
  "category_id":"$CAT1_ID",
  "status":"published",
  "created_at":"2026-03-24T10:30:00Z",
  "updated_at":"2026-03-24T10:30:00Z"
}}
ENDJSON
)"
echo ""
echo "3/10 - AI tuyen dung"

# Article 4 - Cong nghe
post "$BASE/$ART_STORAGE/insert" "$(cat <<ENDJSON
{"documents":{
  "title":"Thủ tướng: Việt Nam phấn đấu có nhà máy chip bán dẫn đầu tiên trong năm 2026",
  "summary":"Việt Nam đặt mục tiêu xây dựng nhà máy sản xuất chip bán dẫn đầu tiên vào năm 2026, với Viettel khởi công xây dựng nhà máy công nghệ cao, đánh dấu bước đột phá trong ngành công nghiệp bán dẫn.",
  "content":"<p>Thủ tướng Phạm Minh Chính nhấn mạnh mục tiêu Việt Nam phấn đấu có nhà máy chip bán dẫn đầu tiên trong năm 2026, thể hiện quyết tâm chính trị cao trong phát triển ngành công nghiệp bán dẫn.</p><h2>Viettel tiên phong</h2><p>Đầu năm 2026, Viettel đã khởi công xây dựng nhà máy sản xuất chip bán dẫn công nghệ cao đầu tiên của Việt Nam, đánh dấu bước khởi đầu để Việt Nam làm chủ giai đoạn khó nhất - chế tạo (fabrication) - bên cạnh giai đoạn thiết kế.</p><h2>Hệ sinh thái bán dẫn</h2><p>Ngành công nghiệp bán dẫn Việt Nam đang phát triển vượt ra ngoài nền tảng ATP ban đầu để trở thành hệ sinh thái bao gồm thiết kế chip, đóng gói, kiểm thử và cuối cùng là chế tạo. Các tập đoàn hàng đầu thế giới như Amkor, Hana Micron, Intel và Coherent đang tăng cường đầu tư vào đóng gói và kiểm thử bán dẫn tại Việt Nam.</p><p>Luật Công nghiệp Công nghệ số (Luật số 71/2025/QH15) được thông qua tháng 6/2025 và có hiệu lực từ 01/01/2026, tạo nền tảng pháp lý toàn diện cho phát triển các lĩnh vực công nghệ mới nổi, bao gồm bán dẫn.</p>",
  "author":"Vietnam.vn",
  "thumbnail":"https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80",
  "category_id":"$CAT1_ID",
  "status":"published",
  "created_at":"2026-03-23T09:00:00Z",
  "updated_at":"2026-03-23T09:00:00Z"
}}
ENDJSON
)"
echo ""
echo "4/10 - Chip ban dan"

# Article 5 - Kinh te
post "$BASE/$ART_STORAGE/insert" "$(cat <<ENDJSON
{"documents":{
  "title":"Bức tranh kinh tế Việt Nam năm 2025 và dự báo năm 2026",
  "summary":"Kinh tế Việt Nam năm 2025 tăng trưởng ấn tượng 8,02% GDP, GDP bình quân đầu người đạt khoảng 5.000 USD. Dự báo năm 2026 tăng trưởng 9-10% trong kịch bản lạc quan.",
  "content":"<p>Theo Viện Nghiên cứu Kinh tế BIDV, kinh tế Việt Nam năm 2025 thể hiện khả năng phục hồi ấn tượng với 'nền tảng vững chắc' cho tăng trưởng tương lai.</p><h2>Sáu điểm mạnh chính</h2><p>Phân tích chỉ ra sáu điểm mạnh chính: quản lý vĩ mô quyết liệt, tăng trưởng GDP đột phá 8,02%, duy trì ổn định kinh tế với lạm phát được kiểm soát, hoạt động kinh doanh sôi động, thu ngân sách nhà nước mạnh mẽ và hội nhập quốc tế thành công.</p><h2>Thách thức phía trước</h2><p>Tuy nhiên, báo cáo cũng thừa nhận những thách thức dai dẳng bao gồm rủi ro địa chính trị, động lực tăng trưởng không đồng đều và các tác động của biến đổi khí hậu ảnh hưởng đến năng suất.</p><h2>Dự báo 2026</h2><p>Dự báo năm 2026: tăng trưởng 9-9,5% trong kịch bản cơ sở hoặc khoảng 10% trong kịch bản lạc quan. GDP bình quân đầu người dự kiến đạt 5.400-5.500 USD.</p>",
  "author":"TS. Cấn Văn Lực - BIDV",
  "thumbnail":"https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80",
  "category_id":"$CAT2_ID",
  "status":"published",
  "created_at":"2026-03-22T11:00:00Z",
  "updated_at":"2026-03-22T11:00:00Z"
}}
ENDJSON
)"
echo ""
echo "5/10 - Buc tranh kinh te"

# Article 6 - Kinh te
post "$BASE/$ART_STORAGE/insert" "$(cat <<ENDJSON
{"documents":{
  "title":"Kinh tế Việt Nam 2025: Vượt cơn gió ngược, tạo đà bứt phá 2026",
  "summary":"Việt Nam đạt tăng trưởng GDP khoảng 8% năm 2025, trở thành một trong những nền kinh tế tăng trưởng nhanh nhất thế giới, với thu ngân sách vượt kế hoạch 25%.",
  "content":"<p>Năm 2025 khép lại với những thành tựu kinh tế đáng kể cho Việt Nam bất chấp những bất ổn toàn cầu từ xung đột địa chính trị, chính sách thương mại bảo hộ và biến động tài chính.</p><h2>Thành tựu nổi bật</h2><p>Việt Nam đạt tăng trưởng GDP khoảng 8%, khẳng định vị thế là một trong những nền kinh tế tăng trưởng nhanh nhất thế giới. GDP bình quân đầu người đạt khoảng 5.000 USD, gần gấp đôi so với năm 2020 và tiếp cận ngưỡng thu nhập trung bình cao. Lạm phát được kiểm soát ở mức khoảng 3,5%.</p><h2>Đầu tư công và hạ tầng</h2><p>Thu ngân sách nhà nước vượt kế hoạch hơn 25%, chủ yếu nhờ hoạt động sản xuất kinh doanh. Đầu tư công được triển khai quyết liệt, hoàn thành hơn 3.500 km đường cao tốc cùng các dự án năng lượng và hạ tầng xã hội lớn.</p><h2>Cải cách thể chế</h2><p>Cải cách thể chế được đẩy mạnh đáng kể, Quốc hội thông qua hơn 180 luật và Chính phủ ban hành 820 nghị định - con số cao nhất trong lịch sử.</p>",
  "author":"Hoàng Long - Báo Thanh Tra",
  "thumbnail":"https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=800&q=80",
  "category_id":"$CAT2_ID",
  "status":"published",
  "created_at":"2026-03-21T08:30:00Z",
  "updated_at":"2026-03-21T08:30:00Z"
}}
ENDJSON
)"
echo ""
echo "6/10 - Vuot gio nguoc"

# Article 7 - Kinh te
post "$BASE/$ART_STORAGE/insert" "$(cat <<ENDJSON
{"documents":{
  "title":"Kinh tế Việt Nam 2026: Tăng trưởng cao và phép thử về nền tảng, thực thi",
  "summary":"Năm 2026 đặt ra phép thử quan trọng về nền tảng tăng trưởng và năng lực thực thi chính sách, Quốc hội đặt mục tiêu GDP tăng trưởng 10% trở lên.",
  "content":"<p>Kinh tế Việt Nam duy trì ổn định trong năm 2025 giữa nhiều bất ổn toàn cầu, tuy nhiên những thách thức đáng kể cho giai đoạn tới liên quan đến 'nền tảng tăng trưởng và năng lực thực thi chính sách.'</p><h2>Phép thử quan trọng</h2><p>Phân tích cho thấy trong khi Việt Nam đạt được ổn định kinh tế năm 2025 bất chấp điều kiện toàn cầu khó khăn, các nhà hoạch định chính sách đối mặt với phép thử quan trọng phía trước.</p><p>Mối quan tâm chính tập trung vào việc củng cố nền tảng cơ cấu hỗ trợ tăng trưởng và nâng cao năng lực thực thi chính sách kinh tế hiệu quả của chính phủ khi đất nước bước vào năm 2026.</p><h2>Mục tiêu tham vọng</h2><p>Quốc hội đặt mục tiêu tăng trưởng GDP 10% trở lên cho năm 2026, GDP bình quân đầu người dự kiến đạt 5.400-5.500 USD. Đây là mục tiêu tham vọng đòi hỏi nỗ lực đồng bộ từ mọi cấp chính quyền và khu vực tư nhân.</p>",
  "author":"Báo Chính Phủ",
  "thumbnail":"https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=800&q=80",
  "category_id":"$CAT2_ID",
  "status":"published",
  "created_at":"2026-03-20T15:00:00Z",
  "updated_at":"2026-03-20T15:00:00Z"
}}
ENDJSON
)"
echo ""
echo "7/10 - Tang truong cao"

# Article 8 - The thao
post "$BASE/$ART_STORAGE/insert" "$(cat <<ENDJSON
{"documents":{
  "title":"Năm 2025: Dấu ấn toàn diện của ngành Thể dục thể thao Việt Nam",
  "summary":"Thể thao Việt Nam năm 2025 đạt thành tích ấn tượng với 2.253 huy chương quốc tế, bao gồm 80 HCV thế giới và 161 HCV châu Á.",
  "content":"<p>Cục Thể dục Thể thao Việt Nam tổ chức hội nghị tổng kết năm vào ngày 26/12/2025, đánh giá toàn diện thành tựu và định hướng ưu tiên phía trước. Thứ trưởng Hoàng Đạo Cương chủ trì hội nghị.</p><h2>Thành tích quốc tế</h2><p>Kết quả thi đấu thể hiện sự phát triển rộng rãi, với các vận động viên giành được 2.253 huy chương quốc tế trong năm 2025, bao gồm 80 huy chương vàng cấp thế giới và 161 huy chương vàng châu Á.</p><h2>Sự kiện khu vực</h2><p>Cục tập trung nguồn lực chuẩn bị và thi đấu tại các sự kiện khu vực lớn, bao gồm SEA Games 33 tại Thái Lan, Đại hội Thể thao Trẻ châu Á tại Bahrain, và tổ chức thành công Hội nghị Bộ trưởng Thể thao ASEAN lần thứ 8.</p><h2>Thể thao quần chúng</h2><p>Hoạt động thể dục thể thao quần chúng mở rộng đáng kể, với số lượng người tập luyện thường xuyên và câu lạc bộ thể thao tăng trên toàn quốc. Nhiều chương trình cộng đồng như phòng chống đuối nước và chạy Olympic phát triển mạnh mẽ.</p>",
  "author":"Bộ Văn hóa, Thể thao và Du lịch",
  "thumbnail":"https://images.unsplash.com/photo-1461896836934-bd45ba8b2cda?w=800&q=80",
  "category_id":"$CAT3_ID",
  "status":"published",
  "created_at":"2026-03-19T07:00:00Z",
  "updated_at":"2026-03-19T07:00:00Z"
}}
ENDJSON
)"
echo ""
echo "8/10 - TDTT 2025"

# Article 9 - The thao
post "$BASE/$ART_STORAGE/insert" "$(cat <<ENDJSON
{"documents":{
  "title":"Cục Thể dục thể thao triển khai công tác năm 2026: Hướng tới ASIAD và SEA Games",
  "summary":"Ngành thể thao Việt Nam triển khai kế hoạch năm 2026 với trọng tâm chuẩn bị vận động viên cho ASIAD 2026 tại Nhật Bản và SEA Games 2027 tại Malaysia.",
  "content":"<p>Ngày 26/12, Cục Thể dục Thể thao Việt Nam tổ chức hội nghị tổng kết công tác năm 2025 và triển khai công tác năm 2026. Sự kiện do Thứ trưởng Hoàng Đạo Cương chủ trì và chỉ đạo.</p><h2>Năm bản lề 2026</h2><p>Năm 2026 được xác định là năm bản lề quan trọng, ngành thể thao cần chuẩn bị vận động viên cho Đại hội Thể thao châu Á (ASIAD) 2026 tại Nhật Bản, tập trung phát triển thể thao trẻ và đảm bảo tính liên tục giữa chuẩn bị cho ASIAD 2026 và SEA Games 2027 tại Malaysia.</p><h2>Chiến lược phát triển</h2><p>Cục đề ra chiến lược phát triển toàn diện, kết hợp thể thao thành tích cao với thể thao quần chúng, nhằm nâng cao vị thế thể thao Việt Nam trên bản đồ thể thao khu vực và thế giới.</p><p>Hội nghị đánh giá năm 2025 là 'Dấu ấn toàn diện của ngành Thể dục thể thao trong giai đoạn bản lề phát triển,' với nhiều thành tích nổi bật trên trường quốc tế.</p>",
  "author":"Việt Hùng - Bộ VHTTDL",
  "thumbnail":"https://images.unsplash.com/photo-1569517282132-25d22f4573e6?w=800&q=80",
  "category_id":"$CAT3_ID",
  "status":"published",
  "created_at":"2026-03-18T13:00:00Z",
  "updated_at":"2026-03-18T13:00:00Z"
}}
ENDJSON
)"
echo ""
echo "9/10 - ASIAD SEA Games"

# Article 10 - The thao
post "$BASE/$ART_STORAGE/insert" "$(cat <<ENDJSON
{"documents":{
  "title":"Đội tuyển Việt Nam tại Vòng loại Asian Cup 2027: Cơ hội và thách thức",
  "summary":"Đội tuyển Việt Nam nằm ở bảng F vòng loại Asian Cup 2027 cùng Malaysia, Nepal và Lào, với mục tiêu giành vé dự vòng chung kết.",
  "content":"<p>Đội tuyển Việt Nam dưới sự dẫn dắt của HLV Kim Sang-sik đang tham gia vòng loại thứ ba AFC Asian Cup 2027, nằm ở bảng F cùng Malaysia, Nepal và Lào.</p><h2>Lịch thi đấu</h2><p>Vòng loại thứ ba diễn ra từ ngày 25/3/2025 đến 31/3/2026, với đội đứng đầu mỗi bảng giành suất tham dự vòng chung kết. Việt Nam được đánh giá là ứng viên hàng đầu với xếp hạng FIFA 116, cao hơn Malaysia (132), Nepal (175) và Lào (186).</p><h2>Kết quả tích cực</h2><p>Đội tuyển Việt Nam đã được xử thắng 3-0 trước Malaysia trong một trận đấu thuộc vòng loại, giúp cải thiện đáng kể vị trí trên bảng xếp hạng FIFA.</p><h2>Đội tuyển nữ</h2><p>Bên cạnh đội tuyển nam, đội tuyển nữ Việt Nam cũng đã đến Thâm Quyến, Trung Quốc để chuẩn bị cho hai trận giao hữu với đội chủ nhà trước thềm Giải vô địch Bóng đá nữ châu Á AFC 2026.</p>",
  "author":"VFF / 24h.com.vn",
  "thumbnail":"https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?w=800&q=80",
  "category_id":"$CAT3_ID",
  "status":"published",
  "created_at":"2026-03-17T16:00:00Z",
  "updated_at":"2026-03-17T16:00:00Z"
}}
ENDJSON
)"
echo ""
echo "10/10 - Asian Cup 2027"

echo ""
echo "=== DONE! Seed completed ==="
