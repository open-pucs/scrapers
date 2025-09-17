{ pkgs, lib, config, inputs, ... }:

{
  # Base configuration shared across all project devenvs
  dotenv.enable = true;
  dotenv.disableHint = true;
  cachix.enable = false;

  # Common packages available to all projects
  packages = with pkgs; [
    just
    curl
    jq
    git
  ];

  # https://devenv.sh/scripts/
  scripts.workspace-info.exec = ''
    echo "🦄 Mycorrhiza Scrapers Workspace"
    echo "==============================="
    echo
    echo "Available projects:"
    echo "  js_scrapers/    - Node.js scrapers with Playwright"
    echo "  uploader_api/   - Rust API server"
    echo
    echo "To work on a specific project:"
    echo "  cd js_scrapers && nix develop"
    echo "  cd uploader_api && nix develop"
    echo
  '';

  enterShell = ''
    workspace-info
  '';

  # See full reference at https://devenv.sh/reference/options/
}