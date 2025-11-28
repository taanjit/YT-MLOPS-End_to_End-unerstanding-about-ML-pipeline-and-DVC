#!/usr/bin/env python3
"""
FastAPI application for managing DVC experiments.
Provides endpoints to list experiments, get parameters, and apply experiments.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict
import subprocess
import json
import re
import sys

app = FastAPI(
    title="DVC Experiments API",
    description="API for managing DVC experiments: list, get parameters, and apply experiments",
    version="1.0.0"
)


class ExperimentInfo(BaseModel):
    """Model for experiment information."""
    commit_hash: str
    experiment_name: str


class ExperimentParams(BaseModel):
    """Model for experiment parameters."""
    model_config = ConfigDict(protected_namespaces=())
    
    data_ingestion: Dict[str, float]
    feature_engineering: Dict[str, int]
    model_building: Dict[str, int]


class ApplyExperimentResponse(BaseModel):
    """Model for apply experiment response."""
    success: bool
    message: str
    experiment_name: str


def get_experiments_list() -> List[tuple]:
    """
    Get list of DVC experiments using 'dvc exp list' command.
    
    Returns:
        list: List of tuples (commit_hash, experiment_name)
    """
    try:
        result = subprocess.run(
            ['dvc', 'exp', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        
        experiments = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('main:'):
                continue
            
            # Parse lines like: "ded11c0 [addle-hill]"
            match = re.match(r'(\w+)\s+\[(.+)\]', line)
            if match:
                commit_hash = match.group(1)
                exp_name = match.group(2)
                experiments.append((commit_hash, exp_name))
        
        return experiments
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running 'dvc exp list': {e.stderr or str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing experiments: {str(e)}"
        )


def get_experiment_params(commit_hash: str) -> Optional[Dict]:
    """
    Get params data for a specific experiment using 'dvc exp show --json'.
    
    Args:
        commit_hash: The commit hash of the experiment
        
    Returns:
        dict: Parameters from dvclive/params.yaml or params.yaml as fallback
    """
    try:
        result = subprocess.run(
            ['dvc', 'exp', 'show', '--json'],
            capture_output=True,
            text=True,
            check=True
        )
        
        data = json.loads(result.stdout)
        
        # Search for the experiment in the JSON data
        for item in data:
            # Check if this is the main branch with experiments
            if 'experiments' in item and item['experiments']:
                for exp in item['experiments']:
                    if 'revs' in exp and exp['revs']:
                        for rev in exp['revs']:
                            # Check if the commit hash matches (full or short)
                            rev_hash = rev.get('rev', '')
                            if commit_hash in rev_hash or rev_hash.startswith(commit_hash):
                                params_data = rev.get('data', {}).get('params', {})
                                
                                # Try to get dvclive/params.yaml first
                                if 'dvclive/params.yaml' in params_data:
                                    dvclive_params = params_data['dvclive/params.yaml']
                                    if 'data' in dvclive_params and 'error' not in dvclive_params:
                                        return dvclive_params['data']
                                
                                # Fall back to params.yaml if dvclive/params.yaml not available
                                if 'params.yaml' in params_data:
                                    params_yaml = params_data['params.yaml']
                                    if 'data' in params_yaml:
                                        return params_yaml['data']
        
        return None
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running 'dvc exp show': {e.stderr or str(e)}"
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting params: {str(e)}"
        )


def apply_experiment(experiment_name: str) -> Dict[str, str]:
    """
    Apply a DVC experiment using 'dvc exp apply' command.
    
    Args:
        experiment_name: Name or commit hash of the experiment to apply
        
    Returns:
        dict: Response with success status and message
    """
    try:
        result = subprocess.run(
            ['dvc', 'exp', 'apply', experiment_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "success": True,
            "message": result.stdout.strip() or f"Experiment '{experiment_name}' applied successfully",
            "experiment_name": experiment_name
        }
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        raise HTTPException(
            status_code=400,
            detail=f"Error applying experiment '{experiment_name}': {error_msg}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error applying experiment: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "DVC Experiments API",
        "version": "1.0.0",
        "endpoints": {
            "GET /experiments": "Get list of all experiments",
            "GET /experiments/{experiment_id}/params": "Get parameters for a specific experiment",
            "POST /experiments/{experiment_id}/apply": "Apply a specific experiment"
        }
    }


@app.get("/experiments", response_model=List[ExperimentInfo])
async def list_experiments():
    """
    Get list of all DVC experiments.
    
    Returns:
        List of experiment information (commit hash and name)
    """
    experiments = get_experiments_list()
    
    return [
        ExperimentInfo(
            commit_hash=commit_hash,
            experiment_name=exp_name
        )
        for commit_hash, exp_name in experiments
    ]


@app.get("/experiments/{experiment_id}/params", response_model=ExperimentParams)
async def get_experiment_parameters(experiment_id: str):
    """
    Get parameters for a specific experiment.
    
    Args:
        experiment_id: Commit hash or experiment name
        
    Returns:
        Experiment parameters (data_ingestion, feature_engineering, model_building)
    """
    # Try to find experiment by name first, then by commit hash
    experiments = get_experiments_list()
    
    commit_hash = None
    for ch, exp_name in experiments:
        if experiment_id == exp_name or experiment_id == ch or ch.startswith(experiment_id):
            commit_hash = ch
            break
    
    if not commit_hash:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment '{experiment_id}' not found"
        )
    
    params = get_experiment_params(commit_hash)
    
    if not params:
        raise HTTPException(
            status_code=404,
            detail=f"Parameters not found for experiment '{experiment_id}'"
        )
    
    # Format the response
    return ExperimentParams(
        data_ingestion=params.get('data_ingestion', {}),
        feature_engineering=params.get('feature_engineering', {}),
        model_building=params.get('model_building', {})
    )


@app.post("/experiments/{experiment_id}/apply", response_model=ApplyExperimentResponse)
async def apply_experiment_endpoint(experiment_id: str):
    """
    Apply a DVC experiment to the current workspace.
    
    Args:
        experiment_id: Commit hash or experiment name to apply
        
    Returns:
        Response indicating success or failure
    """
    # Verify experiment exists
    experiments = get_experiments_list()
    experiment_found = False
    
    for commit_hash, exp_name in experiments:
        if experiment_id == exp_name or experiment_id == commit_hash or commit_hash.startswith(experiment_id):
            experiment_found = True
            # Use the experiment name for applying (DVC prefers names)
            experiment_name = exp_name
            break
    
    if not experiment_found:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment '{experiment_id}' not found"
        )
    
    result = apply_experiment(experiment_name)
    return ApplyExperimentResponse(**result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

