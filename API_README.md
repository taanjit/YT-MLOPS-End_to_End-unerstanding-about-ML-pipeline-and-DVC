# DVC Experiments API

FastAPI application for managing DVC experiments with three main endpoints.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the API

Start the API server:

```bash
python api.py
```

Or using uvicorn directly:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- **Interactive API docs (Swagger UI)**: `http://localhost:8000/docs`
- **Alternative API docs (ReDoc)**: `http://localhost:8000/redoc`

## Endpoints

### 1. Get Experiment List

**GET** `/experiments`

Returns a list of all available DVC experiments.

**Response:**
```json
[
  {
    "commit_hash": "ded11c0",
    "experiment_name": "addle-hill"
  },
  {
    "commit_hash": "aa5f950",
    "experiment_name": "areal-dams"
  }
]
```

**Example:**
```bash
curl http://localhost:8000/experiments
```

### 2. Get Experiment Parameters

**GET** `/experiments/{experiment_id}/params`

Get the parameters for a specific experiment. You can use either the experiment name or commit hash.

**Parameters:**
- `experiment_id`: Experiment name (e.g., "areal-dams") or commit hash (e.g., "aa5f950")

**Response:**
```json
{
  "data_ingestion": {
    "test_size": 0.2
  },
  "feature_engineering": {
    "max_features": 15
  },
  "model_building": {
    "n_estimators": 10,
    "random_state": 2
  }
}
```

**Examples:**
```bash
# Using experiment name
curl http://localhost:8000/experiments/areal-dams/params

# Using commit hash
curl http://localhost:8000/experiments/aa5f950/params
```

### 3. Apply Experiment

**POST** `/experiments/{experiment_id}/apply`

Apply a DVC experiment to the current workspace.

**Parameters:**
- `experiment_id`: Experiment name (e.g., "areal-dams") or commit hash (e.g., "aa5f950")

**Response:**
```json
{
  "success": true,
  "message": "Changes for experiment 'areal-dams' have been applied to your current workspace.",
  "experiment_name": "areal-dams"
}
```

**Examples:**
```bash
# Using experiment name
curl -X POST http://localhost:8000/experiments/areal-dams/apply

# Using commit hash
curl -X POST http://localhost:8000/experiments/aa5f950/apply
```

## Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Get all experiments
response = requests.get(f"{BASE_URL}/experiments")
experiments = response.json()
print("Experiments:", experiments)

# 2. Get parameters for a specific experiment
experiment_name = "areal-dams"
response = requests.get(f"{BASE_URL}/experiments/{experiment_name}/params")
params = response.json()
print(f"Parameters for {experiment_name}:", params)

# 3. Apply an experiment
response = requests.post(f"{BASE_URL}/experiments/{experiment_name}/apply")
result = response.json()
print("Apply result:", result)
```

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (e.g., invalid experiment name)
- `404`: Not Found (experiment doesn't exist)
- `500`: Internal Server Error (DVC command failed)

## Notes

- The API uses the existing DVC commands under the hood
- Experiment parameters are retrieved from `dvclive/params.yaml` if available, otherwise falls back to `params.yaml`
- Applying an experiment modifies your current workspace, so use with caution

