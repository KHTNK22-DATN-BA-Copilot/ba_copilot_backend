from app.api.v1.design import generate_design
from app.core.step_task_registry import StepTaskRegistry


async def run_design_step(
    project_id: int,
    project_name: str,
    description: str,
    documents: list,
    db,
    current_user,
    notifier,
):
    await notifier.send(
        {
            "type": "step_start",
            "step": "design",
        }
    )

    for index, doc in enumerate(documents):
        doc_type = doc["type"]

        await notifier.send(
            {
                "type": "doc_start",
                "step": "design",
                "index": index,
                "doc_type": doc_type,
            }
        )

        result = await generate_design(
            project_id=project_id,
            project_name=project_name,
            design_type=doc_type,
            description=description,
            db=db,
            current_user=current_user,
        )

        await notifier.send(
            {
                "type": "doc_completed",
                "step": "design",
                "index": index,
                "doc_type": doc_type,
                "data": result.model_dump(),
            }
        )

    await notifier.send(
        {
            "type": "step_finished",
            "step": "design",
        }
    )

    StepTaskRegistry.finish(project_id, "design")
