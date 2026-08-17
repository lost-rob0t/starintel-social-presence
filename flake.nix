{
  description = "StarIntel Emacs-first editorial workstation development shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.prolog-rlm = {
    url = "github:lost-rob0t/prolog-rlm/7b527750a64d5cbd9fff79413a399a8c69e90c75";
    flake = false;
  };

  outputs = { nixpkgs, prolog-rlm, ... }:
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
              uv
              pkgs."swi-prolog"
              emacs-nox
              git
              ffmpeg
              pandoc
              graphviz
              ripgrep
            ];

            shellHook = ''
              export PROLOG_RLM_DIR="${prolog-rlm}"
              export PYTHONPATH="$PWD/change_fetcher/src:$PWD/auto_findings/src:$PWD/auto_research/src:$PWD/starintel_tutorial_gen/src''${PYTHONPATH:+:$PYTHONPATH}"
            '';
          };
        });
    };
}
