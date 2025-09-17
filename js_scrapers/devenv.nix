{ pkgs, lib, config, inputs, ... }:

let
  pkgs-playwright = import inputs.nixpkgs-playwright { system = pkgs.stdenv.system; };
  browsers = (builtins.fromJSON (builtins.readFile "${pkgs-playwright.playwright-driver}/browsers.json")).browsers;
  chromium-rev = (builtins.head (builtins.filter (x: x.name == "chromium") browsers)).revision;
in
{
  # Import base workspace configuration
  imports = [
    ../devenv.nix
  ];

  # Playwright-specific environment variables
  env = {
    PLAYWRIGHT_BROWSERS_PATH = "${pkgs-playwright.playwright.browsers}";
    PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = true;
    PLAYWRIGHT_NODEJS_PATH = "${pkgs.nodejs}/bin/node";
    PLAYWRIGHT_LAUNCH_OPTIONS_EXECUTABLE_PATH = "${pkgs-playwright.playwright.browsers}/chromium-${chromium-rev}/chrome-linux/chrome";
  };

  # JS/TS specific packages
  packages = with pkgs; [
    nodejs
    nodePackages.ts-node
    typescript
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

  # https://devenv.sh/scripts/
  scripts.intro.exec = ''
    echo "🕷️ JS Scrapers Development Environment"
    echo "======================================"
    echo
    playwrightNpmVersion="$(node -p "require('./package.json').devDependencies['@playwright/test']")"
    echo "❄️ Playwright nix version: ${pkgs-playwright.playwright.version}"
    echo "📦 Playwright npm version: $playwrightNpmVersion"

    if [ "${pkgs-playwright.playwright.version}" != "$playwrightNpmVersion" ]; then
        echo "❌ Playwright versions in nix (in devenv.yaml) and npm (in package.json) are not the same! Please adapt the configuration."
    else
        echo "✅ Playwright versions in nix and npm are the same"
    fi

    echo
    echo "Available commands:"
    echo "  npx playwright test     - Run tests"
    echo "  npx playwright codegen  - Generate tests"
    echo "  pnpm install           - Install dependencies"
    echo
    env | grep ^PLAYWRIGHT
  '';

  enterShell = ''
    intro
  '';

  # See full reference at https://devenv.sh/reference/options/
}
