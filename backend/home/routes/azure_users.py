from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
import httpx
import os
from msal import ConfidentialClientApplication
import logging
import asyncio
import time
from datetime import datetime, timedelta
import base64

router = APIRouter(prefix="/api/azure", tags=["Azure AD"])
logger = logging.getLogger(__name__)

# Microsoft Graph API configuration
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
TENANT_ID = os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')

# Create MSAL app for getting Graph API token
msal_app = None
if CLIENT_SECRET:
    msal_app = ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET
    )

# 1️⃣ Token cache (60 minutes)
_token_cache = {
    "token": None,
    "expires_at": None
}

# 4️⃣ Photo cache (5-10 minutes)
_photo_cache = {}
PHOTO_CACHE_TTL = 600  # 10 minutes


def get_graph_token():
    """Get a cached token for Microsoft Graph API using client credentials"""
    if not msal_app:
        logger.error("MSAL app not initialized - CLIENT_SECRET missing")
        return None
    
    # Check if we have a valid cached token
    now = datetime.now()
    if _token_cache["token"] and _token_cache["expires_at"] and now < _token_cache["expires_at"]:
        logger.debug("Using cached Graph API token")
        return _token_cache["token"]
    
    try:
        result = msal_app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        if "access_token" in result:
            logger.info("Successfully acquired new Graph API token")
            # Cache token with 60 minute expiry (or use expires_in from response minus buffer)
            expires_in = result.get("expires_in", 3600)  # Default 60 min
            _token_cache["token"] = result["access_token"]
            _token_cache["expires_at"] = now + timedelta(seconds=expires_in - 300)  # 5 min buffer
            return result["access_token"]
        else:
            logger.error(f"Failed to acquire token: {result.get('error_description')}")
            return None
    except Exception as e:
        logger.error(f"Error acquiring Graph token: {e}")
        return None


def get_cached_photo(user_id: str):
    """Get photo from cache if available and not expired"""
    if user_id in _photo_cache:
        photo_data, timestamp = _photo_cache[user_id]
        if time.time() - timestamp < PHOTO_CACHE_TTL:
            return photo_data
        else:
            # Expired, remove from cache
            del _photo_cache[user_id]
    return None


def cache_photo(user_id: str, photo_data_url: Optional[str]):
    """Cache photo data URL with timestamp"""
    _photo_cache[user_id] = (photo_data_url, time.time())


async def fetch_user_photo(client: httpx.AsyncClient, user_id: str, headers: dict) -> Optional[str]:
    """Fetch a single user photo asynchronously with caching"""
    # Check cache first
    cached_photo = get_cached_photo(user_id)
    if cached_photo is not None:
        logger.debug(f"Using cached photo for user {user_id}")
        return cached_photo
    
    try:
        photo_url = f"{GRAPH_API_URL}/users/{user_id}/photo/$value"
        response = await client.get(photo_url, headers=headers, timeout=5.0)
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            photo_base64 = base64.b64encode(response.content).decode('utf-8')
            photo_data_url = f"data:{content_type};base64,{photo_base64}"
            logger.debug(f"✓ Fetched photo for user {user_id} ({len(response.content)} bytes)")
            
            # Cache the photo
            cache_photo(user_id, photo_data_url)
            return photo_data_url
        else:
            logger.debug(f"No photo (HTTP {response.status_code}) for user {user_id}")
            # Cache the None result to avoid repeated failed requests
            cache_photo(user_id, None)
            return None
    except Exception as photo_error:
        logger.warning(f"Photo fetch failed for user {user_id}: {photo_error}")
        return None


@router.get("/users/all")
async def get_all_azure_users(
    authorization: Optional[str] = Header(None)
):
    """
    Get all Azure AD users efficiently using pagination
    Returns users with their display names, emails (no photos for performance)
    """
    try:
        # Get cached Graph API token
        graph_token = get_graph_token()
        
        if not graph_token:
            raise HTTPException(
                status_code=500,
                detail="Unable to acquire Graph API token. Please check server configuration."
            )
        
        headers = {
            "Authorization": f"Bearer {graph_token}",
            "Content-Type": "application/json"
        }
        
        # Use the /users endpoint to get ALL users with pagination
        search_url = f"{GRAPH_API_URL}/users"
        
        params = {
            "$select": "id,displayName,mail,userPrincipalName,jobTitle",
            "$top": 999,  # Max users per page
            "$orderby": "displayName"
        }
        
        logger.info(f"Fetching all Azure AD users...")
        
        all_users = []
        
        # Use httpx AsyncClient for async requests
        async with httpx.AsyncClient() as client:
            next_link = search_url
            page = 1
            
            while next_link:
                if next_link == search_url:
                    response = await client.get(next_link, headers=headers, params=params, timeout=30.0)
                else:
                    # Follow @odata.nextLink for pagination (already has params)
                    response = await client.get(next_link, headers=headers, timeout=30.0)
                
                if response.status_code == 401:
                    logger.error("Graph API returned 401 - token may be invalid")
                    raise HTTPException(
                        status_code=401,
                        detail="Graph API authentication failed"
                    )
                
                if response.status_code != 200:
                    logger.error(f"Graph API error: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Microsoft Graph API error: {response.text}"
                    )
                
                data = response.json()
                users = data.get('value', [])
                
                logger.info(f"Page {page}: Fetched {len(users)} users")
                
                # Filter users with valid emails
                for user in users:
                    email = user.get('mail') or user.get('userPrincipalName')
                    if email:
                        user_data = {
                            "id": user.get('id'),
                            "displayName": user.get('displayName'),
                            "email": email,
                            "jobTitle": user.get('jobTitle', ''),
                            "photoUrl": None  # Don't fetch photos for all users (performance)
                        }
                        all_users.append(user_data)
                
                # Check for next page
                next_link = data.get('@odata.nextLink')
                page += 1
        
        logger.info(f"Total users fetched: {len(all_users)}")
        return {"users": all_users}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching all users: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching all users: {str(e)}"
        )


@router.get("/users/search")
async def search_azure_users(
    query: str,
    authorization: Optional[str] = Header(None)
):
    """
    Search Azure AD users for email autocomplete (optimized with caching and concurrent photo fetching)
    Returns users with their display names, emails, and profile photos
    """
    try:
        # 1️⃣ Get cached Graph API token
        graph_token = get_graph_token()
        
        if not graph_token:
            raise HTTPException(
                status_code=500,
                detail="Unable to acquire Graph API token. Please check server configuration."
            )
        
        headers = {
            "Authorization": f"Bearer {graph_token}",
            "Content-Type": "application/json"
        }
        
        search_url = f"{GRAPH_API_URL}/users"
        
        # Escape single quotes for OData filter
        search_query = query.replace("'", "''")
        
        # 2️⃣ Use $filter with startswith for faster autocomplete (instead of $search)
        # This is much faster than $search for prefix matching
        filter_parts = [
            f"startswith(displayName, '{search_query}')",
            f"startswith(mail, '{search_query}')",
            f"startswith(userPrincipalName, '{search_query}')"
        ]
        
        params = {
            "$filter": " or ".join(filter_parts),
            "$select": "id,displayName,mail,userPrincipalName,jobTitle",
            "$top": 10
        }
        
        logger.info(f"Searching users with query: {query}")
        
        # Use httpx AsyncClient for async requests
        async with httpx.AsyncClient() as client:
            response = await client.get(search_url, headers=headers, params=params, timeout=10.0)
            
            if response.status_code == 401:
                logger.error("Graph API returned 401 - token may be invalid")
                raise HTTPException(
                    status_code=401,
                    detail="Graph API authentication failed"
                )
            
            if response.status_code != 200:
                logger.error(f"Graph API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Microsoft Graph API error: {response.text}"
                )
            
            data = response.json()
            users = data.get('value', [])
            
            logger.info(f"Found {len(users)} users matching '{query}'")
            
            # Filter users with valid emails
            valid_users = []
            for user in users:
                email = user.get('mail') or user.get('userPrincipalName')
                if email:
                    valid_users.append(user)
            
            # 3️⃣ Fetch all photos concurrently using asyncio.gather
            photo_tasks = [
                fetch_user_photo(client, user.get('id'), headers)
                for user in valid_users
            ]
            
            # Fetch all photos in parallel
            if photo_tasks:
                photos = await asyncio.gather(*photo_tasks, return_exceptions=True)
            else:
                photos = []
            
            # Format response with photo URLs
            result = []
            for user, photo_data_url in zip(valid_users, photos):
                # Handle exceptions from gather
                if isinstance(photo_data_url, Exception):
                    logger.warning(f"Photo fetch exception for {user.get('displayName')}: {photo_data_url}")
                    photo_data_url = None
                
                user_data = {
                    "id": user.get('id'),
                    "displayName": user.get('displayName'),
                    "email": user.get('mail') or user.get('userPrincipalName'),
                    "jobTitle": user.get('jobTitle', ''),
                    "photoUrl": photo_data_url  # Will be None if no photo or cached
                }
                result.append(user_data)
                logger.debug(f"User: {user_data['displayName']} ({user_data['email']})")
        
        return {"users": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching users: {str(e)}"
        )


@router.get("/users/by-email/{email}")
async def get_user_by_email(
    email: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get user details by email address including profile photo (optimized with caching)
    """
    try:
        # Get cached Graph API token
        graph_token = get_graph_token()
        
        if not graph_token:
            raise HTTPException(
                status_code=500,
                detail="Unable to acquire Graph API token"
            )
        
        headers = {
            "Authorization": f"Bearer {graph_token}",
            "Content-Type": "application/json"
        }
        
        # Find user by email
        search_url = f"{GRAPH_API_URL}/users"
        params = {
            "$filter": f"mail eq '{email}' or userPrincipalName eq '{email}'",
            "$select": "id,displayName,mail,userPrincipalName,jobTitle"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(search_url, headers=headers, params=params, timeout=10.0)
            
            if response.status_code != 200:
                logger.error(f"Graph API error: {response.status_code}")
                return {"user": None}
            
            data = response.json()
            users = data.get('value', [])
            
            if not users:
                return {"user": None}
            
            user = users[0]
            user_id = user.get('id')
            
            # Fetch photo with caching
            photo_data_url = await fetch_user_photo(client, user_id, headers)
            
            return {
                "user": {
                    "id": user_id,
                    "displayName": user.get('displayName'),
                    "email": user.get('mail') or user.get('userPrincipalName'),
                    "photoUrl": photo_data_url
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return {"user": None}


@router.get("/users/{user_id}/photo")
async def get_user_photo(
    user_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get user profile photo from Azure AD (optimized with caching)
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Authorization token required"
            )
        
        access_token = authorization.replace("Bearer ", "")
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            # Use cached photo if available
            photo_data_url = await fetch_user_photo(client, user_id, headers)
            
            if photo_data_url is None:
                # Return a default avatar if no photo found
                return {"photoUrl": None}
            
            return {
                "photo": photo_data_url
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving photo: {str(e)}"
        )

