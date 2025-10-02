{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixpkgs-playwright.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, nixpkgs-playwright }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      pkgs-playwright = nixpkgs-playwright.legacyPackages.${system};

      # Import the node2nix generated packages
      nodePackages = import ./js_scrapers/default.nix {
        inherit pkgs system;
        nodejs = pkgs.nodejs_20;  # Use Node.js 20 instead of default 14
      };

    in {
      packages.${system} = {
        # Add the node packages as a package
        js-scrapers = nodePackages.package;
        default = nodePackages.package;
      };

      # Development shells
      devShells.${system} = {
        default = pkgs.mkShell {
          nativeBuildInputs = with pkgs; [
            # Node.js toolchain
            nodejs_20
            nodePackages.pnpm
            nodePackages.typescript
            nodePackages.ts-node

            # Playwright
            pkgs-playwright.playwright-driver

            # Additional tools
            git
          ];

          # Environment variables (matching devenv.nix setup)
          PLAYWRIGHT_BROWSERS_PATH = "${pkgs-playwright.playwright.browsers}";
          PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = 1;
          PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = true;
          PLAYWRIGHT_NODEJS_PATH = "${pkgs.nodejs_20}/bin/node";

          shellHook = ''
            echo "🎭 JavaScript Scrapers Environment"
            echo "📍 Working directory: $(pwd)"
            echo "🎭 Playwright browsers: $PLAYWRIGHT_BROWSERS_PATH"
            echo ""
            echo "Available commands:"
            echo "  cd js_scrapers && pnpm install"
            echo "  ts-node playwright/ny_puc_scraper.spec.ts --mode all --begin-date 2025-01-01 --end 2025-01-05 --outfile test.json"
            echo ""
          '';
        };
      };

      # Apps for easy running
      apps.${system} = {
        # NY PUC Scraper app - callable from other binaries
        default = {
          type = "app";
          program = "${pkgs.writeShellScript "ny-puc-scraper" ''
            set -euo pipefail

            # Set up environment
            export PLAYWRIGHT_BROWSERS_PATH="${pkgs-playwright.playwright.browsers}"
            export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
            export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
            export PLAYWRIGHT_NODEJS_PATH="${pkgs.nodejs_20}/bin/node"

            # Use the built node_modules from node2nix
            export NODE_PATH="${nodePackages.package}/lib/node_modules/js_scrapers/node_modules"
            cd "${nodePackages.package}/lib/node_modules/js_scrapers"

            # Run the scraper with all arguments passed through
            echo "Running NY PUC scraper..."
            ${pkgs.nodePackages.ts-node}/bin/ts-node playwright/ny_puc_scraper.spec.ts "$@"
          ''}";
        };

        ny-puc-scraper = {
          type = "app";
          program = "${pkgs.writeShellScript "ny-puc-scraper" ''
            set -euo pipefail

            # Set up environment
            export PLAYWRIGHT_BROWSERS_PATH="${pkgs-playwright.playwright.browsers}"
            export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
            export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
            export PLAYWRIGHT_NODEJS_PATH="${pkgs.nodejs_20}/bin/node"

            # Use the built node_modules from node2nix
            export NODE_PATH="${nodePackages.package}/lib/node_modules/js_scrapers/node_modules"
            cd "${nodePackages.package}/lib/node_modules/js_scrapers"

            # Run the scraper with all arguments passed through
            echo "Running NY PUC scraper..."
            ${pkgs.nodePackages.ts-node}/bin/ts-node playwright/ny_puc_scraper.spec.ts "$@"
          ''}";
        };
      };
    };
}
