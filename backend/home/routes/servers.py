from fastapi import APIRouter, HTTPException, status
from typing import List
from ..models import ServerCreate, ServerUpdate, ServerResponse, ServerModel

router = APIRouter(prefix="/api/servers", tags=["servers"])

@router.post("", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
def create_server(server: ServerCreate):
    """Create a new server"""
    try:
        server_data = server.model_dump()
        created_server = ServerModel.create(server_data)
        return created_server
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create server: {str(e)}"
        )

@router.get("", response_model=List[ServerResponse])
def get_all_servers():
    """Get all servers"""
    try:
        servers = ServerModel.get_all()
        return servers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch servers: {str(e)}"
        )

@router.get("/{server_id}", response_model=ServerResponse)
def get_server(server_id: int):
    """Get server by ID"""
    try:
        server = ServerModel.get_by_id(server_id)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server with id {server_id} not found"
            )
        return server
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch server: {str(e)}"
        )

@router.put("/{server_id}", response_model=ServerResponse)
def update_server(server_id: int, server: ServerUpdate):
    """Update server"""
    try:
        # Check if server exists
        existing_server = ServerModel.get_by_id(server_id)
        if not existing_server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server with id {server_id} not found"
            )
        
        server_data = server.model_dump()
        updated_server = ServerModel.update(server_id, server_data)
        return updated_server
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update server: {str(e)}"
        )

@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(server_id: int):
    """Delete server"""
    try:
        deleted = ServerModel.delete(server_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server with id {server_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete server: {str(e)}"
        )