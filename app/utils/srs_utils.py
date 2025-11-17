import logging
from app.utils.supabase_client import supabase
import re


logger = logging.getLogger(__name__)




def format_srs_to_markdown(document: dict) -> str:
    lines = []

    # Tiêu đề chính
    title = document.get("title", "Untitled Document").strip()
    lines.append(f"# {title}\n")

    # Mô tả chi tiết
    detail = document.get("detail", "").strip()
    if detail:
        lines.append("## Detailed Description\n")
        lines.append(detail)
        lines.append("")  # dòng trống

    # --- Hàm phụ để tách "1. ..." "2. ..." ---
    def split_requirements(text: str):
        text = text.strip()
        # Nếu có \n thì tách theo dòng
        if "\n" in text:
            items = [t.strip() for t in text.splitlines() if t.strip()]
        else:
            # Nếu không có \n thì tách theo số thứ tự (giữ nguyên phần số)
            items = re.findall(r"\d+\.[^0-9]+(?=\d+\.|$)", text)
            items = [t.strip() for t in items if t.strip()]
        return items

    # --- Functional Requirements ---
    func_req = document.get("functional_requirements", "").strip()
    if func_req:
        lines.append("## Functional Requirements\n")
        for line in split_requirements(func_req):
            lines.append(f"- {line}")
        lines.append("")

    # --- Non-Functional Requirements ---
    non_func_req = document.get("non_functional_requirements", "").strip()
    if non_func_req:
        lines.append("## Non-Functional Requirements\n")
        for line in split_requirements(non_func_req):
            lines.append(f"- {line}")
        lines.append("")

    markdown_output = "\n".join(lines).strip()
    return markdown_output
