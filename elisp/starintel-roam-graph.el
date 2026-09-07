;;; starintel-roam-graph.el --- Build an org-roam db for the site builder -*- lexical-binding: t; -*-

;; The site builder consumes org-roam's own sqlite database instead of
;; re-parsing Org link syntax. This entry point points org-roam at the
;; repository content and syncs the database into the build directory.

(require 'org-roam)

(defun starintel-roam-graph-sync (root db-file)
  "Sync the org-roam database for Org files under ROOT into DB-FILE.
Returns the database location."
  (setq org-roam-directory (file-name-as-directory (expand-file-name root)))
  (setq org-roam-db-location (expand-file-name db-file))
  (org-roam-db-sync)
  org-roam-db-location)

(provide 'starintel-roam-graph)
;;; starintel-roam-graph.el ends here
