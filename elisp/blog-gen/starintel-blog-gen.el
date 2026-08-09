;;; starintel-blog-gen.el --- Optional assisted Org editing -*- lexical-binding: t; -*-

(require 'subr-x)

(defun starintel-blog-gen-available-p ()
  "Return non-nil when a supported gptel request function is available."
  (or (fboundp 'gptel-request)
      (and (require 'gptel nil t) (fboundp 'gptel-request))))

(defun starintel-blog-gen--preview (title response)
  (with-current-buffer (get-buffer-create "*StarIntel Editorial Preview*")
    (let ((inhibit-read-only t))
      (erase-buffer)
      (insert title "\n\n" (or response "No response returned."))
      (text-mode)
      (view-mode 1))
    (display-buffer (current-buffer))))

(defun starintel-blog-gen-request (instruction text)
  "Ask the configured gptel backend to apply INSTRUCTION to TEXT.
The result is shown in a preview buffer; this function never replaces source text."
  (unless (starintel-blog-gen-available-p)
    (user-error "gptel is not configured/available; ordinary editing and export still work"))
  (let ((prompt (format "%s\n\nMaterial to edit:\n\n%s" instruction text)))
    (gptel-request
     prompt
     :callback (lambda (response _info)
                 (when response
                   (starintel-blog-gen--preview "Editorial suggestion" response))))))

(defun starintel-blog-gen-region (beg end instruction)
  "Request an editorial suggestion for region BEG..END using INSTRUCTION."
  (interactive
   (list (region-beginning)
         (region-end)
         (read-string "Editorial instruction: " "Make this more concise without changing factual claims.")))
  (unless (use-region-p)
    (user-error "Select a region first"))
  (starintel-blog-gen-request instruction (buffer-substring-no-properties beg end)))

(provide 'starintel-blog-gen)
;;; starintel-blog-gen.el ends here
