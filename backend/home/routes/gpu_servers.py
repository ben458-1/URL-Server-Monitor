from fastapi import APIRouter, HTTPException, status
from typing import List
from ..models.schemas import GPUServerCreate, GPUServerUpdate, GPUServerResponse
from ..models.database_models import GPUServerModel

router = APIRouter(prefix="/api/gpu-servers", tags=["GPU Servers"])


@router.post("", response_model=GPUServerResponse, status_code=status.HTTP_201_CREATED)
async def create_gpu_server(server: GPUServerCreate):
    """Create a new GPU server"""
    try:
        server_dict = server.model_dump()
        result = GPUServerModel.create(server_dict)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating GPU server: {str(e)}"
        )


@router.get("", response_model=List[GPUServerResponse])
async def get_all_gpu_servers():
    """Get all GPU servers"""
    try:
        servers = GPUServerModel.get_all()
        return servers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving GPU servers: {str(e)}"
        )


@router.get("/{server_id}", response_model=GPUServerResponse)
async def get_gpu_server(server_id: int):
    """Get a specific GPU server by ID"""
    try:
        server = GPUServerModel.get_by_id(server_id, decrypt_keys=False)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GPU server with ID {server_id} not found"
            )
        return server
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving GPU server: {str(e)}"
        )


@router.put("/{server_id}", response_model=GPUServerResponse)
async def update_gpu_server(server_id: int, server: GPUServerUpdate):
    """Update a GPU server"""
    try:
        # Check if server exists
        existing_server = GPUServerModel.get_by_id(server_id)
        if not existing_server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GPU server with ID {server_id} not found"
            )
        
        # Update only provided fields
        server_dict = server.model_dump(exclude_unset=True)
        result = GPUServerModel.update(server_id, server_dict)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating GPU server"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating GPU server: {str(e)}"
        )


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gpu_server(server_id: int):
    """Delete a GPU server"""
    try:
        success = GPUServerModel.delete(server_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GPU server with ID {server_id} not found"
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting GPU server: {str(e)}"
        )


@router.get("/by-gpu-name/{gpu_name}")
async def get_servers_by_gpu_name(gpu_name: str):
    """Get all servers with a specific GPU name"""
    try:
        servers = GPUServerModel.get_by_gpu_name(gpu_name)
        return servers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving servers: {str(e)}"
        )


@router.patch("/{server_id}/usage-limit")
async def update_usage_limit(server_id: int, usage_limit: int):
    """Update GPU usage limit for a server"""
    try:
        if usage_limit < 0 or usage_limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usage limit must be between 0 and 100"
            )
        
        result = GPUServerModel.update_usage_limit(server_id, usage_limit)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GPU server with ID {server_id} not found"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating usage limit: {str(e)}"
        )


@router.patch("/{server_id}/alert-emails")
async def update_alert_emails(server_id: int, alert_emails: List[str]):
    """Update alert emails for a server"""
    try:
        result = GPUServerModel.update_alert_emails(server_id, alert_emails)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GPU server with ID {server_id} not found"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating alert emails: {str(e)}"
        )