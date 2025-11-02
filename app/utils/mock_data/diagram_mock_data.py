# app/utils/mock_data.py


def get_mock_data(diagram_type: str):
    """
    Trả về mock data tương ứng với loại diagram.
    Hiện tại hỗ trợ Use Case Diagram (.md / Mermaid format).
    """

    diagram_type_lower = diagram_type.lower()

    if "usecase" in diagram_type_lower:
        return {
            "description": (
                "This is a mock Use Case Diagram representing a typical user interaction flow "
                "in the system. It includes actors, use cases, and their relationships."
            ),
            "diagram_content": """```mermaid
%% Use Case Diagram Mock Data (Markdown format)
---
title: Use Case Diagram - User Login Flow
---
graph TD
    A[User] -->|initiates| B((Login))
    A -->|requests| C((Register))
    A -->|forgets password| D((Reset Password))
    B --> E{System}
    E -->|verifies credentials| F((Validate User))
    F -->|returns result| A
```""",
        }

    return {
        "description": "Mock diagram data unavailable for this diagram type.",
        "diagram_content": "```mermaid\ngraph TD; A-->B;\n```",
    }
