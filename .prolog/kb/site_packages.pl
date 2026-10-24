% flake.nix emits one directory per public vhost from the same Org source.
site_vhost(blog).
site_vhost(docs).
site_vhost(nsaspy).
site_build_parameter('STARINTEL_SITE_BASE_MAP', absolute_cross_vhost_urls).
