{
  description = "StarIntel Emacs-first editorial workstation development shell";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs, ... }:
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

            env.STARINTEL_SITE_BASE_MAP = baseMapJson;

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
