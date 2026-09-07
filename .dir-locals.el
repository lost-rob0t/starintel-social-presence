;;; Directory-local variables for the StarIntel editorial workstation.
;; org-roam treats this repository as a vault: backlinks, node insert, and
;; the roam buffer work on blog/, docs/, and nsaspy/ content in the editor,
;; and the site builder consumes the same repo-local database.

((org-mode
  . ((eval . (progn
               (require 'starintel-social-roam nil t)
               (when (fboundp 'starintel-social-roam-vault-setup)
                 (starintel-social-roam-vault-setup))))))))
