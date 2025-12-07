from fastapi import APIRouter, HTTPException, status
from typing import List
from ..models import HealthStatusResponse, StatsResponse, HealthStatusModel, StatsModel, ProjectCreate, ProjectResponse, ProjectModel

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("/url/{url_id}", response_model=HealthStatusResponse)
def get_current_health(url_id: int):
    """Get current health status for a URL"""
    try:
        health = HealthStatusModel.get_latest_by_url(url_id)
        if not health:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No health status found for URL {url_id}"
            )
        return health
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch health status: {str(e)}"
        )

@router.get("/url/{url_id}/history", response_model=List[HealthStatusResponse])
def get_health_history(url_id: int, minutes: int = 20):
    """Get health status history for last N minutes"""
    try:
        if minutes < 1 or minutes > 1440:  # Max 24 hours
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minutes must be between 1 and 1440"
            )
        history = HealthStatusModel.get_history(url_id, minutes)
        return history
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch health history: {str(e)}"
        )

@router.get("/all-latest", response_model=List[HealthStatusResponse])
def get_all_latest_health():
    """Get latest health status for all URLs"""
    try:
        health_statuses = HealthStatusModel.get_all_latest()
        return health_statuses
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch health statuses: {str(e)}"
        )

@router.get("/stats", response_model=StatsResponse)
def get_statistics():
    """Get overall statistics"""
    try:
        stats = StatsModel.get_overall_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}"
        )


# Project routes
projects_router = APIRouter(prefix="/api/projects", tags=["projects"])

@projects_router.get("", response_model=List[ProjectResponse])
def get_all_projects():
    """Get all project categories"""
    try:
        projects = ProjectModel.get_all()
        return projects
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {str(e)}"
        )

@projects_router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate):
    """Create a new project category"""
    try:
        created_project = ProjectModel.create(project.name)
        return created_project
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )

@projects_router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int):
    """Delete a project category"""
    try:
        deleted = ProjectModel.delete(project_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {project_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )