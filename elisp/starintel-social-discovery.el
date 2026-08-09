;;; starintel-social-discovery.el --- Discovery and production buffers -*- lexical-binding: t; -*-

(require 'json)
(require 'tabulated-list)
(require 'subr-x)

(defgroup starintel-social-discovery nil
  "StarIntel editorial discovery."
  :group 'starintel-social)

(defcustom starintel-social-repositories-directory
  (let ((value (getenv "STARINTEL_REPOSITORIES_DIR")))
    (and value (not (string-empty-p value)) (expand-file-name value)))
  "Optional directory containing StarIntel Git checkouts.
When set, immediate Git repositories whose name or origin mentions StarIntel
are included alongside the explicitly configured repository paths."
  :type '(choice (const :tag "Disabled" nil) directory))

(defvar-local starintel-social--discovery-items nil)
(defvar-local starintel-social--discovery-kind nil)

(defun starintel-social--git-directory-p (directory)
  (file-directory-p (expand-file-name ".git" directory)))

(defun starintel-social--repository-label (directory)
  (let ((origin (starintel-social--git-string directory "remote" "get-url" "origin")))
    (if (string-empty-p origin) (file-name-nondirectory (directory-file-name directory))
      (replace-regexp-in-string "\\.git\\'" "" origin))))

(defun starintel-social--git-string (directory &rest arguments)
  (with-temp-buffer
    (if (zerop (apply #'call-process "git" nil t nil "-C" directory arguments))
        (string-trim (buffer-string))
      "")))

(defun starintel-social--configured-repositories ()
  "Return available local StarIntel repositories without a hard-coded catalog."
  (let* ((environment-names '("STARINTEL_SERVER_DIR" "STARINTEL_AUTO_DIG_DIR"
                              "STARINTEL_AUTO_RESEARCH_DIR" "STARINTEL_QUASAR_DIR"
                              "STARINTEL_QUASAR_UI_DIR"))
         (configured (delq nil (mapcar (lambda (name)
                                         (let ((value (getenv name)))
                                           (and value (not (string-empty-p value))
                                                (expand-file-name value))))
                                       environment-names)))
         (discovered
          (when (file-directory-p starintel-social-repositories-directory)
            (seq-filter
             (lambda (directory)
               (and (file-directory-p directory)
                    (starintel-social--git-directory-p directory)
                    (string-match-p "star\\|quasar" (downcase (file-name-nondirectory directory)))))
             (directory-files starintel-social-repositories-directory t directory-files-no-dot-files-regexp))))
         (repositories (delete-dups (append configured discovered))))
    (mapcar (lambda (directory) (cons (starintel-social--repository-label directory) directory))
            (seq-filter #'starintel-social--git-directory-p repositories))))

(defun starintel-social--call-python-json (module &rest arguments)
  (let ((process-environment (copy-sequence process-environment))
        (buffer (generate-new-buffer " *starintel-social-json*")))
    (setenv "PYTHONPATH" (starintel-social--python-path))
    (unwind-protect
        (if (zerop (apply #'call-process "python3" nil buffer nil "-m" module arguments))
            (with-current-buffer buffer
              (goto-char (point-min))
              (json-parse-buffer :object-type 'alist :array-type 'list))
          (error "%s failed: %s" module (with-current-buffer buffer (buffer-string))))
      (kill-buffer buffer))))

(defun starintel-social--feature-items (&optional since)
  (let ((range (or since "14 days ago")) result)
    (dolist (repository (starintel-social--configured-repositories))
      (let* ((label (car repository))
             (directory (cdr repository))
             (lines (split-string (starintel-social--git-string
                                   directory "log" (format "--since=%s" range)
                                   "--max-count=40" "--format=%H%x1f%aI%x1f%s") "\n" t)))
        (dolist (line lines)
          (pcase-let ((`(,commit ,date ,subject) (split-string line "\x1f")))
            (when (and commit date subject)
              (push `((repository . ,label) (directory . ,directory) (commit . ,commit)
                      (date . ,date) (title . ,subject)
                      (files . ,(split-string (starintel-social--git-string
                                                directory "diff-tree" "--no-commit-id" "--name-only" "-r" commit) "\n" t)))
                    result))))))
    (sort result (lambda (left right) (string> (alist-get 'date left) (alist-get 'date right))))))

(defun starintel-social--finding-items ()
  (let ((root (getenv "STARINTEL_AUTO_DIG_DIR")))
    (unless (and root (file-directory-p root))
      (user-error "Set STARINTEL_AUTO_DIG_DIR to search canonical Auto Dig records"))
    (starintel-social--call-python-json "starintel_auto_findings.cli" root "--limit" "500")))

(define-derived-mode starintel-social-discovery-mode tabulated-list-mode "StarIntel Discovery"
  "Read-only, keyboard-first StarIntel discovery list."
  (setq tabulated-list-padding 2)
  (setq tabulated-list-sort-key nil)
  (tabulated-list-init-header))

(defun starintel-social--show-discovery (title kind columns items entries)
  (with-current-buffer (get-buffer-create title)
    (starintel-social-discovery-mode)
    (setq-local starintel-social--discovery-kind kind)
    (setq-local starintel-social--discovery-items items)
    (setq tabulated-list-format columns)
    (setq tabulated-list-entries entries)
    (tabulated-list-init-header)
    (tabulated-list-print t)
    (use-local-map (copy-keymap tabulated-list-mode-map))
    (local-set-key (kbd "RET") #'starintel-social-discovery-inspect)
    (local-set-key (kbd "t") #'starintel-social-discovery-topic)
    (local-set-key (kbd "g") #'revert-buffer)
    (display-buffer (current-buffer))))

(defun starintel-social-features (&optional since)
  "Browse recent local StarIntel feature evidence.
SINCE uses Git's date syntax and defaults to the last fourteen days."
  (interactive (list (read-string "Changes since: " "14 days ago")))
  (let ((items (starintel-social--feature-items since)))
    (starintel-social--show-discovery
     "*StarIntel Features*" 'feature
     [("Date" 20 t) ("Repository" 30 t) ("Change" 0 t)] items
     (mapcar (lambda (item)
               (list item (vector (substring (alist-get 'date item) 0 10)
                                  (alist-get 'repository item) (alist-get 'title item)))) items))))

(defun starintel-social-findings ()
  "Browse source-preserving candidate material from canonical Auto Dig records."
  (interactive)
  (let ((items (starintel-social--finding-items)))
    (starintel-social--show-discovery
     "*StarIntel Findings*" 'finding
     [("Dataset" 24 t) ("Type" 16 t) ("Sources" 8 t) ("Candidate" 0 t)] items
     (mapcar (lambda (item)
               (list item (vector (or (alist-get 'dataset item) "")
                                  (alist-get 'dtype item)
                                  (number-to-string (alist-get 'source_count item))
                                  (alist-get 'title item)))) items))))

(defun starintel-social-discovery--item ()
  (or (tabulated-list-get-id) (user-error "No discovery item at point")))

(defun starintel-social-discovery-inspect ()
  "Show exact source references for the item at point."
  (interactive)
  (let ((item (starintel-social-discovery--item)))
    (with-current-buffer (get-buffer-create "*StarIntel Evidence*")
      (let ((inhibit-read-only t))
        (erase-buffer)
        (pcase starintel-social--discovery-kind
          ('feature
           (insert (format "Repository: %s\nCommit: %s\nDate: %s\n\n%s\n\nChanged files:\n%s\n"
                           (alist-get 'repository item) (alist-get 'commit item) (alist-get 'date item)
                           (alist-get 'title item) (string-join (alist-get 'files item) "\n"))))
          ('finding
           (insert (format "Document: %s\nDataset: %s\nType: %s\nSource record: %s\n\n%s\n\nSources:\n%s\n"
                           (alist-get 'document_id item) (or (alist-get 'dataset item) "") (alist-get 'dtype item)
                           (alist-get 'source_path item) (alist-get 'summary item)
                           (string-join (alist-get 'source_locators item) "\n")))))
        (special-mode))
      (display-buffer (current-buffer)))))

(defun starintel-social--topic-path (slug)
  (starintel-social--path "editorial" "topics" (concat slug ".org")))

(defun starintel-social--topic-reference (kind item)
  (pcase kind
    ('feature (format "- commit :: %s@%s\n- files :: %s"
                      (alist-get 'repository item) (alist-get 'commit item)
                      (string-join (alist-get 'files item) ", ")))
    ('finding (format "- document :: %s\n- record :: %s\n- sources :: %s"
                      (alist-get 'document_id item) (alist-get 'source_path item)
                      (string-join (alist-get 'source_locators item) ", ")))))

(defun starintel-social-discovery-topic (title)
  "Create an Org editorial topic from the selected evidence item."
  (interactive (list (read-string "Topic title: " (alist-get 'title (starintel-social-discovery--item)))))
  (let* ((item (starintel-social-discovery--item))
         (kind starintel-social--discovery-kind)
         (slug (starintel-social--slugify title))
         (path (starintel-social--topic-path slug)))
    (when (file-exists-p path) (user-error "Topic already exists: %s" path))
    (make-directory (file-name-directory path) t)
    (write-region
     (format "#+title: %s\n#+slug: %s\n#+topic_type: %s\n#+status: SELECTED\n#+date: %s\n\n* Source material\n%s\n\n* Editorial angle\n\n* Confirmed facts\n\n* Analysis and inference\n\n* Open questions\n"
             title slug kind (format-time-string "%Y-%m-%d") (starintel-social--topic-reference kind item))
     nil path)
    (find-file path)))

(defun starintel-social-topic-production (topic)
  "Create reviewable blog, script, presentation, and demo Org sources for TOPIC.
The topic remains the source index; no claim is copied in as a new fact."
  (interactive (list (read-file-name "Topic Org: " (starintel-social--path "editorial" "topics") nil t)))
  (with-current-buffer (find-file-noselect topic)
    (let* ((title (or (starintel-social--keyword "TITLE") (file-name-base topic)))
           (slug (or (starintel-social--keyword "SLUG") (file-name-base topic)))
           (kind (or (starintel-social--keyword "TOPIC_TYPE") "feature"))
           (video-dir (starintel-social--path "youtube" "video-source" slug))
           (blog (starintel-social--path "blog" "drafts" (concat slug ".org"))))
      (make-directory (file-name-concat video-dir "assets" "images") t)
      (make-directory (file-name-directory blog) t)
      (unless (file-exists-p blog)
        (write-region (format "#+title: %s\n#+status: DRAFT\n#+slug: %s\n#+topic: [[file:%s][%s]]\n\n%s"
                              title slug topic title
                              (if (string= kind "finding")
                                  "* What I found\n\n* Why I looked\n\n* What the records show\n\n* What I think it means\n\n* What is confirmed\n\n* What is still speculative\n\n* Sources\n\n* Next questions\n"
                                "* What changed\n\n* What it replaces\n\n* Why I changed it\n\n* How it works\n\n* Demo\n\n* Technical details\n\n* What comes next\n\n* References\n")) nil blog))
      (dolist (spec `(("script.org" . ,(if (string= kind "finding")
                                             "* Cold open\n\n* Setup\n\n* Records\n\n* Analysis\n\n* Uncertainty\n\n* Closing\n"
                                           "* Cold open\n\n* Setup\n\n* What changed\n\n* Walkthrough\n\n* Demo\n\n* Technical details\n\n* Closing\n"))
                      ("present.org" . "* Question / problem\n\n* Evidence\n\n* Walkthrough\n\n* Demo\n\n* What is next\n")
                      ("demo.org" . "* Objective\n\n* Required repositories and services\n\n* Commands\n\n* Expected output\n\n* Screens to capture\n\n* Fallback steps\n\n* Cleanup\n\n* Verification\n- [ ] MANUAL — commands must be taken from current repository documentation and run before recording.\n")))
        (let ((path (file-name-concat video-dir (car spec))))
          (unless (file-exists-p path)
            (write-region (format "#+title: %s — %s\n#+slug: %s\n#+topic: [[file:%s][%s]]\n#+status: DRAFT\n\n%s"
                                  title (file-name-base (car spec)) slug topic title (cdr spec)) nil path))))
      (find-file blog))))

(provide 'starintel-social-discovery)
;;; starintel-social-discovery.el ends here
