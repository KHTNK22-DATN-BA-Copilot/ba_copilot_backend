import logging
import uuid
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.rag_database import get_rag_db
from app.models.deletion_job import DeletionJob
from app.models.file import Files
from app.utils.file_handling import delete_file_from_supabase_strict
from app.utils.rag_indexer import delete_rag_chunks_for_file

logger = logging.getLogger(__name__)


AI_GENERATED_FILE_CATEGORY = "ai gen"


async def background_hard_delete_files(file_ids: list[str]):
    """Process queued physical cleanup for files hidden by soft delete."""
    if not file_ids:
        return

    db_gen = get_db()
    db = next(db_gen)
    rag_db_gen = get_rag_db()
    rag_db = next(rag_db_gen)

    completed_count = 0
    failed_ids = []

    logger.info(f"Starting deletion cleanup for {len(file_ids)} files")

    try:
        
        jobs = (
            db.query(DeletionJob)
            .filter(
                DeletionJob.file_id.in_(file_ids),
                DeletionJob.status.in_(["pending", "failed", "processing"]),
            )
            .order_by(DeletionJob.created_at.asc())
            .all()
        )

        if not jobs:
            files_to_queue = db.query(Files).filter(Files.id.in_(file_ids)).all()
            for file_record in files_to_queue:
                db.add(
                    DeletionJob(
                        file_id=file_record.id,
                        project_id=file_record.project_id,
                        storage_path=file_record.storage_path,
                        storage_md_path=file_record.storage_md_path,
                        status="pending",
                    )
                )
            db.commit()
            jobs = (
                db.query(DeletionJob)
                .filter(
                    DeletionJob.file_id.in_(file_ids),
                    DeletionJob.status == "pending",
                )
                .order_by(DeletionJob.created_at.asc())
                .all()
            )

        logger.info(f"Found {len(jobs)} deletion jobs")

        for job in jobs:
            try:
                logger.info(
                    f"Processing deletion job={job.id}, file_id={job.file_id}"
                )

                job.status = "processing"
                job.attempt_count = (job.attempt_count or 0) + 1
                job.last_error = None
                db.commit()

                if job.file_id:
                    try:
                        delete_rag_chunks_for_file(rag_db, file_id=str(job.file_id))
                        rag_db.commit()
                    except Exception:
                        rag_db.rollback()
                        raise

                if job.storage_path:
                    await delete_file_from_supabase_strict(job.storage_path)
                if job.storage_md_path:
                    await delete_file_from_supabase_strict(job.storage_md_path)

                if job.file_id:
                    file_record = (
                        db.query(Files).filter(Files.id == job.file_id).first()
                    )
                    if file_record:
                        if file_record.file_category == AI_GENERATED_FILE_CATEGORY:
                            file_record.status = "deleted"
                        else:
                            db.delete(file_record)

                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.last_error = None
                db.commit()

                completed_count += 1
                logger.info(f"Completed deletion job={job.id}, file_id={job.file_id}")

            except Exception as exc:
                db.rollback()
                rag_db.rollback()

                failed_job_id = job.id
                job = (
                    db.query(DeletionJob)
                    .filter(DeletionJob.id == failed_job_id)
                    .first()
                )
                if job:
                    job.status = "failed"
                    job.last_error = str(exc)
                    db.commit()
                    failed_ids.append(str(job.file_id))

                logger.error(
                    f"Deletion job failed job={failed_job_id}, "
                    f"file_id={job.file_id if job else None}: {exc}"
                )

    finally:
        db_gen.close()
        rag_db_gen.close()

        logger.info(
            f"File deletion task completed. "
            f"Completed: {completed_count}/{len(file_ids)}, "
            f"Failed: {len(failed_ids)}"
        )
        if failed_ids:
            logger.error(f"Failed file IDs: {failed_ids}")
