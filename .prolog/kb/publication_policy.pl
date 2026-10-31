% Publication privacy policy for web-facing content.
% Established 2026-10-30 after Shipyard 001-003 accumulated links to
% repositories that later went private (404 for anonymous readers).
%
% Policy: web-facing Org (blog/posts/, nsaspy/) must never link to or
% name a repository that is not publicly reachable. Refer to private
% components generically ("the actor fleet", "the deployment
% repository") and record merged SHAs only in :noexport: editorial
% sections, with the repository labeled unlinked.

policy(private_repos_unlinked).

% Gate checks enforcing the policy (wired into scripts/check).
gate_check('scripts/check_no_private_links.py',
           'web-facing Org must not name a private repository slug').
gate_check('scripts/check_links.py',
           'every http(s) link in web-facing Org must open: HTTP 2xx/3xx').

% Slugs treated as private by the offline scan (site_builder
% private_links.PRIVATE_PATTERNS). Update both when visibility changes.
private_slug('starintel-pro-actors').
private_slug('starintel-biz').
private_slug('starintel-infra').
private_slug('starintel-farm').
private_slug('starintel-discord-reporting').
private_slug('ohmycaptcha').

% Publicly reachable homes verified by anonymous HTTP on 2026-10-30.
public_home('starintel-server', ['git.starintel.actor/starintel-labs', 'github.com/lost-rob0t']).
public_home('starintel-social-presence', ['github.com/lost-rob0t']).
public_home('quasar', ['git.starintel.actor/nsaspy', 'github.com/lost-rob0t']).
public_home('star-face', ['git.starintel.actor/starintel-labs']).
public_home('star-lang', ['git.starintel.actor/nsaspy', 'github.com/lost-rob0t']).
public_home('starintel-gpt-auto-dig', ['git.starintel.actor/starintel-labs']).
public_home('website', ['github.com/starintel-labs']).

% A published private-repo mention is redacted to generic prose with a
% revision bump; the site badge then shows the correction.
redaction_revision_bump(true).
