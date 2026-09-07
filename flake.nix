{
  description = "StarIntel Emacs-first editorial workstation development shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { nixpkgs, ... }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python313
              python313Packages.pytest
              python313Packages.pygments
              python313Packages.playwright
              uv
              emacs-nox
              git
              ffmpeg
              pandoc
              graphviz
              ripgrep
              chromium
            ];

            shellHook = ''
              export PYTHONPATH="$PWD/change_fetcher/src:$PWD/auto_findings/src:$PWD/auto_research/src:$PWD/starintel_tutorial_gen/src:$PWD/site_builder/src''${PYTHONPATH:+:$PYTHONPATH}"
            '';
          };
        });
    };
}
