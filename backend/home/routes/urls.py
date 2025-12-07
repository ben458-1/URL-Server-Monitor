from fastapi import APIRouter, HTTPException, status
from typing import List
from ..models import URLCreate, URLUpdate, URLResponse, URLModel, HealthCheckToggle

router = APIRouter(prefix="/api/urls", tags=["urls"])

@router.post("", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
def create_url(url: URLCreate):
    """Create a new URL"""
    try:
        url_data = url.model_dump()
        created_url = URLModel.create(url_data)
        return created_url
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create URL: {str(e)}"
        )

@router.get("", response_model=List[URLResponse])
def get_all_urls():
    """Get all URLs"""
    try:
        urls = URLModel.get_all()
        return urls
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch URLs: {str(e)}"
        )

@router.get("/{url_id}", response_model=URLResponse)
def get_url(url_id: int):
    """Get URL by ID"""
    try:
        url = URLModel.get_by_id(url_id)
        if not url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"URL with id {url_id} not found"
            )
        return url
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch URL: {str(e)}"
        )

@router.get("/environment/{environment}", response_model=List[URLResponse])
def get_urls_by_environment(environment: str):
    """Get URLs by environment"""
    try:
        if environment not in ['production', 'development', 'staging']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Environment must be production, development, or staging"
            )
        urls = URLModel.get_by_environment(environment)
        return urls
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch URLs: {str(e)}"
        )

@router.put("/{url_id}", response_model=URLResponse)
def update_url(url_id: int, url: URLUpdate):
    """Update URL"""
    try:
        # Check if URL exists
        existing_url = URLModel.get_by_id(url_id)
        if not existing_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"URL with id {url_id} not found"
            )
        
        url_data = url.model_dump()
        updated_url = URLModel.update(url_id, url_data)
        return updated_url
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update URL: {str(e)}"
        )

@router.delete("/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_url(url_id: int):
    """Delete URL"""
    try:
        deleted = URLModel.delete(url_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"URL with id {url_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete URL: {str(e)}"
        )

@router.patch("/{url_id}/health-check", response_model=URLResponse)
def toggle_health_check(url_id: int, toggle: HealthCheckToggle):
    """Toggle health check status (YES/NO) for a URL"""
    try:
        existing_url = URLModel.get_by_id(url_id)
        if not existing_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"URL with id {url_id} not found"
            )
        
        updated_url = URLModel.toggle_health_check(url_id, toggle.status)
        return updated_url
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle health check: {str(e)}"
        )

@router.patch("/{url_id}/alert-emails", response_model=URLResponse)
def update_alert_emails(url_id: int, alert_emails: List[str]):
    """Update alert emails for a URL"""
    try:
        existing_url = URLModel.get_by_id(url_id)
        if not existing_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"URL with id {url_id} not found"
            )
        
        updated_url = URLModel.update_alert_emails(url_id, alert_emails)
        return updated_url
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert emails: {str(e)}"
        )