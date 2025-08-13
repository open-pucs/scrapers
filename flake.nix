{
  description = "Nix flake for OpenPUC Scrapers development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Python version and packages
        python = pkgs.python312;

        # Selenium drivers
        chromedriver = pkgs.chromedriver;
        geckodriver = pkgs.geckodriver;

        # UV for Python package management
        uv = pkgs.uv;

        # Project dependencies from pyproject.toml
        projectDependencies = with pkgs.python312Packages; [
          aioboto3
          aiohttp
          aiosqlite
          asyncpg
          beautifulsoup4
          faker
          jinja2
          langchain-community
          langchain-core
          libsql-client
          psycopg2
          pydantic
          pymupdf
          pymupdf4llm
          pytest
          redis
          requests
          selenium
          sqlalchemy
          fastapi
          uvicorn
        ];

        # Development environment
        devPackages = with pkgs; [
          python
          uv
          chromedriver
          geckodriver
          google-chrome
          firefox
        ];

        # Python environment with dependencies
        pythonEnv = python.withPackages (ps: projectDependencies);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = devPackages;
          nativeBuildInputs = with pkgs; [
            python
            uv
          ];

          shellHook = ''
            # Set up environment variables for Selenium drivers
            export PATH="${chromedriver}/bin:${geckodriver}/bin:$PATH"
            
            # Set up Python environment
            export PYTHONPATH="${pythonEnv}/${python.sitePackages}:$PYTHONPATH"
            
            # Create virtual environment with UV
            if [ ! -d ".venv" ]; then
              echo "Creating virtual environment with UV..."
              uv venv --python ${python}/bin/python
            fi
            
            # Activate virtual environment
            source .venv/bin/activate
            
            # Install dependencies with UV
            echo "Installing dependencies with UV..."
            uv pip install -e .
            
            echo "Development environment is ready!"
            echo "Python: $(which python)"
            echo "UV: $(which uv)"
            echo "ChromeDriver: $(which chromedriver)"
            echo "GeckoDriver: $(which geckodriver)"
          '';
        };

        # For direct usage without shell
        packages.default = pythonEnv;
      });
}