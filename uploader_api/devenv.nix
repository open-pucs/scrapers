{ pkgs, lib, config, inputs, ... }:

{
  # Import base workspace configuration
  imports = [
    ../devenv.nix
  ];

  # Rust-specific packages
  packages = with pkgs; [
    rustc
    cargo
    rustfmt
    rust-analyzer
    clippy
    pkg-config
    openssl
  ];

  # https://devenv.sh/languages/
  languages.rust = {
    enable = true;
    channel = "stable";
  };

  # Environment variables for Rust development
  env = {
    RUST_LOG = "debug";
    PKG_CONFIG_PATH = "${pkgs.openssl.dev}/lib/pkgconfig";
  };

  # https://devenv.sh/scripts/
  scripts.intro.exec = ''
    echo "🦀 Uploader API Development Environment"
    echo "======================================"
    echo
    echo "🦀 Rust version: $(rustc --version)"
    echo "📦 Cargo version: $(cargo --version)"
    echo
    echo "Available commands:"
    echo "  cargo run          - Start the API server"
    echo "  cargo test         - Run tests"
    echo "  cargo build        - Build the project"
    echo "  cargo clippy       - Run linter"
    echo "  cargo fmt          - Format code"
    echo
  '';

  scripts.dev.exec = ''
    echo "🚀 Starting uploader API in development mode..."
    cargo run
  '';

  scripts.build.exec = ''
    echo "🔨 Building uploader API..."
    cargo build
  '';

  scripts.test.exec = ''
    echo "🧪 Running uploader API tests..."
    cargo test
  '';

  enterShell = ''
    intro
  '';

  # See full reference at https://devenv.sh/reference/options/
}