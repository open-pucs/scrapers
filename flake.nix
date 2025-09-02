{
  description = "Nix flake for OpenPUC Scrapers development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    devenv.url = "github:cachix/devenv";
  };

  outputs = { self, nixpkgs, flake-utils, devenv }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # Configure nixpkgs to allow unfree packages (like Google Chrome)
        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;
          };
        };

        # Python environment with dependencies
        pythonEnv = pkgs.python312.withPackages (ps: with ps; [
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
        ]);
      in
      {
        devShells.default = devenv.lib.mkShell {
          inherit pkgs;
          devenv = ./devenv.nix;
        };

        # For direct usage without shell
        packages.default = pythonEnv;
      });
}
