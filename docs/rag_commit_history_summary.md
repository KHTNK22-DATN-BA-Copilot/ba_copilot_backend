# Tóm tắt 4 commit gần nhất liên quan đến RAG

Tài liệu này tổng hợp 4 commit gần nhất trong `ba_copilot_backend` có ảnh hưởng đến chức năng RAG, gồm: ingest tài liệu, chunking, embedding, lưu vector vào CSDL và chuẩn bị truy vấn similarity search.

## 1. Danh sách commit và thay đổi chính

| Commit | Thay đổi | Chức năng bị ảnh hưởng | Chức năng đó làm gì | Trạng thái hiện tại |
|---|---|---|---|---|
| `bbddaa389bc9bfc4ecb025697b69caee4d230b24` | `feat: add rag in upload file process` | Pipeline upload file, cấu hình RAG, schema lưu chunk | Tạo nền tảng RAG: thêm cấu hình OpenAI embedding, chunk size/overlap, tạo task `index_rag_task`, thêm bộ index `index_rag_chunks`, và tạo bảng/rpc `rag_chunks` | Đã có nền tảng ingest + lưu chunk, nhưng chưa thấy được nối hoàn chỉnh vào luồng upload cuối cùng trong code hiện tại |
| `5d9772881e914ab9c917dc581f26937f6eb4c3af` | `fix: change chunk_size to 500 tokens and overlap to 70 (15%)` | Logic chia chunk và tham số chunking | Chuyển chunking từ cắt theo ký tự sang cắt theo token; thêm fallback `tiktoken`; chia đoạn theo paragraph/sentence/word; cập nhật size/overlap | Đã cải thiện chất lượng chunk, phù hợp hơn cho embedding/RAG |
| `7d236b966d1a37f3488671fcbdaec206e634bede` | `fix: change rag_chunks schema` | Schema bảng `rag_chunks` và RPC similarity search | Đổi cột lưu ngữ cảnh từ `storage_key` sang `document_type`; cập nhật RPC `match_rag_chunks` để trả về `document_type` | Schema đã phù hợp hơn với phân loại tài liệu, nhưng đây mới là lớp dữ liệu, chưa phải lớp truy vấn ứng dụng |
| `1b27c1394b6c3c17a528bb150223b53976ec0e84` | `fix: change logic chunking and add logic to extract document_type` | Task `index_rag_task` và hàm `index_rag_chunks` | Suy ra `document_type` từ metadata tài liệu thay vì lấy từ storage path; cập nhật logic chunking/lưu dữ liệu cho đúng ngữ cảnh tài liệu | Bổ sung đúng hơn về mặt nghiệp vụ, nhưng vẫn phụ thuộc vào việc task có được gọi trong pipeline hay không |

## 2. Các chức năng RAG hiện có trong code

### 2.1 `process_markdown_task`

Chức năng này chuyển file upload sang Markdown, lưu lại đường dẫn Markdown trên Supabase và trả về nội dung Markdown để các bước sau dùng tiếp.

### 2.2 `extract_metadata_task`

Task này gọi AI service để trích metadata của tài liệu, rồi lưu metadata vào `file_metadata`. Đây là nguồn để suy ra `document_type` cho RAG.

### 2.3 `index_rag_task`

Task này nhận `md_text`, lấy `file_metadata`, suy ra `document_type`, rồi gọi `index_rag_chunks` để:

- chia tài liệu thành chunk theo token
- tạo embedding bằng OpenAI
- xóa chunk cũ theo `file_id`
- insert các chunk mới vào bảng `rag_chunks`

### 2.4 `index_rag_chunks`

Đây là hàm lõi của RAG ingest. Nó thực hiện toàn bộ vòng đời indexing cho một file: chunking, embedding, batch insert, và gắn thông tin tài liệu vào từng chunk.

### 2.5 `match_rag_chunks`

Đây là RPC trong database để similarity search trên vector embedding. Hàm này chuẩn bị sẵn lớp truy vấn để lấy các chunk liên quan theo cosine similarity.

## 3. Mức độ hoàn thiện hiện tại

Trong repo hiện tại, phần RAG đã hoàn thành khá tốt ở lớp nền tảng dữ liệu và indexing:

- đã có cấu hình môi trường cho embedding và chunking
- đã có hàm chia chunk theo token
- đã có task tạo embedding và lưu `rag_chunks`
- đã có schema `rag_chunks` và RPC similarity search trong database
- đã có logic xác định `document_type` từ metadata tài liệu

Tuy nhiên, phần này chưa hoàn thiện end-to-end:

- trong `app/api/v1/files.py`, pipeline hiện tại chỉ chain `process_markdown_task` -> `extract_metadata_task`, chưa thấy gọi `index_rag_task`
- chưa thấy backend API nào sử dụng `match_rag_chunks` để truy vấn RAG
- chưa thấy test chuyên biệt cho ingest/search RAG trong thư mục `tests/`

Kết luận ngắn: phần RAG hiện ở mức đã hoàn thành lớp ingest/indexing và schema nền, nhưng chưa hoàn chỉnh ở tầng tích hợp runtime và truy vấn đầu ra.

## 4. Phạm vi mà `rag_schema.sql` đã cover

- **Lớp cơ sở dữ liệu (DB schema):** `rag_schema.sql` tạo bảng `rag_chunks` với các cột cần thiết để lưu chunk: `id`, `file_id`, `project_id`, `document_type`, `chunk_index`, `content`, `token_count`, `embedding` (kiểu `VECTOR(3072)`), và `created_at`.
- **Chỉ mục hiệu năng:** Tạo index theo `project_id`, `file_id` và index vector dùng `ivfflat` với `vector_cosine_ops` (tham số `lists = 100`) để hỗ trợ tìm kiếm tương đồng quy mô lớn.
- **RPC similarity search:** Định nghĩa hàm `match_rag_chunks(query_embedding, match_count, project_id_filter, min_similarity)` trả về các chunk có similarity >= `min_similarity`, áp dụng filter theo `project_id` và sắp xếp theo khoảng cách embedding (`<=>`) để lấy các kết quả gần nhất.
- **Tương thích embedding dimension:** Schema sử dụng `VECTOR(3072)`, trùng khớp với kích thước embedding của model `text-embedding-3-large` (được cấu hình trong code), nên vector lưu trữ và truy vấn về mặt chiều là phù hợp.

Những gì `rag_schema.sql` **không** cover (cần lưu ý):

- **Provisioning / migration automation:** Tệp chỉ chứa SQL DDL; repo chưa cho thấy migration script tự động chạy (ví dụ Alembic) để áp dụng schema vào DB production.
- **Quyền truy cập / an ninh DB:** Không có ràng buộc quyền, role, hoặc kiểm soát truy cập cho RPC/index.
- **Tầng ứng dụng:** Schema không triển khai các hàm truy vấn ở tầng ứng dụng (API hoặc service) — phải có code gọi RPC `match_rag_chunks` hoặc thực thi SQL tương đương để thực hiện retrieval.
- **Quản lý lifecycle của chỉ mục vector:** `ivfflat` cần được khởi tạo/rehash/ANALYZE sau khi load dữ liệu lớn để có hiệu năng tốt; script không chứa các bước này.

Tóm lại: `rag_schema.sql` fully covers dữ liệu và truy vấn similarity ở tầng DB (schema + RPC + index), và nó khớp với thiết lập embedding trong code. Để hoàn thiện end-to-end cần bổ sung: migration automation, tích hợp gọi RPC từ backend API, và bước quản lý/khởi tạo index vector trên DB.
