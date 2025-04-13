Here is the file structure for this python library, but we have a bit of a problem, airflow wants all the files /dags to be included as the project. 
```
.:
dags
db
__init__.py
models
pipelines
scrapers
server

./dags:
all_cases_dag.py
latest_cases_dag.py

./db:
queries
s3_utils.py
s3_wrapper.py
sql_utilities.py

./db/queries:
001_create_db.sql

./models:
attachment.py
case.py
constants.py
filing.py
hashes.py
__init__.py
networking.py
raw_attachments.py
timestamp.py

./pipelines:
flyte_pipeline_wrappers.py
generic_pipeline_wrappers.py
helper_utils.py
raw_attachment_handling.py
test_ny.py

./scrapers:
base.py
co_puc.py
__init__.py
ma_puc.py
ny_puc.py
scraper_lookup.py

./server:
fetch_attachment_utils.py
main.py
static

./server/static:
index.html

```
However, we have this problem where the code inside dags references a bunch of other code in the project to deal with dependancies and stuff

but those files dont exist since the files get mounted in the dag directory like so:
```yaml
  volumes:
    - ${AIRFLOW_PROJ_DIR:-.}/dags:/opt/airflow/dags
    - ${AIRFLOW_PROJ_DIR:-.}/logs:/opt/airflow/logs
    - ${AIRFLOW_PROJ_DIR:-.}/config:/opt/airflow/config
    - ${AIRFLOW_PROJ_DIR:-.}/plugins:/opt/airflow/plugins
```

and the python code gets imported in the dags like so:

```py

from datetime import datetime
from typing import Any, List
from airflow.decorators import dag, task
from openpuc_scrapers.pipelines.generic_pipeline_wrappers import (
    generate_intermediate_object_save_path,
    get_all_caselist_raw,
    get_new_caselist_since_date,
    process_case,
)
from openpuc_scrapers.scrapers.scraper_lookup import (
    get_scraper_type_from_name_unvalidated,
)

from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.scrapers.base import StateCaseData, StateFilingData
# from functools import partial

default_args = {
    "owner": "airflow",
    "start_date": datetime(2023, 1, 1),
}


@dag(
    default_args=default_args,
    schedule_interval=None,
    params={"scraper_name": "unknown"},
    tags=["scrapers"],
)
def all_cases_dag():
    # NOTE: Logic code contained in here 
all_cases_workflow = all_cases_dag()
```

How should I set up this python repo so that airflow has access to all the code it needs.


Dont write anything just write a bit to help me think out how to structure these files.

Based on the files I've examined, here are some architectural approaches to solve the Airflow DAG import issue:

## Option 1: Package Installation in Airflow Container

The most robust solution is to install your `openpuc_scrapers` package in the Airflow container. This ensures all imports work correctly.

### Implementation:

1. **Create a Custom Airflow Docker Image**:
   - Build on top of the base Airflow image
   - Install your package during the build

2. **Package Structure**:
   - Ensure your package is properly structured with `setup.py` or `pyproject.toml`
   - Make sure all imports use the full package path (`from openpuc_scrapers.module import ...`)

3. **Dockerfile.airflow**:
   ```dockerfile
   FROM apache/airflow:2.10.5
   
   WORKDIR /app
   
   # Copy package structure
   COPY pyproject.toml ./
   COPY openpuc_scrapers/ ./openpuc_scrapers/
   
   # Install the package in development mode
   RUN pip install -e .
   
   # No need to copy DAGs separately as they'll be mounted
   ```

4. **Docker Compose Configuration**:
   - Update your compose file to use this custom image for Airflow services

## Option 2: Python Path Modification

If you prefer not to rebuild the image, you can modify the Python path in Airflow.

### Implementation:

1. **Mount the Entire Project**:
   ```yaml
   volumes:
     - ${AIRFLOW_PROJ_DIR:-.}:/opt/airflow/project
     - ${AIRFLOW_PROJ_DIR:-.}/dags:/opt/airflow/dags
   ```

2. **Add Python Path in Environment**:
   ```yaml
   environment:
     PYTHONPATH: /opt/airflow/project
   ```

3. **Create an Airflow Plugin**:
   - Create a file in the plugins directory that adds your project to the Python path

## Option 3: Restructure DAGs

Restructure your DAGs to be more self-contained or use relative imports.

### Implementation:

1. **Move Core Logic to Plugins**:
   - Move shared code to the Airflow plugins directory
   - Import from the plugins in your DAGs

2. **Duplicate Necessary Code**:
   - For small amounts of code, consider duplicating in the DAGs directory
   - Not ideal for maintenance but simplifies deployment

## Recommended Approach

Based on your setup, I recommend **Option 1: Package Installation** as the most robust solution. Your `Dockerfile.airflow` is already set up for this approach, but needs some refinements:

1. **Fix the Dockerfile.airflow**:
   - It currently has two FROM statements (one for Airflow, one for Python)
   - It should build on top of the Airflow image only
   - Install your package properly

2. **Update Docker Compose**:
   - Use your custom Airflow image for all Airflow services

3. **Ensure Package Structure**:
   - Make sure your package is properly installable
   - All imports should use the full package path

This approach ensures that:
1. Your DAGs can import from anywhere in the package
2. You maintain a clean separation of concerns
3. You avoid duplication of code
4. The solution is maintainable long-term

Would you like me to provide a specific implementation for any of these approaches?

**Generation complete!** Please review the code suggestions above.



## Recommended Architecture for Live Code Updates

### 1. Fix the Dockerfile.airflow

```dockerfile
FROM apache/airflow:2.10.5

WORKDIR /app

# Install UV for dependency management
RUN pip install --no-cache-dir uv

# We'll install dependencies but not copy the code
# Code will be mounted as a volume for live updates
COPY pyproject.toml uv.lock ./

# Generate and install dependencies
RUN uv pip compile pyproject.toml --output requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create a directory for the package
# The actual code will be mounted here at runtime
RUN mkdir -p /app/openpuc_scrapers

# Install the package in development mode
# This creates links to the code rather than copying it
WORKDIR /app
RUN pip install -e .

# Create entrypoint script
RUN echo '#!/bin/bash\n\
# Add the app directory to Python path\n\
export PYTHONPATH=$PYTHONPATH:/app\n\
\n\
# Execute the command passed to the container\n\
exec "$@"' > /entrypoint.sh

# Set permissions
USER root
RUN chmod +x /entrypoint.sh

# Switch back to airflow user
USER airflow

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
CMD ["airflow"]
```

### 2. Update docker-compose.yaml

Add these volume mounts to all Airflow services:

```yaml
volumes:
  - ${AIRFLOW_PROJ_DIR:-.}/dags:/opt/airflow/dags
  - ${AIRFLOW_PROJ_DIR:-.}/logs:/opt/airflow/logs
  - ${AIRFLOW_PROJ_DIR:-.}/config:/opt/airflow/config
  - ${AIRFLOW_PROJ_DIR:-.}/plugins:/opt/airflow/plugins
  - ${AIRFLOW_PROJ_DIR:-.}/openpuc_scrapers:/app/openpuc_scrapers
```

### 3. Create a Simple airflow-startup.sh Script

```bash
#!/bin/bash

# Add the app directory to Python path
export PYTHONPATH=$PYTHONPATH:/app

# Execute the command passed to the container
exec "$@"
```

### 4. Move DAGs to the Right Location

Ensure your DAG files are in the correct location:

```
/home/nicole/Documents/mycorrhizae/open-scrapers/dags/
```

Instead of:

```
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/dags/
```

### 5. Update Project Structure

Your project structure should look like:

```
open-scrapers/
├── dags/
│   ├── all_cases_dag.py
│   └── latest_cases_dag.py
├── openpuc_scrapers/
│   ├── __init__.py
│   ├── models/
│   ├── pipelines/
│   ├── scrapers/
│   └── ...
├── Dockerfile.airflow
├── docker-compose.yaml
└── pyproject.toml
```

## Implementation Steps

1. **Create the airflow-startup.sh script**:
   ```bash
   #!/bin/bash
   
   # Add the app directory to Python path
   export PYTHONPATH=$PYTHONPATH:/app
   
   # Execute the command passed to the container
   exec "$@"
   ```

2. **Fix the Dockerfile.airflow** as shown above

3. **Move DAG files** from `openpuc_scrapers/dags/` to the top-level `dags/` directory

4. **Update docker-compose.yaml** to include the volume mount for `openpuc_scrapers`

5. **Build and run** your updated Docker setup

## Benefits of This Approach

1. **Live Code Updates**: Changes to your `openpuc_scrapers` code will be immediately available in the Airflow container
2. **Proper Package Installation**: The package is installed in development mode, so imports work correctly
3. **Separation of Concerns**: DAGs are separate from your core package code
4. **Maintainability**: No code duplication or complex workarounds

This approach gives you the best of both worlds - proper package installation with the ability to make live code changes without rebuilding the container.

Would you like me to provide any specific implementation details for any of these steps?


