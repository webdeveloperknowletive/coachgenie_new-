import re
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str | None = None
    

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name_no_digits(cls, v: str) -> str:
        if v:
            v_clean = v.strip()
            if re.search(r"\d", v_clean):
                raise ValueError("Name cannot contain numbers.")
            return v_clean
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v_clean = str(v).strip()
        if not v_clean:
            return None
        digits = re.sub(r"\D", "", v_clean)
        if len(digits) != 10:
            raise ValueError("Phone number must be exactly 10 digits.")
        return digits

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Must contain uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Must contain lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Must contain a digit.")
        if not re.search(r"[@$!%*?&]", v):
            raise ValueError("Must contain special character (@$!%*?&).")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    role: str
    tenant_id: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
