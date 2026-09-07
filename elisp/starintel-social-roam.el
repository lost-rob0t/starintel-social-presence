;;; starintel-social-roam.el --- Treat the repo as a real org-roam vault -*- lexical-binding: t; -*-

;; The editorial content (blog/, docs/, nsaspy/) is ordinary org-roam
;; content. Opening any Org file in this repository points org-roam at the
;; repository root with a repo-local database, so backlinks, node insert,
;; the roam buffer, and org-roam-ui work in the author's editor exactly as
;; they do for any other vault. The site builder consumes the same
;; database; it never maintains a parallel graph.

(require 'subr-x)

(defgroup starintel-social-roam nil
  "org-roam vault integration for the StarIntel editorial desk."
  :group 'starintel-social)

(defconst starintel-social-roam-db-relative ".cache/org-roam.db"
  "Repo-local org-roam database location, shared with the site builder.")

(defun starintel-social-roam--repo-root ()
  "Return the repository root for the current buffer, if any."
  (or (when (bound-and-true-p starintel-social-root)
        (and (file-directory-p starintel-social-root) starintel-social-root))
      (locate-dominating-file default-directory ".dir-locals.el")
      (locate-dominating-file default-directory "starintel-social.el")))

(defun starintel-social-roam-vault-setup ()
  "Make org-roam treat this repository as its own vault, buffer-locally.
Safe to call from `eval' in .dir-locals.el. Degrades cleanly when
org-roam is not installed."
  (when-let* ((root (starintel-social-roam--repo-root)))
    (setq-local org-roam-directory (file-name-as-directory root))
    (setq-local org-roam-db-location
                (expand-file-name starintel-social-roam-db-relative root))))

(defun starintel-social-roam-sync ()
  "Sync the repository vault's org-roam database."
  (interactive)
  (unless (require 'org-roam nil t)
    (user-error "org-roam is not installed"))
  (starintel-social-roam-vault-setup)
  (org-roam-db-sync)
  (message "org-roam db synced: %s" org-roam-db-location))

(defun starintel-social-roam-vault-nodes ()
  "Return org-roam nodes restricted to this repository's vault."
  (unless (require 'org-roam nil t)
    (user-error "org-roam is not installed"))
  (let ((root (starintel-social-roam--repo-root)))
    (seq-filter
     (lambda (node)
       (string-prefix-p root (org-roam-node-file node)))
     (org-roam-node-list))))

(defun starintel-social-roam-insert-link ()
  "Insert an org-roam link restricted to this repository's content."
  (interactive)
  (unless (require 'org-roam nil t)
    (user-error "org-roam is not installed"))
  (let* ((nodes (starintel-social-roam-vault-nodes))
         (node (org-roam-node-read nil nodes)))
    (insert (format "[[id:%s][%s]]"
                    (org-roam-node-id node)
                    (org-roam-node-title node)))))

(provide 'starintel-social-roam)
;;; starintel-social-roam.el ends here
