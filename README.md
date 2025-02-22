# OpenPUC Scrapers

TODO: explain the whole deal

So far, `openpuc_scrapers` has coverage for the following state commissions.

| State | PUC                                  | Status |
|-------|--------------------------------------|--------|
| MA    | [Department of Public Utilities](https://eeaonline.eea.state.ma.us/DPU/Fileroom) | ✅ Available    |


## Installation

TODO easy peasy installation using pip

## Installation (for development)

To install and set up the project using Poetry, follow these steps:

1. **Clone the repository**:
    First, clone the repository to your local machine:
    ```bash
    git clone https://github.com/Open-PUCs/scrapers.git
    cd scrapers
    ```

2. **Install Poetry**:
    If you don’t have Poetry installed, you can install it by running the following command:
    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

3. **Ensure Python 3.11 is installed**:
    This is required for certain development dependencies
    ```bash
    poetry env use python 3.11
    ```

3. **Install dependencies**:
    Install all the required dependencies for the project using Poetry:
    ```bash
    poetry install
    ```

4. **Activate the virtual environment**:
    After installing the dependencies, activate the virtual environment:
    ```bash
    poetry shell
    ```

    This will activate the project's virtual environment, and you can start working on the package.
