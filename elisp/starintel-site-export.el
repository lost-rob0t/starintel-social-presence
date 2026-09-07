;;; starintel-site-export.el --- Batch Org->HTML fragments for the site builder -*- lexical-binding: t; -*-

;; The site builder (Python) owns page shells, navigation, badges, and layout.
;; This backend exports the article body only: table of contents plus content,
;; without any <html>/<head>/<body> wrapper or <h1 class="title"> (the site
;; builder renders the title and metadata from Org keywords itself).

(require 'org)
(require 'ox-html)
(require 'org-id)
(require 'json)

(defun starintel-site-export--template (contents _info)
  "Return CONTENTS unchanged: the inner template already emits the
TOC, article body, and footnotes; this only strips the HTML shell."
  contents)

(org-export-define-derived-backend 'starintel-site-html 'html
  :translate-alist '((template . starintel-site-export--template)))

(defun starintel-site-export--options ()
  '(:with-toc 3
    :section-numbers nil
    :with-title nil
    :with-author nil
    :with-date nil
    :with-email nil
    :html-validation-link nil
    :html-postamble nil
    :html-preamble nil
    :html-html5-fancy t
    :html-doctype "html5"
    :html-prefer-user-labels t))

(defun starintel-site-export-file (org-file output-file)
  "Export ORG-FILE as a body fragment to OUTPUT-FILE. Return OUTPUT-FILE."
  (let* ((org-file (expand-file-name org-file))
         (output-file (expand-file-name output-file))
         (default-directory (file-name-directory org-file))
         (coding-system-for-write 'utf-8))
    (with-current-buffer (find-file-noselect org-file)
      (let ((inhibit-message t))
        (org-export-to-file 'starintel-site-html output-file
                            nil nil nil nil
                            (starintel-site-export--options))))
    output-file))

(defun starintel-site-export-manifest (manifest-file)
  "Export each {src,out} pair in the JSON MANIFEST-FILE.
Org-roam style [[id:...]] links resolve through org-id across all
manifest sources. The org-id locations cache stays in a temporary
file so batch runs never depend on (or pollute) a user profile."
  (let* ((json-array-type 'list)
         (org-id-locations-file (make-temp-file "starintel-org-id-locations"))
         (entries (json-read-file manifest-file))
         (srcs (mapcar (lambda (e) (expand-file-name (alist-get 'src e))) entries)))
    (org-id-update-id-locations srcs t)
    (dolist (entry entries)
      (starintel-site-export-file (alist-get 'src entry) (alist-get 'out entry))
      (message "exported %s" (alist-get 'out entry)))
    (length entries)))

(provide 'starintel-site-export)
;;; starintel-site-export.el ends here
