"""Centralized Plan & Entitlement Matrix for CoachGenie Enterprise SaaS."""
from typing import Dict, Any

CANONICAL_PLANS: Dict[str, Dict[str, Any]] = {
    "starter": {
        "name": "Starter",
        "description": "For individual tutors and emerging coaching centers",
        "quotas": {
            "max_students": 100,
            "max_staff": 5,
            "max_batches": 5,
            "storage_mb": 1024,
        },
        "features": {
            "ai_copilot_enabled": False,
            "custom_roles_enabled": False,
            "custom_fields_enabled": True,
            "advanced_analytics_enabled": False,
            "whatsapp_notifications_enabled": False,
        },
    },
    "growth": {
        "name": "Growth",
        "description": "For expanding institutes requiring multi-batch management and automation",
        "quotas": {
            "max_students": 500,
            "max_staff": 20,
            "max_batches": 25,
            "storage_mb": 5120,
        },
        "features": {
            "ai_copilot_enabled": True,
            "custom_roles_enabled": True,
            "custom_fields_enabled": True,
            "advanced_analytics_enabled": True,
            "whatsapp_notifications_enabled": True,
        },
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "For large multi-branch coaching institutes with unlimited scale",
        "quotas": {
            "max_students": 5000,
            "max_staff": 100,
            "max_batches": 200,
            "storage_mb": 51200,
        },
        "features": {
            "ai_copilot_enabled": True,
            "custom_roles_enabled": True,
            "custom_fields_enabled": True,
            "advanced_analytics_enabled": True,
            "whatsapp_notifications_enabled": True,
        },
    },
}

# Legacy alias mappings for backward compatibility
PLAN_ALIASES = {
    "basic": "starter",
    "free": "starter",
    "pro": "growth",
    "standard": "growth",
    "enterprise": "enterprise",
}


def normalize_plan_name(plan: str | None) -> str:
    """Normalize any plan string or alias to canonical plan name."""
    if not plan:
        return "starter"
    cleaned = str(plan).strip().lower()
    return PLAN_ALIASES.get(cleaned, cleaned if cleaned in CANONICAL_PLANS else "starter")


def get_base_plan_config(plan_name: str | None) -> Dict[str, Any]:
    """Retrieve base plan quotas and feature flags."""
    canonical = normalize_plan_name(plan_name)
    return CANONICAL_PLANS.get(canonical, CANONICAL_PLANS["starter"])
