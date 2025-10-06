{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixpkgs-playwright.url = "github:NixOS/nixpkgs/nixos-unstable";
    nix2container.url = "github:nlewo/nix2container";
    nix2container.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, nixpkgs-playwright, nix2container }:
    let
      supportedSystems = [ "x86_64-linux" "x86_64-darwin" ];

      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;

      pkgsFor = system: nixpkgs.legacyPackages.${system};
      pkgsPlaywrightFor = system: nixpkgs-playwright.legacyPackages.${system};

    in {
      packages = forAllSystems (system:
        let
          pkgs = pkgsFor system;
          pkgs-playwright = pkgsPlaywrightFor system;

          # Import the scraper derivation from js_scrapers
          scraperMainDerivation = import ./js_scrapers/main.nix {
            inherit pkgs pkgs-playwright system;
          };

        in {
          # Add the node packages as a package
          js-scrapers = scraperMainDerivation.package;
          default = scraperMainDerivation.package;
        } // (nixpkgs.lib.optionalAttrs (system == "x86_64-linux") {
          # Container image (Linux only)
          container = nix2container.packages.${system}.nix2container.buildImage {
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
        }));

      # Apps for easy running
      apps = forAllSystems (system:
        let
          pkgs = pkgsFor system;
          pkgs-playwright = pkgsPlaywrightFor system;

          scraperMainDerivation = import ./js_scrapers/main.nix {
            inherit pkgs pkgs-playwright system;
          };
        in scraperMainDerivation.apps);
    };
}
