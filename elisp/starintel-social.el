;;; starintel-social.el --- Emacs-first StarIntel editorial desk -*- lexical-binding: t; -*-

(require 'dired)
(require 'json)
(require 'org)
(require 'seq)
(require 'ox-html)
(require 'subr-x)

(defgroup starintel-social nil
  "StarIntel editorial workstation."
  :group 'applications)

(defconst starintel-social--package-root
  (file-name-directory
   (directory-file-name
    (file-name-directory (or load-file-name buffer-file-name default-directory)))))

(defcustom starintel-social-root
  (let ((configured (getenv "STARINTEL_SOCIAL_ROOT")))
    (if (and configured (not (string-empty-p configured)))
        (expand-file-name configured)
      starintel-social--package-root))
  "Repository root for starintel-social-presence."
  :type 'directory)

(defcustom starintel-social-author user-full-name
  "Default author inserted into new Org posts."
  :type 'string)

(defconst starintel-social-html-style
  "<style>
:root{color-scheme:dark;--bg:#090909;--panel:#111;--text:#eee;--muted:#aaa;--gold:#d6ad36;--gold2:#f5cf58;--line:#2b2515}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:18px/1.7 ui-sans-serif,system-ui,sans-serif}
#content{max-width:900px;margin:0 auto;padding:4rem 1.5rem 7rem}h1,h2,h3,h4{line-height:1.2;color:#fff}h1{font-size:clamp(2.4rem,7vw,4.8rem);letter-spacing:-.04em;border-bottom:1px solid var(--line);padding-bottom:1rem}h2{margin-top:3.5rem;color:var(--gold2)}a{color:var(--gold2)}code,pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}pre{overflow:auto;padding:1rem 1.2rem;background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--gold);border-radius:.35rem}code{color:#ffe8a3}table{width:100%;border-collapse:collapse;display:block;overflow-x:auto}th,td{border:1px solid #332d1d;padding:.55rem .7rem;text-align:left}th{color:var(--gold2);background:#15130e}blockquote{margin:2rem 0;padding:.2rem 1.2rem;border-left:3px solid var(--gold);color:#ddd;background:#0e0e0e}.figure img{max-width:100%;height:auto}.org-src-container{margin:1.5rem 0}#table-of-contents{background:#0e0e0e;border:1px solid var(--line);padding:1rem 1.4rem;border-radius:.35rem}.timestamp{color:var(--muted)}
@media(max-width:640px){body{font-size:16px}#content{padding:2rem 1rem 4rem}h1{font-size:2.5rem}}
</style>")

(defun starintel-social--html-template (contents info)
  (let ((info (copy-sequence info)))
    (setq info (plist-put info :html-head
                          (concat starintel-social-html-style
                                  (or (plist-get info :html-head) ""))))
    (org-html-template contents info)))

(org-export-define-derived-backend 'starintel-html 'html
  :translate-alist '((template . starintel-social--html-template)))

(defun starintel-social--path (&rest pieces)
  (seq-reduce #'file-name-concat pieces (file-name-as-directory starintel-social-root)))

(defun starintel-social-open-workspace ()
  "Open the social-presence repository in Dired."
  (interactive)
  (dired starintel-social-root))

(defun starintel-social-list-blog ()
  "Open the blog directory."
  (interactive)
  (dired (starintel-social--path "blog")))

(defun starintel-social--slugify (text)
  (let ((slug (downcase (string-trim text))))
    (setq slug (replace-regexp-in-string "[^[:alnum:]]+" "-" slug))
    (string-trim slug "-+" "-+")))

(defun starintel-social-new-post (title)
  "Create a new human-editable Org draft named from TITLE."
  (interactive "sPost title: ")
  (let* ((slug (starintel-social--slugify title))
         (path (starintel-social--path "blog" "drafts" (concat slug ".org"))))
    (when (file-exists-p path)
      (user-error "Draft already exists: %s" path))
    (make-directory (file-name-directory path) t)
    (find-file path)
    (insert (format "#+title: %s\n#+date: %s\n#+author: %s\n#+description: \n#+slug: %s\n#+tags: \n\n* Draft\n"
                    title (format-time-string "%Y-%m-%d") starintel-social-author slug))
    (save-buffer)))

(defun starintel-social--keyword (keyword)
  "Return the first value of Org KEYWORD in the current buffer."
  (let ((entry (assoc-string (upcase keyword)
                             (org-collect-keywords (list (upcase keyword)))
                             t)))
    (car (cdr entry))))

(defun starintel-social--slug ()
  (or (starintel-social--keyword "SLUG")
      (and buffer-file-name (file-name-base buffer-file-name))
      (user-error "Cannot determine document slug")))

(defun starintel-social-open-video-source ()
  "Open script.org associated with the current Org document slug."
  (interactive)
  (unless (derived-mode-p 'org-mode)
    (user-error "Run this from an Org source document"))
  (let* ((slug (starintel-social--slug))
         (dir (starintel-social--path "youtube" "video-source" slug))
         (script (file-name-concat dir "script.org"))
         (present (file-name-concat dir "present.org")))
    (make-directory (file-name-concat dir "assets" "images") t)
    (unless (file-exists-p script)
      (write-region (format "#+title: %s — script\n#+slug: %s\n\n* Notes\n" (or (starintel-social--keyword "TITLE") slug) slug) nil script))
    (unless (file-exists-p present)
      (write-region (format "#+title: %s — presentation\n#+slug: %s\n\n* Opening\n" (or (starintel-social--keyword "TITLE") slug) slug) nil present))
    (find-file script)))

(defun starintel-social-export-current (&optional open)
  "Export current Org buffer with the StarIntel black/gold backend.
With prefix argument OPEN, open the resulting HTML in a browser."
  (interactive "P")
  (unless (derived-mode-p 'org-mode)
    (user-error "Current buffer is not Org"))
  (let* ((slug (starintel-social--slug))
         (out-dir (starintel-social--path "local-exports"))
         (output (file-name-concat out-dir (concat slug ".html"))))
    (make-directory out-dir t)
    (org-export-to-file 'starintel-html output nil nil nil nil
                        '(:with-toc t :section-numbers nil))
    (when open (browse-url-of-file output))
    (message "Exported %s" output)
    output))

(defun starintel-social--python-path ()
  (mapconcat
   #'identity
   (mapcar (lambda (dir) (starintel-social--path dir "src"))
           '("change_fetcher" "auto_findings" "auto_research" "starintel_tutorial_gen"))
   path-separator))

(defun starintel-social--changes (repository revision-range)
  (let ((process-environment (copy-sequence process-environment))
        (buffer (generate-new-buffer " *starintel-changes*")))
    (setenv "PYTHONPATH" (starintel-social--python-path))
    (unwind-protect
        (let ((status (call-process "python3" nil buffer nil
                                    "-m" "starintel_change_fetcher.cli"
                                    (expand-file-name repository)
                                    "--range" revision-range)))
          (unless (zerop status)
            (error "change_fetcher failed: %s" (with-current-buffer buffer (buffer-string))))
          (with-current-buffer buffer
            (goto-char (point-min))
            (json-parse-buffer :object-type 'alist :array-type 'list)))
      (kill-buffer buffer))))

(defun starintel-social-fetch-changes (repository revision-range)
  "Fetch normalized Git changes from REPOSITORY over REVISION-RANGE."
  (interactive
   (list (read-directory-name "Git repository: " (or (getenv "STARINTEL_SERVER_DIR") "~/"))
         (read-string "Revision range: " "HEAD~10..HEAD")))
  (let ((changes (starintel-social--changes repository revision-range)))
    (with-current-buffer (get-buffer-create "*StarIntel Changes*")
      (let ((inhibit-read-only t))
        (erase-buffer)
        (dolist (change changes)
          (insert (format "%s  %s\n  %s\n  %s\n\n"
                          (alist-get 'commit change)
                          (alist-get 'timestamp change)
                          (alist-get 'message change)
                          (string-join (alist-get 'changed_files change) ", "))))
        (special-mode))
      (display-buffer (current-buffer)))
    changes))

(defun starintel-social-insert-change-at-point (repository revision-range)
  "Select a normalized change and insert its factual summary into current Org buffer."
  (interactive
   (list (read-directory-name "Git repository: " (or (getenv "STARINTEL_SERVER_DIR") "~/"))
         (read-string "Revision range: " "HEAD~10..HEAD")))
  (let* ((changes (starintel-social--changes repository revision-range))
         (choices (mapcar (lambda (change)
                            (cons (format "%.12s %s" (alist-get 'commit change) (alist-get 'message change)) change))
                          changes))
         (selected (cdr (assoc (completing-read "Change: " choices nil t) choices))))
    (insert (format "- Repository: =%s=\n- Commit: =%s=\n- Timestamp: %s\n- Message: %s\n- Changed files: %s\n"
                    (alist-get 'repository selected)
                    (alist-get 'commit selected)
                    (alist-get 'timestamp selected)
                    (alist-get 'message selected)
                    (string-join (alist-get 'changed_files selected) ", ")))))

(let ((module-dir (file-name-concat starintel-social-root "elisp")))
  (add-to-list 'load-path (file-name-concat module-dir "blog-gen"))
  (add-to-list 'load-path (file-name-concat module-dir "blog-deslop")))
(require 'starintel-blog-deslop)
(require 'starintel-blog-gen)
(defalias 'starintel-social-deslop #'starintel-blog-deslop)

(defun starintel-social-blog-assist-region (beg end)
  "Request a non-destructive editorial suggestion for selected region BEG..END."
  (interactive "r")
  (unless (use-region-p) (user-error "Select a region first"))
  (starintel-blog-gen-region beg end "Make this more concise while preserving factual claims, source references, and the author's technical voice."))

(if (require 'transient nil t)
    (eval
     '(transient-define-prefix starintel-social-menu ()
        "StarIntel Social"
        [["Workspace"
          ("o" "Open workspace" starintel-social-open-workspace)
          ("b" "Blog" starintel-social-list-blog)
          ("n" "New post" starintel-social-new-post)
          ("v" "Video source" starintel-social-open-video-source)]
         ["Facts"
          ("f" "Fetch changes" starintel-social-fetch-changes)
          ("i" "Insert change" starintel-social-insert-change-at-point)]
         ["Edit"
          ("d" "Deslop lint" starintel-blog-deslop)
          ("a" "Assist region" starintel-social-blog-assist-region)
          ("e" "Export HTML" starintel-social-export-current)]]))
  (defun starintel-social-menu ()
    "Fallback StarIntel command menu when transient is unavailable."
    (interactive)
    (call-interactively
     (intern
      (completing-read
       "StarIntel Social: "
       '("starintel-social-open-workspace"
         "starintel-social-list-blog"
         "starintel-social-new-post"
         "starintel-social-fetch-changes"
         "starintel-social-insert-change-at-point"
         "starintel-blog-deslop"
         "starintel-social-blog-assist-region"
         "starintel-social-export-current")
       nil t)))))

(provide 'starintel-social)
;;; starintel-social.el ends here
