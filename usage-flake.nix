{
  description = "Minimal flake for using SkySim";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.11";

    flake-utils = {
      url = "github:numtide/flake-utils";
      inputs.systems.follows = "nix-systems";
    };

    nix-systems.url = "github:nix-systems/default";
  };

  outputs =
    {
      self,
      nixpkgs,
      ...
    }@flake-inputs:
    let

      system = flake-inputs.flake-utils.lib.system.x86_64-linux;
      nixpkgs-for-system = sys: nixpkgs.legacyPackages.${sys};

    in
    {
      devShells.${system}.default =
        let
          pkgs = nixpkgs-for-system system;

          libraries = pkgs.lib.makeLibraryPath (
            with pkgs;
            [
              stdenv.cc.cc.lib
              zlib
            ]
          );

        in
        pkgs.mkShell {
          name = "skysim"; # name of dev env

          # set library path for python packages
          LD_LIBRARY_PATH = "${libraries}";

          packages = with pkgs; [
            poetry
            ffmpeg
          ];
        };

    };
}
