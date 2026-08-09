;;; starintel-social-dslide.el --- Dslide commands for StarIntel video sources -*- lexical-binding: t; -*-

(require 'org)

(defun starintel-social-dslide--require ()
  "Load Dslide or explain how to make this Org source presentable."
  (unless (require 'dslide nil t)
    (user-error "Dslide is not installed; install the dslide package, then retry")))

(defun starintel-social-dslide--current-presentation ()
  "Return the canonical presentation path for the current Org source."
  (unless (derived-mode-p 'org-mode)
    (user-error "Run this from an Org source document"))
  (let* ((slug (starintel-social--slug))
         (directory (starintel-social--path "youtube" "video-source" slug))
         (presentation (file-name-concat directory "present.org")))
    (make-directory directory t)
    (unless (file-exists-p presentation)
      (write-region
       (format "#+title: %s — presentation\n#+slug: %s\n#+options: toc:nil num:nil\n\n* Opening\n"
               (or (starintel-social--keyword "TITLE") slug) slug)
       nil presentation))
    presentation))

(defun starintel-social-dslide-open-current ()
  "Open the canonical Dslide source for the current Org document."
  (interactive)
  (find-file (starintel-social-dslide--current-presentation)))

(defun starintel-social-dslide-start ()
  "Start the current Org source as a Dslide deck."
  (interactive)
  (unless (derived-mode-p 'org-mode)
    (user-error "Run this from an Org presentation source"))
  (starintel-social-dslide--require)
  (dslide-deck-start))

(defun starintel-social-dslide-develop ()
  "Start the current Org source in Dslide's source-and-slides layout."
  (interactive)
  (unless (derived-mode-p 'org-mode)
    (user-error "Run this from an Org presentation source"))
  (starintel-social-dslide--require)
  (dslide-deck-develop))

(defun starintel-social-dslide-present ()
  "Present the current Org source through Dslide in a dedicated frame."
  (interactive)
  (unless (derived-mode-p 'org-mode)
    (user-error "Run this from an Org presentation source"))
  (starintel-social-dslide--require)
  (dslide-deck-present))

(provide 'starintel-social-dslide)
;;; starintel-social-dslide.el ends here
