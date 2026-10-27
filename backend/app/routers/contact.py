"""Contact form on the home page."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ContactMessage
from ..schemas import ContactIn, ContactOut

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def submit_contact(data: ContactIn, db: Session = Depends(get_db)):
    db.add(ContactMessage(**data.model_dump()))
    db.commit()
    return ContactOut()
