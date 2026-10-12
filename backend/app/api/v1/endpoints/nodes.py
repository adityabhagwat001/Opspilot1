import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.node import Node, NodeStatus
from app.models.audit import AuditLog
from app.schemas.node import NodeRegister, NodeResponse, NodeRegisterResponse
from app.core.security import generate_node_api_key, hash_api_key
from app.api.deps import get_current_user, get_current_operator, get_current_admin

router = APIRouter()


@router.post(
    "/register",
    response_model=NodeRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Infrastructure Host Node",
    description="Registers a new node and generates a unique, cryptographically signed API key for the agent probe. Requires OPERATOR or ADMIN role."
)
async def register_node(
    payload: NodeRegister,
    current_user: User = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db)
) -> NodeRegisterResponse:
    node_id = payload.id.strip() if payload.id else f"srv-{uuid.uuid4().hex[:8]}"

    # Check for existing node_id
    existing = await db.execute(select(Node).where(Node.id == node_id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Node identifier '{node_id}' is already registered."
        )

    # Generate Agent API Key
    plain_api_key = generate_node_api_key()
    key_hash = hash_api_key(plain_api_key)

    new_node = Node(
        id=node_id,
        name=payload.name,
        hostname=payload.hostname,
        ip_address=payload.ip_address,
        api_key_hash=key_hash,
        status=NodeStatus.ONLINE,
        os_info=payload.os_info
    )
    db.add(new_node)

    # Audit entry
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="NODE_REGISTERED",
        resource=f"node:{new_node.id}",
        details=f"Node {new_node.name} ({new_node.hostname}) registered by {current_user.email}"
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(new_node)

    return NodeRegisterResponse(
        node=NodeResponse.model_validate(new_node),
        api_key=plain_api_key,
        message="Node successfully registered. Securely configure your agent with this API key."
    )


@router.get(
    "",
    response_model=List[NodeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Registered Nodes",
    description="Retrieves a list of all registered infrastructure hosts. Requires authenticated user."
)
async def list_nodes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[Node]:
    result = await db.execute(select(Node).order_by(Node.created_at.desc()))
    nodes = result.scalars().all()
    return list(nodes)


@router.get(
    "/{node_id}",
    response_model=NodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Node Details",
    description="Returns detailed telemetry metadata for a specific registered node."
)
async def get_node(
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Node:
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node with ID '{node_id}' not found."
        )
    return node


@router.delete(
    "/{node_id}",
    status_code=status.HTTP_200_OK,
    summary="Decommission Node",
    description="Deregisters and deletes an infrastructure node. Requires ADMIN role."
)
async def delete_node(
    node_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> dict:
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node with ID '{node_id}' not found."
        )

    await db.delete(node)

    audit_entry = AuditLog(
        user_id=current_user.id,
        action="NODE_DECOMMISSIONED",
        resource=f"node:{node_id}",
        details=f"Node {node_id} deleted by admin {current_user.email}"
    )
    db.add(audit_entry)
    await db.commit()

    return {"status": "success", "message": f"Node '{node_id}' has been decommissioned."}
