from fastapi import APIRouter, HTTPException, status
from typing import List
from ..models import GPUMetricsResponse, GPUMetricsModel

router = APIRouter(prefix="/api/gpu", tags=["gpu"])

@router.get("/metrics", response_model=List[GPUMetricsResponse])
def get_latest_gpu_metrics():
    """Get latest GPU metrics for all hosts and GPUs"""
    try:
        metrics = GPUMetricsModel.get_latest_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch GPU metrics: {str(e)}"
        )

@router.get("/metrics/{host}", response_model=List[GPUMetricsResponse])
def get_gpu_metrics_by_host(host: str):
    """Get latest GPU metrics for a specific host"""
    try:
        metrics = GPUMetricsModel.get_metrics_by_host(host)
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No GPU metrics found for host {host}"
            )
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch GPU metrics: {str(e)}"
        )

@router.get("/hosts", response_model=List[str])
def get_all_hosts():
    """Get all unique hosts with GPU metrics"""
    try:
        hosts = GPUMetricsModel.get_all_hosts()
        return hosts
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch hosts: {str(e)}"
        )

@router.get("/metrics/overall/by-gpu-name")
def get_overall_metrics():
    """Get overall aggregated metrics grouped by GPU name"""
    try:
        overall_metrics = GPUMetricsModel.get_overall_metrics_by_gpu_name()
        individual_metrics = GPUMetricsModel.get_latest_metrics()
        
        return {
            "overall": overall_metrics,
            "individual": individual_metrics
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch overall metrics: {str(e)}"
        )


