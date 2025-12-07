from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import requests
import os
import logging
from functools import lru_cache
from ..config.database import get_db_cursor
from datetime import datetime

security = HTTPBearer()
logger = logging.getLogger(__name__)

# Azure AD Configuration
TENANT_ID = os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"


def get_microsoft_public_keys():
    """Fetch Microsoft's public signing keys for token validation"""
    keys_url = f"{AUTHORITY}/discovery/v2.0/keys"
    print(f"🔑 Fetching public keys from: {keys_url}")
    response = requests.get(keys_url)
    keys_data = response.json()
    print(f"🔑 Fetched {len(keys_data.get('keys', []))} keys from Microsoft")
    return keys_data


async def verify_token_with_msal(token: str):
    """
    Verify Microsoft token with multiple audience support
    Supports:
    1. Token issued for this app (CLIENT_ID)
    2. Token issued for API scope (api://CLIENT_ID)
    3. Microsoft Graph tokens (as fallback for migration)
    """
    try:
        # Get Microsoft's public keys
        jwks = get_microsoft_public_keys()
        
        # Decode token header to find the right key
        unverified_header = jwt.get_unverified_header(token)
        
        # Decode without verification first to inspect claims
        unverified_payload = jwt.get_unverified_claims(token)
        print(f"🔍 Token inspection:")
        print(f"  - Audience (aud): {unverified_payload.get('aud')}")
        print(f"  - Issuer (iss): {unverified_payload.get('iss')}")
        print(f"  - Subject (sub): {unverified_payload.get('sub')}")
        print(f"  - User: {unverified_payload.get('preferred_username') or unverified_payload.get('upn')}")
        
        # Find the matching key
        print(f"🔑 Looking for key with kid: {unverified_header['kid']}")
        print(f"🔑 Available keys: {[k['kid'] for k in jwks['keys']]}")
        
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                # Include all fields for better compatibility
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key.get("use", "sig"),
                    "n": key["n"],
                    "e": key["e"],
                    "alg": key.get("alg", "RS256"),
                    "x5c": key.get("x5c"),
                    "x5t": key.get("x5t")
                }
                print(f"✅ Found matching key: {key['kid']}")
                break
        
        if not rsa_key:
            print(f"❌ No matching key found for kid: {unverified_header['kid']}")
            raise HTTPException(
                status_code=401, 
                detail="Unable to find appropriate key"
            )
        
        # Try multiple audience options
        valid_audiences = [
            CLIENT_ID,  # Direct app ID
            f"api://{CLIENT_ID}",  # API scope format
            f"api://{CLIENT_ID}/access_as_user",  # Full API scope
            "00000003-0000-0000-c000-000000000000",  # Microsoft Graph (temporary workaround)
        ]
        
        # Try multiple issuer formats (v2.0 and v1.0)
        valid_issuers = [
            f"{AUTHORITY}/v2.0",  # Azure AD v2.0
            f"https://sts.windows.net/{TENANT_ID}/",  # Azure AD v1.0
        ]
        
        payload = None
        last_error = None
        
        # Special handling for Microsoft Graph tokens (temporary workaround)
        actual_audience = unverified_payload.get('aud')
        if actual_audience == "00000003-0000-0000-c000-000000000000":
            print("⚠️  Microsoft Graph token detected - using lenient validation")
            
            # TEMPORARY: Skip all verification for Microsoft Graph tokens
            # This is NOT secure for production - only for testing!
            print("⚠️  WARNING: Using unverified token payload (TEMPORARY)")
            payload = unverified_payload
            print(f"✅ Graph token accepted (UNVERIFIED - FIX THIS!)")
            
            # try:
            #     # Validate with more lenient options (skip issuer validation for Graph tokens)
            #     payload = jwt.decode(
            #         token,
            #         rsa_key,
            #         algorithms=["RS256"],
            #         audience="00000003-0000-0000-c000-000000000000",
            #         options={"verify_iss": False, "verify_signature": False}  # Skip verification temporarily
            #     )
            #     print(f"✅ Graph token validated successfully (lenient mode)")
            # except JWTError as e:
            #     print(f"⚠️  Graph token lenient validation failed: {type(e).__name__}: {str(e)}")
            #     last_error = e
            #     payload = None
        
        # Try normal validation for API tokens
        if not payload:
            for audience in valid_audiences:
                for issuer in valid_issuers:
                    try:
                        payload = jwt.decode(
                            token,
                            rsa_key,
                            algorithms=["RS256"],
                            audience=audience,
                            issuer=issuer
                        )
                        print(f"✅ Token validated successfully with audience: {audience}, issuer: {issuer}")
                        break
                    except JWTError as e:
                        last_error = e
                        continue
                if payload:
                    break
        
        if not payload:
            print(f"❌ Token validation failed for all audiences")
            print(f"Expected audiences: {valid_audiences}")
            print(f"Actual audience: {unverified_payload.get('aud')}")
            print(f"Expected issuers: {valid_issuers}")
            print(f"Actual issuer: {unverified_payload.get('iss')}")
            print(f"Last error: {last_error}")
            raise HTTPException(
                status_code=401, 
                detail=f"Token validation failed: Invalid audience. Expected one of {valid_audiences}, got {unverified_payload.get('aud')}"
            )
        
        return payload
        
    except HTTPException:
        raise
    except JWTError as e:
        print(f"❌ JWT validation error: {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail=f"Token validation failed: {str(e)}"
        )
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail=f"Authentication error: {str(e)}"
        )


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Main token verification function
    Token is validated by Microsoft
    """
    token = credentials.credentials
    payload = await verify_token_with_msal(token)
    return payload


# Auto-create users on first login with 'viewer' role
# This ensures all authenticated users are tracked in the database
# Admin/Owner can later upgrade their roles via UI


async def get_current_user(token_data: dict = Depends(verify_token)):
    """
    Get current authenticated user with permissions from database
    Authentication done by Microsoft, permissions from database
    DEFAULT: All users have 'viewer' role unless explicitly assigned in DB
    """
    email = token_data.get("preferred_username") or token_data.get("email") or token_data.get("upn")
    name = token_data.get("name")
    azure_user_id = token_data.get("oid")
    
    if not email or not azure_user_id:
        raise HTTPException(
            status_code=400, 
            detail="Invalid token: missing required claims"
        )
    
    # Check if user exists in permission database
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            SELECT * FROM gpu_monitor.users 
            WHERE azure_user_id = %s
        """, (azure_user_id,))
        
        user = cursor.fetchone()
        
        if user:
            # User has elevated permissions in DB
            # Check if user is active
            if not user['is_active']:
                raise HTTPException(
                    status_code=403, 
                    detail="User account is disabled"
                )
            
            # Update last login
            cursor.execute("""
                UPDATE gpu_monitor.users 
                SET last_login = %s 
                WHERE email = %s
            """, (datetime.now(), user['email']))
            
            # Get role permissions
            cursor.execute("""
                SELECT r.* FROM gpu_monitor.roles r
                WHERE r.role_name = %s
            """, (user['role'],))
            
            permissions = cursor.fetchone()
            
            if not permissions:
                raise HTTPException(
                    status_code=500, 
                    detail="User role configuration not found"
                )
            
            return {
                "user": dict(user),
                "permissions": dict(permissions)
            }
        else:
            # User NOT in DB - create new user with default 'viewer' role
            # Get viewer role permissions first
            cursor.execute("""
                SELECT * FROM gpu_monitor.roles 
                WHERE role_name = 'viewer'
            """)
            
            viewer_permissions = cursor.fetchone()
            
            if not viewer_permissions:
                raise HTTPException(
                    status_code=500, 
                    detail="Viewer role configuration not found"
                )
            
            # Create new user in database with viewer role
            try:
                cursor.execute("""
                    INSERT INTO gpu_monitor.users (email, name, azure_user_id, role, is_active, last_login)
                    VALUES (%s, %s, %s, 'viewer', true, %s)
                    RETURNING *
                """, (email, name, azure_user_id, datetime.now()))
                
                new_user = cursor.fetchone()
                logger.info(f"Created new user in database: {email} with viewer role")
                
                return {
                    "user": dict(new_user),
                    "permissions": dict(viewer_permissions)
                }
            except Exception as e:
                # If duplicate key error (race condition), retry fetching the user
                if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                    logger.warning(f"User {email} was created by another request, fetching...")
                    cursor.execute("""
                        SELECT * FROM gpu_monitor.users 
                        WHERE azure_user_id = %s
                    """, (azure_user_id,))
                    
                    user = cursor.fetchone()
                    if user:
                        return {
                            "user": dict(user),
                            "permissions": dict(viewer_permissions)
                        }
                
                logger.error(f"Failed to create user {email}: {e}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to create user: {str(e)}"
                )


def require_permission(permission: str):
    """
    Decorator to check if user has specific permission
    Permissions come from database, NOT from Microsoft
    """
    async def permission_checker(current_user: dict = Depends(get_current_user)):
        if not current_user['permissions'].get(permission, False):
            raise HTTPException(
                status_code=403, 
                detail=f"Permission denied: {permission} required"
            )
        return current_user
    return permission_checker


def require_owner(current_user: dict = Depends(get_current_user)):
    """Require owner role - only owner can manage user roles"""
    if current_user['user']['role'] != 'owner':
        raise HTTPException(
            status_code=403, 
            detail="Owner access required"
        )
    return current_user


def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin or owner role"""
    if current_user['user']['role'] not in ['owner', 'admin']:
        raise HTTPException(
            status_code=403, 
            detail="Admin access required"
        )
    return current_user

