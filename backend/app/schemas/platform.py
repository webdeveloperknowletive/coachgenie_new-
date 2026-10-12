import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class PlatformMetricsOut(BaseModel):
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    total_students: int
    total_staff: int
    plan_distribution: Dict[str, int]
    total_invoiced_amount: float
    total_collected_revenue: float


class PlatformTenantOut(BaseModel):
    id: uuid.UUID
    name: str
    subdomain: str
    plan: str
    is_active: bool
    created_at: Optional[datetime] = None
    student_count: int = 0
    staff_count: int = 0
    batch_count: int = 0
    settings: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class PlatformTenantDetailOut(BaseModel):
    tenant: PlatformTenantOut
    entitlements: Dict[str, Any]


class PlanUpdateIn(BaseModel):
    plan: str = Field(..., description="Canonical plan: 'starter', 'growth', or 'enterprise'")


class QuotaOverridesIn(BaseModel):
    max_students: Optional[int] = Field(None, ge=1, le=100000)
    max_staff: Optional[int] = Field(None, ge=1, le=10000)
    max_batches: Optional[int] = Field(None, ge=1, le=5000)
    storage_mb: Optional[int] = Field(None, ge=100, le=1048576)
    features: Optional[Dict[str, bool]] = None


class DiagnosticTokenOut(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_in_seconds: int = 900
    tenant_id: uuid.UUID
    impersonated_email: str
    issued_for_super_admin: str


class TenantProvisionIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    subdomain: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    plan: str = Field("starter", description="starter, growth, enterprise")
    owner_email: str = Field(..., min_length=5, max_length=255)
    owner_password: str = Field(..., min_length=8)
    owner_first_name: str = Field("Institute", min_length=1)
    owner_last_name: str = Field("Owner", min_length=1)


class PlatformHealthOut(BaseModel):
    database_status: str
    database_latency_ms: float
    scheduler_status: str
    outbox_backlog_count: int
    smtp_status: str
    web_push_status: str
    ai_status: str
    timestamp: datetime


class AIModelRouting(BaseModel):
    copilot_model: str = "llama3-70b-8192"
    doubt_solver_model: str = "llama3-70b-8192"
    career_guidance_model: str = "llama3-8b-8192"
    analytics_assistant_model: str = "llama3-70b-8192"


class AIPlatformConfig(BaseModel):
    model_config = {"protected_namespaces": ()}

    enabled: bool = True
    active_provider: str = "groq"
    available_providers: List[str] = ["groq", "openai-compatible", "render-copilot"]
    model_routing: AIModelRouting = Field(default_factory=AIModelRouting)
    last_health_check: Optional[datetime] = None
    average_latency_ms: float = 240.0


class FeatureFlagsPlatformOut(BaseModel):
    features: Dict[str, bool]


class FeatureFlagsUpdateIn(BaseModel):
    features: Dict[str, bool]


class PlatformFinanceOut(BaseModel):
    currency: str = "INR"
    mrr: float
    arr: float
    active_subscriptions: Dict[str, int]
    tier_pricing_monthly: Dict[str, float]
    total_lifetime_subscription_revenue: float
    total_student_invoiced_across_tenants: float
    total_student_collected_across_tenants: float

