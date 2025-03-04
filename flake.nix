{
  description = "Template for Python Development";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.11";

    flake-utils = {
      url = "github:numtide/flake-utils";
      inputs.systems.follows = "nix-systems";
    };

    nix-systems.url = "github:nix-systems/default";

    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    ignoreboy = {
      url = "github:ookiiboy/ignoreboy";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.systems.follows = "nix-systems";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      ...
    }@flake-inputs:
    let
      treefmt-for-system =
        system:
        flake-inputs.treefmt-nix.lib.evalModule (nixpkgs-for-system system) {
          programs = {
            # generic
            dos2unix.enable = true;

            # python
            mypy.enable = true; # static type checker
            black.enable = true;

            # other
            nixfmt.enable = true;
            shellcheck.enable = true;
          };
        };

      system = flake-inputs.flake-utils.lib.system.x86_64-linux;
      nixpkgs-for-system = sys: nixpkgs.legacyPackages.${sys};

    in
    {
      # nix fmt
      formatter.${system} = (treefmt-for-system system).config.build.wrapper;

      # nix flake check
      checks.${system} = {
        formatting = (treefmt-for-system system).config.build.check self;
      };

      devShells.${system}.default =
        let
          pkgs = nixpkgs-for-system system;

          gitignore = flake-inputs.ignoreboy.lib.${system}.gitignore {
            github.languages = [
              "Python"
              "community/Python/JupyterNotebooks"
            ];

            useSaneDefaults = true; # adds OS and Nix-specific entries

            # extra custom entries
            extraConfig = ''
              *.py:Zone.Identifier
              docs/source/generated
              .testmondata
              .testmondata*
            '';
          };
          libraries = pkgs.lib.makeLibraryPath (
            with pkgs;
            [
              stdenv.cc.cc.lib
              zlib
              libmysqlclient
            ]
          );
        in
        pkgs.mkShell {
          name = "skysim"; # name of dev env

          # set library path for python packages
          LD_LIBRARY_PATH = "${libraries}";

          shellHook = ''
            ${gitignore}
          '';

          packages = with pkgs; [
            poetry
            pkg-config # for poetry to locate dependencies
            just # command runner (per-project aliases)
          ];
        };

    };
}
