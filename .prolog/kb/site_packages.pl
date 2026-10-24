% flake.nix emits one directory per public vhost from the same Org source.
site_vhost(blog).
site_vhost(docs).
site_vhost(nsaspy).
site_build_parameter('STARINTEL_SITE_BASE_MAP', absolute_cross_vhost_urls).
site_publication_filter(imported_org_document, tenant_identifier, omit_page).
site_publication_gate(rendered_output, tenant_identifier, reject_build).
