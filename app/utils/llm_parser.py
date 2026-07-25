import json
import re


def process_llm_response(raw_llm_output: str) -> dict:
    """Xử lý output từ LLM để tạo ra JSON object chứa 'content' và 'summary'

    đúng chuẩn format.
    """
    if not isinstance(raw_llm_output, str):
        return {"content": str(raw_llm_output), "summary": "No summary provided."}

    text = raw_llm_output.strip()

    # 1. Bóc tách khối code block nếu LLM cố tình chèn ```markdown hoặc ```
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text).strip()

    # 2. Tìm nội dung bên trong thẻ <summary>...</summary>
    summary_pattern = r"<summary>(.*?)</summary>"
    summary_match = re.search(summary_pattern, text, flags=re.DOTALL)

    if summary_match:
        # Lấy nội dung summary và làm sạch dòng thừa
        summary = summary_match.group(1).strip()
        # Xóa thẻ <summary> ra khỏi text để giữ lại phần Content (Markdown) nguyên bản
        content = re.sub(summary_pattern, "", text, flags=re.DOTALL).strip()
    else:
        # Fallback an toàn nếu LLM quên sinh thẻ <summary>
        summary = "No summary provided."
        content = text

    # 3. Trả về Dictionary đúng cấu trúc yêu cầu
    return {"content": content, "summary": summary}
