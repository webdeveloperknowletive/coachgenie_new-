import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import CustomRole
from app.utils.security import hash_password
from tests.conftest import make_access_token


@pytest.mark.asyncio
async def test_custom_role_crud_and_permissions(client: AsyncClient, db_session: AsyncSession, tenant: Tenant, owner_headers: dict):
    # 1. Get available permissions metadata
    meta_res = await client.get("/api/v1/roles/meta/permissions", headers=owner_headers)
    assert meta_res.status_code == 200
    meta_data = meta_res.json()
    assert "resources" in meta_data
    assert "actions" in meta_data
    assert "fees" in meta_data["resources"]
    assert "create" in meta_data["actions"]

    # 2. Create a custom role: "Accountant"
    role_payload = {
        "name": "Institute Accountant",
        "description": "Handles fees and invoices",
        "permissions": ["fees.view", "fees.create", "fees.edit", "reports.view"],
    }
    create_res = await client.post("/api/v1/roles/", json=role_payload, headers=owner_headers)
    assert create_res.status_code == 201
    created_role = create_res.json()
    role_id = created_role["id"]
    assert created_role["name"] == "Institute Accountant"
    assert "fees.view" in created_role["permissions"]

    # 3. List custom roles for tenant
    list_res = await client.get("/api/v1/roles/", headers=owner_headers)
    assert list_res.status_code == 200
    roles_list = list_res.json()
    assert any(r["id"] == role_id for r in roles_list)

    # 4. Update custom role
    update_res = await client.patch(
        f"/api/v1/roles/{role_id}",
        json={"description": "Updated description for accountant"},
        headers=owner_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated description for accountant"

    # 5. Create a staff user assigned to this custom role
    staff_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="accountant@example.com",
        password_hash=hash_password("Pass123!"),
        role="custom",
        custom_role_id=uuid.UUID(role_id),
        first_name="John",
        last_name="Accountant",
        is_active=True,
        is_verified=True,
    )
    db_session.add(staff_user)
    await db_session.flush()

    staff_token = make_access_token(staff_user, tenant)
    staff_headers = {
        "Authorization": f"Bearer {staff_token}",
        "X-Tenant-Subdomain": tenant.subdomain,
    }

    # 6. Verify staff user can access permitted endpoints (/roles view is denied, but /fees is allowed)
    # Roles router requires `require_permission("roles", "view")` -> Accountant doesn't have roles.view
    roles_denied = await client.get("/api/v1/roles/", headers=staff_headers)
    assert roles_denied.status_code == 403

    # Fees endpoint check: has permission fees.view
    fees_res = await client.get("/api/v1/fees/invoices", headers=staff_headers)
    assert fees_res.status_code == 200

    # 7. Attempt to delete custom role while staff user is assigned -> should fail with 409 Conflict
    del_conflict = await client.delete(f"/api/v1/roles/{role_id}", headers=owner_headers)
    assert del_conflict.status_code == 409

    # Reassign staff user and delete
    staff_user.custom_role_id = None
    await db_session.flush()

    del_res = await client.delete(f"/api/v1/roles/{role_id}", headers=owner_headers)
    assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_dynamic_rbac_tenant_isolation(client: AsyncClient, db_session: AsyncSession, tenant: Tenant, owner_headers: dict):
    # Create Tenant B
    tenant_b = Tenant(
        id=uuid.uuid4(),
        name="Tenant B",
        subdomain=f"tenant-b-{uuid.uuid4().hex[:6]}",
        plan="basic",
        is_active=True,
        settings={},
    )
    db_session.add(tenant_b)
    await db_session.flush()

    # Create role in Tenant A
    role_a = CustomRole(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Tenant A Role",
        permissions=["leads.view"],
        is_active=True,
    )
    db_session.add(role_a)
    await db_session.flush()

    # Create owner user for Tenant B
    owner_b = User(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        email="owner_b@example.com",
        password_hash=hash_password("Pass123!"),
        role="owner",
        first_name="Owner",
        last_name="B",
        is_active=True,
        is_verified=True,
    )
    db_session.add(owner_b)
    await db_session.flush()

    token_b = make_access_token(owner_b, tenant_b)
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Tenant-Subdomain": tenant_b.subdomain,
    }

    # Tenant B tries to view Tenant A's custom role -> 404 Not Found
    get_res = await client.get(f"/api/v1/roles/{role_a.id}", headers=headers_b)
    assert get_res.status_code == 404

    # Tenant B tries to delete Tenant A's custom role -> 404 Not Found
    del_res = await client.delete(f"/api/v1/roles/{role_a.id}", headers=headers_b)
    assert del_res.status_code == 404
