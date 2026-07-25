import re
from typing import Any, Dict


def process_llm_response(raw_llm_output: str) -> Dict[str, Any]:
   
    if not isinstance(raw_llm_output, str):
        return {
            "response": {
                "content": str(raw_llm_output),
                "summary": "No summary provided.",
            }
        }

    text = raw_llm_output.strip()

    if not text:
        return {
            "response": {
                "content": "",
                "summary": "No summary provided.",
            }
        }

 
    text = _remove_outer_code_fence(text)

   
    return _parse_marker_format(text)

def _remove_outer_code_fence(text: str) -> str:
    text = text.strip()

    match = re.match(
        r"^```[a-zA-Z0-9_-]*\s*\n([\s\S]*?)\n```$",
        text,
    )

    if match:
        return match.group(1).strip()

    return text


def _parse_marker_format(text: str) -> Dict[str, Any]:
    summary_match = re.search(
        r"===SUMMARY===\s*\n([\s\S]*?)(?=\n===\w+===|$)",
        text,
    )

    summary = (
        summary_match.group(1).strip() if summary_match else "No summary provided."
    )


    html_match = re.search(
        r"===HTML===\s*\n([\s\S]*?)(?=\n===\w+===|$)",
        text,
    )

    css_match = re.search(
        r"===CSS===\s*\n([\s\S]*?)(?=\n===\w+===|$)",
        text,
    )

    if html_match or css_match:
        html = html_match.group(1).strip() if html_match else ""
        css = css_match.group(1).strip() if css_match else ""

        return {
            "response": {
                "content": {
                    "html": html,
                    "css": css,
                },
                "summary": summary,
            }
        }

    content_match = re.search(
        r"===CONTENT===\s*\n([\s\S]*?)$",
        text,
    )

    if content_match:
        content = content_match.group(1).strip()

        return {
            "response": {
                "content": content,
                "summary": summary,
            }
        }

 
    content = re.sub(
        r"===SUMMARY===\s*\n[\s\S]*?(?=\n===\w+===|$)",
        "",
        text,
    ).strip()

    return {
        "response": {
            "content": content,
            "summary": summary,
        }
    }

