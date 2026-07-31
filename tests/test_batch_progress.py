
from ocr_manga_title.db.crud import (
    create_batch_run,
    create_pipeline_run,
    update_batch_progress,
)


async def test_update_batch_progress_all_completed(db_session):
    batch = await create_batch_run(db_session, name="test", total_count=3)
    for _ in range(3):
        run = await create_pipeline_run(
            db_session,
            input_image_path="/tmp/test.png",
            batch_run_id=batch.id,
        )
        run.status = "completed"
    await db_session.commit()

    updated = await update_batch_progress(db_session, batch.id)
    assert updated is not None
    assert updated.completed_count == 3
    assert updated.failed_count == 0
    assert updated.status == "completed"
    assert updated.completed_at is not None


async def test_update_batch_progress_partial_failure(db_session):
    batch = await create_batch_run(db_session, name="test", total_count=3)

    r1 = await create_pipeline_run(
        db_session, input_image_path="/tmp/a.png", batch_run_id=batch.id
    )
    r1.status = "completed"

    r2 = await create_pipeline_run(
        db_session, input_image_path="/tmp/b.png", batch_run_id=batch.id
    )
    r2.status = "failed"

    r3 = await create_pipeline_run(
        db_session, input_image_path="/tmp/c.png", batch_run_id=batch.id
    )
    r3.status = "completed"
    await db_session.commit()

    updated = await update_batch_progress(db_session, batch.id)
    assert updated.completed_count == 2
    assert updated.failed_count == 1
    assert updated.status == "partial_failure"
    assert updated.completed_at is not None


async def test_update_batch_progress_still_processing(db_session):
    batch = await create_batch_run(db_session, name="test", total_count=3)

    r1 = await create_pipeline_run(
        db_session, input_image_path="/tmp/a.png", batch_run_id=batch.id
    )
    r1.status = "completed"

    await create_pipeline_run(
        db_session, input_image_path="/tmp/b.png", batch_run_id=batch.id
    )
    await db_session.commit()

    updated = await update_batch_progress(db_session, batch.id)
    assert updated.completed_count == 1
    assert updated.failed_count == 0
    assert updated.status == "pending"
    assert updated.completed_at is None


async def test_update_batch_progress_not_found(db_session):
    import uuid

    result = await update_batch_progress(db_session, uuid.uuid4())
    assert result is None


async def test_update_batch_progress_ignores_unrelated_runs(db_session):
    batch = await create_batch_run(db_session, name="test", total_count=1)

    await create_pipeline_run(
        db_session, input_image_path="/tmp/unrelated.png"
    )

    r = await create_pipeline_run(
        db_session, input_image_path="/tmp/batched.png", batch_run_id=batch.id
    )
    r.status = "completed"
    await db_session.commit()

    updated = await update_batch_progress(db_session, batch.id)
    assert updated.completed_count == 1
    assert updated.status == "completed"
