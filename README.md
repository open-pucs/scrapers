<p align="center">
  <img src="docs/source/_static/logo.png" alt="Project Logo" width="200">
</p>
<h1 align="center">OpenPUC Scrapers</h1>
<p align="center">
  <a href="https://open-pucs.github.io/scrapers/">
    <img src="https://img.shields.io/badge/docs-latest-blue.svg" alt="Documentation">
  </a>
  <a href="https://github.com/Open-PUCs/scrapers/actions/workflows/nox.yml">
    <img src="https://github.com/Open-PUCs/scrapers/actions/workflows/nox.yml/badge.svg?branch=main" alt="Tests">
  </a>
  <!-- <a href="https://codecov.io/gh/your-repo">
    <img src="https://codecov.io/gh/your-repo/branch/main/graph/badge.svg" alt="Code Coverage">
  </a>
  <a href="https://pypi.org/project/openpuc-scrapers/">
    <img src="https://img.shields.io/pypi/v/openpuc-scrapers.svg" alt="PyPI Version">
  </a> -->
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  </a>
</p>

<hr/>

`openpuc_scrapers` is an open-source Python package designed to democratize access to public utility commission (PUC) documents across different U.S. states. Too often, important information about state energy policy is hidden away in slow, hard-to-navigate websites. This package provides a unified interface for accessing case records, filings, and associated documents, regardless of state. Built with modular scrapers, standardized data models, and a lightweight design, OpenPUC Scrapers enables researchers, policymakers, and advocates to efficiently access regulatory information. 

So far, `openpuc_scrapers` has coverage for the following state commissions.

<div align="center">

| State | PUC                                  | Status |
|-------|--------------------------------------|--------|
| MA    | [Department of Public Utilities](https://eeaonline.eea.state.ma.us/DPU/Fileroom) | ✅ Available    |
| NY    | [Department of Public Service](https://documents.dps.ny.gov/public/common/search.html) | 🚧 Coming soon    |
| CA    | [Public Utilities Commission](https://apps.cpuc.ca.gov/apex/f?p=401:1:0) | 🚧 Coming soon    |
| MI    | [Public Service Commission](https://mi-psc.my.site.com/s/) | 🚧 Coming soon    |
| IL    | [Commerce Commission](https://www.icc.illinois.gov/) | 🚧 Coming soon    |

</div>

We welcome anyone interested in contributing an interface for a new PUC! Please create a new [issue](https://github.com/Open-PUCs/scrapers/issues) for each PUC you want to add and follow the steps for contributing in the [docs](https://open-pucs.github.io/scrapers/contributing.html).

## Getting started

### Using Nix (Recommended)

This project includes a Nix flake for reproducible development environments:

1. Install [Nix](https://nixos.org/download.html) if you haven't already
2. Enable flakes by adding to your `~/.config/nix/nix.conf`:
   ```
   experimental-features = nix-command flakes
   ```
3. Enter the development environment:
   ```bash
   nix develop
   ```
   
This will provide all necessary dependencies including:
- Python 3.12
- UV for package management
- Selenium with ChromeDriver and GeckoDriver
- All project dependencies

### Using pip

TODO easy peasy installation using pip
