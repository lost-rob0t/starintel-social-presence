;;; starintel-blog-deslop.el --- Deterministic editorial lint -*- lexical-binding: t; -*-

(require 'cl-lib)

(defgroup starintel-blog-deslop nil
  "Deterministic checks for weak generated prose."
  :group 'text)

(defconst starintel-blog-deslop-rules
  '((generic-intro . "\\b\\(in today'?s rapidly evolving\\|in the ever-changing\\|in the digital age\\)\\b")
    (meaningless-intensifier . "\\b\\(incredibly\\|remarkably\\|extremely\\|truly\\|very\\)\\b")
    (not-just . "\\bnot just\\b.+\\bbut\\b")
    (model-self-reference . "\\b\\(as an ai\\|as a language model\\|i cannot browse\\)\\b")
    (corporate-filler . "\\b\\(leverage\\|synergy\\|game[- ]changer\\|revolutionary\\|cutting-edge solution\\)\\b"))
  "Simple deterministic lint rules.  Values are Emacs regular expressions.")

(defun starintel-blog-deslop--line-number (position)
  (line-number-at-pos position t))

(defun starintel-blog-deslop-findings (beg end)
  "Return deterministic lint findings between BEG and END.
Each finding is a plist containing :rule, :line, :start, :end and :text."
  (save-excursion
    (save-restriction
      (narrow-to-region beg end)
      (let (findings)
        (dolist (rule starintel-blog-deslop-rules)
          (goto-char (point-min))
          (while (re-search-forward (cdr rule) nil t)
            (push (list :rule (car rule)
                        :line (starintel-blog-deslop--line-number (match-beginning 0))
                        :start (match-beginning 0)
                        :end (match-end 0)
                        :text (match-string-no-properties 0))
                  findings)))
        (goto-char (point-min))
        (while (search-forward "—" nil t)
          (when (>= (how-many "—" (line-beginning-position) (line-end-position)) 2)
            (push (list :rule 'excessive-em-dash
                        :line (starintel-blog-deslop--line-number (point))
                        :start (1- (point))
                        :end (point)
                        :text "multiple em dashes on one line")
                  findings)))
        (nreverse findings)))))

(defun starintel-blog-deslop--render (findings)
  (with-current-buffer (get-buffer-create "*StarIntel Deslop*")
    (let ((inhibit-read-only t))
      (erase-buffer)
      (insert (format "StarIntel editorial lint: %d finding(s)\n\n" (length findings)))
      (dolist (finding findings)
        (insert (format "L%-5d %-24s %s\n"
                        (plist-get finding :line)
                        (plist-get finding :rule)
                        (plist-get finding :text))))
      (special-mode))
    (display-buffer (current-buffer))))

(defun starintel-blog-deslop (beg end)
  "Lint region BEG..END, or the full buffer when no region is active."
  (interactive (if (use-region-p)
                   (list (region-beginning) (region-end))
                 (list (point-min) (point-max))))
  (let ((findings (starintel-blog-deslop-findings beg end)))
    (starintel-blog-deslop--render findings)
    findings))

(provide 'starintel-blog-deslop)
;;; starintel-blog-deslop.el ends here
