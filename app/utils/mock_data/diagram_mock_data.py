# app/utils/mock_data.py


def get_mock_data(diagram_type: str):
    """
    Trả về mock data tương ứng với loại diagram.
    Hỗ trợ:
      - Use Case Diagram (.md / Mermaid format)
      - Class Diagram (.md / Mermaid format)
    """

    diagram_type_lower = diagram_type.lower()

    # -------------------------------
    # Mock data: Use Case Diagram
    # -------------------------------
    if "usecase" in diagram_type_lower:
        return {
            "description": (
                "This Use Case Diagram represents a complete user interaction flow "
                "for an online event ticketing system. It includes both external "
                "actors (User, Event Organizer, Admin) and the system's main use cases "
                "such as account management, event browsing, and ticket purchasing."
            ),
            "diagram_content": """```mermaid
            %% Use Case Diagram - Event Ticketing System
            ---
            title: Use Case Diagram - Event Ticketing System
            ---

            graph TD
                %% Actors
                A[User]
                B[Event Organizer]
                C[Admin]
                S((Event Ticketing System))

                %% Use Cases
                UC1((Register Account))
                UC2((Login))
                UC3((Browse Events))
                UC4((Purchase Ticket))
                UC5((View Ticket History))
                UC6((Create Event))
                UC7((Manage Event Details))
                UC8((Approve Events))
                UC9((View Reports))

                %% Relationships
                A --> UC1
                A --> UC2
                A --> UC3
                A --> UC4
                A --> UC5

                B --> UC6
                B --> UC7

                C --> UC8
                C --> UC9

                UC4 -->|includes| UC2
                UC6 -->|extends| UC7

                %% System boundary
                subgraph System Boundary
                    UC1
                    UC2
                    UC3
                    UC4
                    UC5
                    UC6
                    UC7
                    UC8
                    UC9
                end
            ```""",
        }

    # -------------------------------
    # Mock data: Class Diagram
    # -------------------------------
    elif "class" in diagram_type_lower:
        return {
            "description": (
                "This Class Diagram shows the core structure of an online ticketing system. "
                "It includes classes for users, events, tickets, and payments, "
                "with their key attributes and relationships."
            ),
            "diagram_content": """```mermaid
            %% Class Diagram - Event Ticketing System
            ---
            title: Class Diagram - Event Ticketing System
            ---

            classDiagram
                class User {
                    +int id
                    +string name
                    +string email
                    +string password
                    +register()
                    +login()
                }

                class Event {
                    +int id
                    +string title
                    +string description
                    +Date date
                    +double price
                    +create()
                    +update()
                }

                class Ticket {
                    +int id
                    +string seatNumber
                    +Date purchaseDate
                    +generateQR()
                }

                class Payment {
                    +int id
                    +string method
                    +double amount
                    +Date date
                    +process()
                }

                class Admin {
                    +approveEvent()
                    +viewReports()
                }

                %% Relationships
                User "1" --> "*" Ticket : purchases >
                Ticket "*" --> "1" Event : belongs to >
                User "1" --> "*" Payment : makes >
                Event "1" --> "*" Ticket : has >
                Admin --> Event : manages >
            ```""",
        }

    elif "activity" in diagram_type_lower:
        return {
            "description": (
                "This Activity Diagram demonstrates the process flow for purchasing a ticket "
                "in the Event Ticketing System. It includes key actions, decision nodes, and "
                "synchronization points to represent system logic."
            ),
            "diagram_content": """```mermaid
            %% Activity Diagram - Ticket Purchase Flow
            ---
            title: Activity Diagram - Ticket Purchase Flow
            ---

            flowchart TD
                start([Start])
                login{User logged in?}
                browse[Browse Events]
                select[Select Event]
                choose[Choose Ticket Type & Quantity]
                pay[Make Payment]
                confirm[Payment Successful?]
                generate[Generate e-Ticket]
                fail[Show Error Message]
                end([End])

                %% Flow connections
                start --> login
                login -->|No| browse
                login -->|Yes| browse
                browse --> select
                select --> choose
                choose --> pay
                pay --> confirm
                confirm -->|Yes| generate
                confirm -->|No| fail
                generate --> end
                fail --> end
            ```""",
        }
    # -------------------------------
    # Default fallback
    # -------------------------------
    return {
        "description": "Mock diagram data unavailable for this diagram type.",
        "diagram_content": "```mermaid\ngraph TD; A-->B;\n```",
    }
