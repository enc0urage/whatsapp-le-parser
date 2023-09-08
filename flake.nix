{
  "description" = "Toolkit for parsing Whatsapp law enforcement data requests";
  "inputs" = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    utils.url = "github:numtide/flake-utils";
  };
  outputs = {
    self,
    nixpkgs,
    utils,
  }:
    utils.lib.eachDefaultSystem (
      system: let
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        packages.default = pkgs.poetry2nix.mkPoetryApplication {
          projectDir = ./.;
          preferWheels = true;
        };
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [parallel poetry];
        };
        formatter = pkgs.writeShellApplication {
          name = "treefmt-wrapped";
          runtimeInputs = with pkgs; [alejandra black];
          text = "${pkgs.treefmt}/bin/treefmt";
        };
      }
    );
}
