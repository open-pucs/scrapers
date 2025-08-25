{
  description = "Nix flake for OpenPUC Scrapers development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # Configure nixpkgs to allow unfree packages (like Google Chrome)
        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;
          };
        };


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
          # libsql-client # this might be a problem
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
          # opentelemetry-distro
          opentelemetry-exporter-otlp
        ];

        python = pkgs.python312;

        # Selenium drivers
        chromedriver = pkgs.chromedriver;
        geckodriver = pkgs.geckodriver;

        # UV for Python package management
        uv = pkgs.uv;
        devPackages = with pkgs; [
          uv
          chromedriver
          geckodriver
          chromium
          firefox
        ];
        # Python environment with dependencies
        pythonEnv = python.withPackages (ps: projectDependencies);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = devPackages;
          nativeBuildInputs = with pkgs; [
            nodejs
            cypress
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
            # include all environment variables in .env
            if [ -f ".env" ]; then
                echo "Loading environment variables from .env..."
                set -a
                source .env
                set +a
            else
                echo "Warning: .env file not found"
            fi
            
            # Install dependencies with UV
            echo "Installing dependencies with UV..."
            uv pip install -e .
            opentelemetry-bootstrap --action=install
            
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
