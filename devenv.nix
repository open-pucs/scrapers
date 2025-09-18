{ pkgs, lib, config, inputs, ... }:

let
  pkgs-playwright = import inputs.nixpkgs-playwright { system = pkgs.stdenv.system; };
  browsers = (builtins.fromJSON (builtins.readFile "${pkgs-playwright.playwright-driver}/browsers.json")).browsers;
  chromium-rev = (builtins.head (builtins.filter (x: x.name == "chromium") browsers)).revision;
in
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
    # JS/TS specific packages
    nodejs
    nodePackages.ts-node
    typescript
    # Rust-specific packages
    rustc
    cargo
    rustfmt
    rust-analyzer
    clippy
    pkg-config
    openssl
  ];

  # https://devenv.sh/languages/
  languages.javascript = {
    enable = true;
    pnpm = {
      enable = true;
      install.enable = true;
    };
  };
  languages.typescript = {
    enable = true;
  };
  languages.rust = {
    enable = true;
    channel = "stable";
  };

  # Environment variables
  env = {
    PLAYWRIGHT_BROWSERS_PATH = "${pkgs-playwright.playwright.browsers}";
    PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = true;
    PLAYWRIGHT_NODEJS_PATH = "${pkgs.nodejs}/bin/node";
    PLAYWRIGHT_LAUNCH_OPTIONS_EXECUTABLE_PATH = "${pkgs-playwright.playwright.browsers}/chromium-${chromium-rev}/chrome-linux/chrome";
    RUST_LOG = "debug";
    PKG_CONFIG_PATH = "${pkgs.openssl.dev}/lib/pkgconfig";
  };

  # https://devenv.sh/scripts/
  scripts.workspace-info.exec = ''
    echo "🦄 Mycorrhiza Scrapers Workspace"
    echo "==============================="
    echo
    echo "This is a combined environment for all projects."
    echo
    js-intro
    rust-intro
  '';

  scripts.js-intro.exec = ''
    echo "🕷️ JS Scrapers Development Environment"
    echo "======================================"
    echo
    # Check if js_scrapers/package.json exists before trying to read it
    if [ -f "js_scrapers/package.json" ]; then
      playwrightNpmVersion="$(node -p "require('./js_scrapers/package.json').devDependencies['@playwright/test']")"
      echo "❄️ Playwright nix version: ${pkgs-playwright.playwright.version}"
      echo "📦 Playwright npm version: $playwrightNpmVersion"

      if [ "${pkgs-playwright.playwright.version}" != "$playwrightNpmVersion" ]; then
          echo "❌ Playwright versions in nix (in devenv.yaml) and npm (in package.json) are not the same! Please adapt the configuration."
      else
          echo "✅ Playwright versions in nix and npm are the same"
      fi
    else
      echo "Could not find js_scrapers/package.json"
    fi

    echo
    echo "Available commands for JS Scrapers:"
    echo "  (cd js_scrapers && npx playwright test)     - Run tests"
    echo "  (cd js_scrapers && npx playwright codegen)  - Generate tests"
    echo "  (cd js_scrapers && pnpm install)           - Install dependencies"
    echo
    env | grep ^PLAYWRIGHT
  '';

  scripts.rust-intro.exec = ''
    echo "🦀 Uploader API Development Environment"
    echo "======================================"
    echo
    echo "🦀 Rust version: $(rustc --version)"
    echo "📦 Cargo version: $(cargo --version)"
    echo
    echo "Available commands for Uploader API:"
    echo "  (cd uploader_api && cargo run)          - Start the API server"
    echo "  (cd uploader_api && cargo test)         - Run tests"
    echo "  (cd uploader_api && cargo build)        - Build the project"
    echo "  (cd uploader_api && cargo clippy)       - Run linter"
    echo "  (cd uploader_api && cargo fmt)          - Format code"
    echo
  '';

  scripts.dev.exec = ''
    echo "🚀 Starting uploader API in development mode..."
    (cd uploader_api && cargo run)
  '';

  scripts.build.exec = ''
    echo "🔨 Building uploader API..."
    (cd uploader_api && cargo build)
  '';

  scripts.test.exec = ''
    echo "🧪 Running uploader API tests..."
    (cd uploader_api && cargo test)
  '';

  enterShell = ''
    workspace-info
  '';

  # See full reference at https://devenv.sh/reference/options/
}
