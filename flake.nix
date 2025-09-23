{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    naersk = {
      url = "github:nix-community/naersk";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    nix2container = {
      url = "github:nlewo/nix2container";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, naersk, nix2container }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      naersk' = pkgs.callPackage naersk {};
      nix2containerPkgs = nix2container.packages.${system};

      # Build the Rust application from uploader_api directory
      uploader-api = naersk'.buildPackage {
        src = ./uploader_api;
        name = "openscraper_uploader";

        # Add any additional build inputs if needed
        nativeBuildInputs = with pkgs; [
          pkg-config
        ];

        buildInputs = with pkgs; [
          openssl
        ];

        # Set environment variables for OpenSSL
        OPENSSL_NO_VENDOR = 1;
        PKG_CONFIG_PATH = "${pkgs.openssl.dev}/lib/pkgconfig";
      };

      # Create the OCI container using dockerTools
      uploader-api-container = pkgs.dockerTools.buildImage {
        name = "uploader-api";
        tag = "latest";

        copyToRoot = pkgs.buildEnv {
          name = "image-root";
          paths = [ uploader-api pkgs.coreutils pkgs.bash ];
          pathsToLink = [ "/bin" ];
        };

        config = {
          Cmd = [ "${uploader-api}/bin/openscraper_uploader" ];
          Env = [
            "PATH=/bin"
          ];
        };
      };

    in {
      packages.${system} = {
        default = uploader-api;
        uploader-api = uploader-api;
        container = container;
      };

      # Development shell
      devShells.${system}.default = pkgs.mkShell {
        nativeBuildInputs = with pkgs; [
          cargo
          rustc
          rust-analyzer
          pkg-config
        ];

        buildInputs = with pkgs; [
          openssl
        ];

        OPENSSL_NO_VENDOR = 1;
        PKG_CONFIG_PATH = "${pkgs.openssl.dev}/lib/pkgconfig";
      };

      # Apps for easy running
      apps.${system} = {
        default = {
          type = "app";
          program = "${uploader-api}/bin/openscraper_uploader";
        };

        build-uploader-api-container = {
          type = "app";
          program = "${pkgs.writeShellScript "build-container" ''
            set -euo pipefail
            echo "Building uploader api container..."
            if ! nix build .#uploader-api-container; then
              echo "Container build failed!" >&2
              exit 1
            fi
            echo "Container built successfully!"
            echo "Loading into Docker..."
            if ! docker load < result; then
              echo "Failed to load container into Docker!" >&2
              exit 1
            fi
            echo "Container loaded into Docker as uploader-api:latest"
          ''}";
        };
      };
    };
}
