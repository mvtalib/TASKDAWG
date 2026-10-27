"""Task CRUD. Every query is scoped to the logged-in user."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Task, User
from ..schemas import ReorderIn, TaskCreate, TaskOut, TaskStats, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _get_owned_task(db: Session, user: User, task_id: int) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if task is None:
        # 404 (not 403) so other users' task ids aren't revealed.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found.")
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(
    filter: Literal["all", "pending", "in_progress", "completed"] = Query(
        "all",
        description="'pending' means every task that isn't completed, like the To Do filter in the UI.",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Task).where(Task.user_id == user.id)
    if filter == "pending":
        query = query.where(Task.status != "completed")
    elif filter in ("in_progress", "completed"):
        query = query.where(Task.status == filter)
    # Manual order first (drag and drop), newest first as the tie-breaker.
    query = query.order_by(Task.position.asc(), Task.id.desc())
    return db.scalars(query).all()


@router.get("/stats", response_model=TaskStats)
def task_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    row = db.execute(
        select(
            func.count(Task.id),
            func.coalesce(func.sum(case((Task.status != "completed", 1), else_=0)), 0),
            func.coalesce(func.sum(case((Task.status == "in_progress", 1), else_=0)), 0),
            func.coalesce(func.sum(case((Task.status == "completed", 1), else_=0)), 0),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Task.status != "completed")
                            & Task.due_date.is_not(None)
                            & (Task.due_date < now),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(Task.user_id == user.id)
    ).one()
    return TaskStats(
        total=row[0], pending=row[1], in_progress=row[2], completed=row[3], overdue=row[4]
    )


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    # New tasks go to the top of the list, like the front-end does.
    lowest = db.scalar(select(func.min(Task.position)).where(Task.user_id == user.id))
    position = 0 if lowest is None else lowest - 1

    task = Task(user_id=user.id, position=position, **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_tasks(
    data: ReorderIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Save a new manual order. `ids` is the list of task ids from top to bottom."""
    tasks = db.scalars(select(Task).where(Task.user_id == user.id, Task.id.in_(data.ids))).all()
    if len(tasks) != len(data.ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "One or more task ids were not found.")

    by_id = {task.id: task for task in tasks}
    for index, task_id in enumerate(data.ids):
        by_id[task_id].position = index
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_owned_task(db, user, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = _get_owned_task(db, user, task_id)
    for field in data.model_fields_set:
        setattr(task, field, getattr(data, field))
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    task = _get_owned_task(db, user, task_id)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
