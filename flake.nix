{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixpkgs-playwright.url = "github:NixOS/nixpkgs/nixos-unstable";
    nix2container.url = "github:nlewo/nix2container";
    nix2container.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, nixpkgs-playwright, nix2container }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      pkgs-playwright = nixpkgs-playwright.legacyPackages.${system};

      # Import the scraper derivation from js_scrapers
      scraperMainDerivation = import ./js_scrapers/main.nix {
        inherit pkgs pkgs-playwright system;
      };

      # nix2container packages
      nix2containerPkgs = nix2container.packages.${system};

    in {
      packages.${system} = {
        # Add the node packages as a package
        js-scrapers = scraperMainDerivation.package;
        default = scraperMainDerivation.package;

        # Container image
        container = nix2containerPkgs.nix2container.buildImage {
          name = "utility-scrapers";
          config = {
            entrypoint = [ "${pkgs.nodePackages.ts-node}/bin/ts-node" ];
            cmd = [ "playwright/ny_puc_scraper.spec.ts" ];
            env = [
              "PLAYWRIGHT_BROWSERS_PATH=${pkgs-playwright.playwright.browsers}"
              "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1"
              "PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true"
              "PLAYWRIGHT_NODEJS_PATH=${pkgs.nodejs_20}/bin/node"
              "NODE_PATH=${scraperMainDerivation.package}/lib/node_modules/js_scrapers/node_modules"
            ];
            workingDir = "${scraperMainDerivation.package}/lib/node_modules/js_scrapers";
          };
        };
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
      apps.${system} = scraperMainDerivation.apps;
    };
}
