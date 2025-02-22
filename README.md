# OpenPUC Scrapers

TODO: explain the whole deal

So far, `openpuc_scrapers` has coverage for the following state commissions.

| State | PUC                                  | Status |
|-------|--------------------------------------|--------|
| MA    | [Department of Public Utilities](https://eeaonline.eea.state.ma.us/DPU/Fileroom) | ✅ Available    |


## Installation

TODO easy peasy installation using pip

## Contributing

We welcome contributions to **OpenPUC Scrapers**! Follow these steps to set up your development environment and submit contributions.

### 1. Fork and Clone the Repository
First, fork the repository on GitHub and then clone your fork:
```bash
git clone https://github.com/your-username/scrapers.git
cd scrapers
```

### 2. Set Up the Environment
Ensure you have **Poetry** installed:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```
Then, install dependencies (Python 3.11 for development is recommended):
```bash
poetry env use python3.11
poetry install
```

### 3. Install Pre-Commit Hooks
Run the following to install **pre-commit hooks**:
```bash
pre-commit install
```
To test all hooks manually:
```bash
pre-commit run --all-files
```

### 4. Run Tests and Linting
Before submitting changes, ensure all tests pass and code follows standards:
```bash
nox -s tests
nox -s mypy
nox -s lint
```
or just run `nox` to run all checks.

### 5. Create a Feature Branch
Follow a descriptive naming convention:
```bash
git checkout -b feature/add-new-scraper
```

### 6. Commit and Push
Format your commit messages properly:
```bash
git commit -m "Add scraper for [state PUC]"
git push origin feature/add-new-scraper
```

### 7. Submit a Pull Request
- Open a **Pull Request (PR)** on GitHub.  
- Link any relevant **issues**.  
- Wait for a **code review** and address any feedback.  

### 8. Join the Discussion
If you have ideas or issues, start a discussion in the **Issues** tab!  

Thanks for contributing! 🚀

