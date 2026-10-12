# from pydantic import BaseModel
# from typing import Optional, List
# from datetime import datetime
# import uuid


# class TemplateCreate(BaseModel):
#     name: str
#     channel: str
#     subject: Optional[str] = None
#     body: str
#     variables: Optional[List[str]] = None
#     is_active: bool = True


# class TemplateOut(BaseModel):
#     id: uuid.UUID
#     name: str
#     channel: str
#     subject: Optional[str] = None
#     body: str
#     is_active: bool

#     class Config:
#         from_attributes = True


# class SendNotificationRequest(BaseModel):
#     template_id: uuid.UUID
#     # recipient_ids: List[uuid.UUID]
#     recipients: List[RecipientContact]
#     variables: Optional[dict] = None


# class NotificationLogOut(BaseModel):
#     id: uuid.UUID
#     channel: str
#     recipient_ref: str
#     status: str
#     sent_at: Optional[datetime] = None
#     error_msg: Optional[str] = None

#     class Config:
#         from_attributes = True

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid


class TemplateCreate(BaseModel):
    name: str
    channel: str
    subject: Optional[str] = None
    body: str
    variables: Optional[List[str]] = None
    is_active: bool = True


class TemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    channel: str
    subject: Optional[str] = None
    body: str
    is_active: bool

    class Config:
        from_attributes = True


class RecipientContact(BaseModel):
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None


class SendNotificationRequest(BaseModel):
    template_id: uuid.UUID
    recipients: List[RecipientContact]
    variables: Optional[dict] = None


class NotificationLogOut(BaseModel):
    id: uuid.UUID
    channel: str
    recipient_ref: str
    subject: Optional[str] = None
    body: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    error_msg: Optional[str] = None

    class Config:
        from_attributes = True