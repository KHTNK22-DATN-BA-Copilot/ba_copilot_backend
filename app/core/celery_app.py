from celery import Celery
from app.core.config import settings

# don't delete all models below
from app.models.file import Files
from app.models.folder import Folder
from app.models.global_search_index import GlobalSearchIndex
from app.models.project_member import ProjectMember
from app.models.project import Project
from app.models.role import Role
from app.models.session import Chat_Session
from app.models.token import Token
from app.models.user_identity import UserIdentity
from app.models.user import User

celery_app = Celery(
    "ba_copilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.file_tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
)

# celery_app.autodiscover_tasks(["app.tasks"])
