#!/usr/bin/env python3
"""
Python script to list DVC experiments and extract dvclive/params.yaml data for each experiment.
"""

import subprocess
import sys
import json
import re


def get_experiments_list():
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
        print(f"Error running 'dvc exp list': {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error parsing experiments: {e}", file=sys.stderr)
        return []


def get_experiment_params(commit_hash):
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
        print(f"Error running 'dvc exp show': {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error getting params: {e}", file=sys.stderr)
        return None


def format_params_output(params):
    """
    Format parameters in the requested format.
    
    Args:
        params: Dictionary containing the parameters
        
    Returns:
        str: Formatted string with parameters
    """
    if not params:
        return "  No parameters available"
    
    output = []
    output.append("data_ingestion:")
    test_size = params.get('data_ingestion', {}).get('test_size', 'N/A')
    output.append(f"  test_size: {test_size}")
    
    output.append("feature_engineering:")
    max_features = params.get('feature_engineering', {}).get('max_features', 'N/A')
    output.append(f"  max_features: {max_features}")
    
    output.append("model_building:")
    n_estimators = params.get('model_building', {}).get('n_estimators', 'N/A')
    random_state = params.get('model_building', {}).get('random_state', 'N/A')
    output.append(f"  n_estimators: {n_estimators}")
    output.append(f"  random_state: {random_state}")
    
    return '\n'.join(output)


def list_dvc_experiments_with_params():
    """
    List DVC experiments and display dvclive/params.yaml data for each.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Get list of experiments
        experiments = get_experiments_list()
        
        if not experiments:
            print("No experiments found.", file=sys.stderr)
            return 1
        
        # Display parameters for each experiment
        for commit_hash, exp_name in experiments:
            print(f"\n{'='*60}")
            print(f"Experiment: {exp_name} ({commit_hash})")
            print(f"{'='*60}")
            
            params = get_experiment_params(commit_hash)
            if params:
                print(format_params_output(params))
            else:
                print("  Could not retrieve parameters for this experiment")
        
        return 0
        
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = list_dvc_experiments_with_params()
    sys.exit(exit_code)

