from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from ..config.database import get_db_cursor
from ..auth.microsoft_auth import get_current_user, require_permission, require_owner
from ..models.schemas import User, UserUpdate, Role

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current logged-in user information and permissions"""
    return current_user


@router.get("/", response_model=List[dict])
async def get_all_users(
    current_user: dict = Depends(require_permission("can_manage_users"))
):
    """Get all users - requires user management permission"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT u.*, r.display_name as role_display_name
            FROM gpu_monitor.users u
            LEFT JOIN gpu_monitor.roles r ON u.role = r.role_name
            ORDER BY u.created_at ASC
        """)
        users = cursor.fetchall()
        return [dict(user) for user in users]


@router.post("/")
async def create_user(
    user_data: dict,
    current_user: dict = Depends(require_permission("can_manage_users"))
):
    """Create a new user - admin or owner can do this"""
    email = user_data.get('email')
    name = user_data.get('name')
    azure_user_id = user_data.get('azure_user_id')
    role = user_data.get('role', 'viewer')
    
    if not email or not azure_user_id:
        raise HTTPException(status_code=400, detail="Email and azure_user_id are required")
    
    # Validate role
    valid_roles = ['admin', 'owner', 'editor', 'viewer']
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    # Check permissions for role assignment
    current_user_role = current_user['permissions'].get('role_name', 'viewer')
    
    # Owner cannot edit other owners
    if current_user_role == 'owner' and role in ['owner', 'admin']:
        raise HTTPException(
            status_code=403, 
            detail="Owners cannot create admin or owner roles"
        )
    
    with get_db_cursor(commit=True) as cursor:
        # Verify role exists in roles table
        cursor.execute(
            "SELECT role_name FROM gpu_monitor.roles WHERE role_name = %s",
            (role,)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Invalid role")
        
        try:
            # Create user
            cursor.execute("""
                INSERT INTO gpu_monitor.users (email, name, azure_user_id, role, is_active, last_login)
                VALUES (%s, %s, %s, %s, true, CURRENT_TIMESTAMP)
                RETURNING *
            """, (email, name, azure_user_id, role))
            
            new_user = cursor.fetchone()
            return {"success": True, "user": dict(new_user)}
            
        except Exception as e:
            # If user already exists, return conflict error
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                raise HTTPException(status_code=409, detail="User already exists")
            raise HTTPException(status_code=500, detail=str(e))


@router.put("/{email}/role")
async def update_user_role(
    email: str,
    role_data: dict,
    current_user: dict = Depends(require_permission("can_manage_users"))
):
    """Update user role - admin or owner can do this"""
    new_role = role_data.get('role')
    
    if not new_role:
        raise HTTPException(status_code=400, detail="Role is required")
    
    # Validate role
    valid_roles = ['admin', 'owner', 'editor', 'viewer']
    if new_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    # Get current user's role
    current_user_role = current_user['permissions'].get('role_name', 'viewer')
    
    # Prevent user from changing their own role
    if current_user['user']['email'] == email:
        raise HTTPException(
            status_code=400, 
            detail="You cannot change your own role"
        )
    
    # Check target user's current role
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT role FROM gpu_monitor.users WHERE email = %s", (email,))
        target_user = cursor.fetchone()
        
        if target_user:
            target_user_role = target_user['role']
            
            # Owner cannot edit other owners or admins
            if current_user_role == 'owner' and target_user_role in ['owner', 'admin']:
                raise HTTPException(
                    status_code=403, 
                    detail="Owners cannot edit admin or owner roles"
                )
            
            # Owner cannot assign owner or admin roles
            if current_user_role == 'owner' and new_role in ['owner', 'admin']:
                raise HTTPException(
                    status_code=403, 
                    detail="Owners cannot assign admin or owner roles"
                )
        
        # Verify new role exists
        cursor.execute(
            "SELECT role_name FROM gpu_monitor.roles WHERE role_name = %s",
            (new_role,)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Invalid role")
        
        # Update user role
        cursor.execute("""
            UPDATE gpu_monitor.users 
            SET role = %s, updated_at = CURRENT_TIMESTAMP
            WHERE email = %s
            RETURNING *
        """, (new_role, email))
        
        updated_user = cursor.fetchone()
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"success": True, "user": dict(updated_user)}


@router.put("/{email}/status")
async def toggle_user_status(
    email: str,
    status_data: dict,
    current_user: dict = Depends(require_permission("can_manage_users"))
):
    """Enable/disable user - admin or owner can do this"""
    is_active = status_data.get('is_active')
    
    if is_active is None:
        raise HTTPException(status_code=400, detail="is_active is required")
    
    # Prevent owner from disabling themselves
    if current_user['user']['email'] == email:
        raise HTTPException(
            status_code=400, 
            detail="You cannot disable your own account"
        )
    
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            UPDATE gpu_monitor.users 
            SET is_active = %s, updated_at = CURRENT_TIMESTAMP
            WHERE email = %s
            RETURNING *
        """, (is_active, email))
        
        updated_user = cursor.fetchone()
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"success": True, "user": dict(updated_user)}


@router.get("/roles", response_model=List[dict])
async def get_all_roles(current_user: dict = Depends(get_current_user)):
    """Get all available roles"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM gpu_monitor.roles ORDER BY id")
        roles = cursor.fetchall()
        return [dict(role) for role in roles]


@router.delete("/{email}")
async def delete_user(
    email: str,
    current_user: dict = Depends(require_permission("can_manage_users"))
):
    """Delete user - admin or owner can do this"""
    # Prevent owner from deleting themselves
    if current_user['user']['email'] == email:
        raise HTTPException(
            status_code=400, 
            detail="You cannot delete your own account"
        )
    
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "DELETE FROM gpu_monitor.users WHERE email = %s RETURNING *",
            (email,)
        )
        deleted_user = cursor.fetchone()
        
        if not deleted_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"success": True, "message": "User deleted successfully"}

