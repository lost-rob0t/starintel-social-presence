;;; export-smoke.el --- Batch smoke test -*- lexical-binding: t; -*-

(let* ((root (or (getenv "STARINTEL_SOCIAL_ROOT")
                 (expand-file-name ".." (file-name-directory (or load-file-name buffer-file-name)))))
       (elisp (expand-file-name "elisp" root)))
  (add-to-list 'load-path elisp)
  (setenv "STARINTEL_SOCIAL_ROOT" root)
  (require 'starintel-social)
  (with-temp-buffer
    (org-mode)
    (insert "#+title: Export smoke\n#+slug: export-smoke\n\n* Working\n\n#+begin_src lisp\n(+ 1 1)\n#+end_src\n")
    (let ((output (starintel-social-export-current)))
      (unless (and (file-exists-p output)
                   (with-temp-buffer
                     (insert-file-contents output)
                     (and (search-forward "--gold:" nil t)
                          (search-forward "Export smoke" nil t))))
        (error "black/gold Org export smoke test failed")))))
