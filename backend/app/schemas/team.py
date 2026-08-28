from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class InviteCreate(BaseModel):
    """owner 发起邀请：只允许授予 member / readonly，owner 不能通过邀请授予。"""
    email: EmailStr
    role: Literal["member", "readonly"] = "member"


class InviteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    email: str
    role: str
    expires_at: datetime


class AcceptInvite(BaseModel):
    code: str


class MemberUpdate(BaseModel):
    role: Literal["owner", "member", "readonly"]


class TeamMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: str
    created_at: datetime
