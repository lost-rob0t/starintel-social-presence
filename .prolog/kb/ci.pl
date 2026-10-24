% Forgejo run 8219 failed at unauthenticated checkout of this private repo.
% Run 8221 passed checkout and metadata validation, then exposed a hygiene
% grep that matched its own script. The rule now matches YAML steps only.
ci_checkout_auth(private_forgejo_repo, ephemeral_job_token).
ci_hygiene_match(uses_step, yaml_list_item_only).
