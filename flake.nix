{
  description = "StarIntel Emacs-first editorial workstation development shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  inputs.starintel-server.flake = false;
  inputs.starintel-server.url = "github:lost-rob0t/starintel-server";
  inputs.quasar.flake = false;
  inputs.quasar.url = "github:lost-rob0t/quasar";
  inputs.starintel-auto-research.flake = false;
  inputs.starintel-auto-research.url = "github:lost-rob0t/starintel-auto-research";
  inputs.starintel-gpt-auto-dig.flake = false;
  inputs.starintel-gpt-auto-dig.url = "github:lost-rob0t/starintel-gpt-auto-dig";
  inputs.star-lang.flake = false;
  inputs.star-lang.url = "github:lost-rob0t/star-lang";
  inputs.starintel-doc.flake = false;
  inputs.starintel-doc.url = "github:lost-rob0t/starintel-doc";
  inputs.a0-symbolics.flake = false;
  inputs.a0-symbolics.url = "github:lost-rob0t/a0-symbolics";
  inputs.star-cl.flake = false;
  inputs.star-cl.url = "git+https://git.starintel.actor/nsaspy/star-cl";
  inputs.cl-couch.flake = false;
  inputs.cl-couch.url = "git+https://git.starintel.actor/nsaspy/cl-couch";
  inputs.star-bbpd.flake = false;
  inputs.star-bbpd.url = "git+https://git.starintel.actor/nsaspy/star-bbpd";
  inputs.starintel-client.flake = false;
  inputs.starintel-client.url = "git+https://git.starintel.actor/starintel-labs/starintel-client";
  inputs.rage.flake = false;
  inputs.rage.url = "git+https://git.starintel.actor/starintel-labs/RAGE";

  outputs = { self, nixpkgs, ... }@inputs:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;

      # Per-vhost public base URLs used when building releasable site
      # packages. Empty in the dev shell; the site package build fixes the
      # staging hostnames so cross-vhost links and assets are absolute.
      siteBaseMap = {
        www = "https://staging.starintel.actor";
        blog = "https://blog-staging.starintel.actor";
        docs = "https://docs-staging.starintel.actor";
        nsaspy = "https://nsaspy-staging.starintel.actor";
      };
      baseMapJson = builtins.toJSON siteBaseMap;
    in {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          emacs-site = (pkgs.emacsPackagesFor pkgs.emacs-nox).emacsWithPackages
            (epkgs: with epkgs; [ org-roam ]);
        in {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python313
              python313Packages.pytest
              python313Packages.pygments
              python313Packages.playwright
              uv
              emacs-site
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

      packages = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          emacs-site = (pkgs.emacsPackagesFor pkgs.emacs-nox).emacsWithPackages
            (epkgs: with epkgs; [ org-roam ]);
          python-site = pkgs.python313.withPackages (ps: [ ps.pygments ]);
          # Every public StarIntel repo: the docs vhost aggregates its
          # README landing plus docs/**.org and doc/**.org trees.
          repoInputs = {
            STARINTEL_SERVER_DIR = inputs.starintel-server;
            STARINTEL_QUASAR_DIR = inputs.quasar;
            STARINTEL_AUTO_RESEARCH_DIR = inputs.starintel-auto-research;
            STARINTEL_AUTO_DIG_DIR = inputs.starintel-gpt-auto-dig;
            STARINTEL_STAR_LANG_DIR = inputs.star-lang;
            STARINTEL_STARINTEL_DOC_DIR = inputs.starintel-doc;
            STARINTEL_A0_SYMBOLICS_DIR = inputs.a0-symbolics;
            STARINTEL_STAR_CL_DIR = inputs.star-cl;
            STARINTEL_CL_COUCH_DIR = inputs.cl-couch;
            STARINTEL_STAR_BBPD_DIR = inputs.star-bbpd;
            STARINTEL_STARINTEL_CLIENT_DIR = inputs.starintel-client;
            STARINTEL_RAGE_DIR = inputs.rage;
          };
          site = pkgs.stdenv.mkDerivation {
            pname = "starintel-social-presence-site";
            version = "unstable-${self.shortRev or "dirty"}";

            src = self;

            nativeBuildInputs = [
              emacs-site
              python-site
              pkgs.pandoc
              pkgs.git
            ];

            env = builtins.mapAttrs (name: path: toString path) repoInputs // {
              STARINTEL_SITE_BASE_MAP = baseMapJson;
            };

            buildPhase = ''
              export HOME=$TMPDIR/home
              mkdir -p "$HOME"
              export PYTHONPATH="$PWD/site_builder/src"
              export STARINTEL_SOCIAL_ROOT="$PWD"
              python3 -m starintel_site_builder.cli build \
                --root "$PWD" \
                --out "$out" \
                --build-dir "$TMPDIR/.build" \
                --base-map "$STARINTEL_SITE_BASE_MAP"
            '';

            passthru.vhosts = [ "www" "blog" "docs" "nsaspy" ];  # www built but not published

            dontStrip = true;
          };
          vhostPackage = name:
            pkgs.runCommand "starintel-site-${name}" { } ''
              mkdir -p $out
              ln -s ${site}/${name}/* $out/
            '';
          # The www/main-site vhost deploys from starintel-labs/website;
          # this repo publishes only blog, docs, and nsaspy.
          publishedVhosts = [ "blog" "docs" "nsaspy" ];
        in {
          site = site;
        } // builtins.listToAttrs (map
          (name: {
            name = name;
            value = vhostPackage name;
          })
          publishedVhosts));
    };
}
