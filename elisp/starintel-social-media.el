;;; starintel-social-media.el --- StarIntel media workflow and gptel tool -*- lexical-binding: t; -*-

(require 'subr-x)

(defun starintel-social-media--python-path ()
  (file-name-concat starintel-social-root "media_gen" "src"))

(defun starintel-social-media--call (&rest args)
  "Run starintel_media_gen with ARGS and return stdout."
  (let ((process-environment (copy-sequence process-environment))
        (buffer (generate-new-buffer " *starintel-media*")))
    (setenv "PYTHONPATH"
            (string-join
             (delq nil
                   (list (starintel-social-media--python-path)
                         (getenv "PYTHONPATH")))
             path-separator))
    (unwind-protect
        (let ((status (apply #'call-process "python3" nil buffer nil
                             "-m" "starintel_media_gen.cli" args)))
          (unless (zerop status)
            (error "starintel-media failed: %s"
                   (with-current-buffer buffer (buffer-string))))
          (with-current-buffer buffer
            (string-trim-right (buffer-string))))
      (kill-buffer buffer))))

(defun starintel-social-media-template-string (description &optional media-kind flow title)
  "Return a canonical Org media template for DESCRIPTION."
  (starintel-social-media--call
   "template"
   (or description "")
   "--kind" (or media-kind "both")
   "--flow" (or flow "auto")
   "--title" (or title "StarIntel media draft")))

(defun starintel-social-media-template (title description media-kind flow output)
  "Generate an Org production template from DESCRIPTION and visit OUTPUT."
  (interactive
   (list (read-string "Title: ")
         (read-string "Description: ")
         (completing-read "Media kind: " '("both" "image" "video") nil t nil nil "both")
         (completing-read "Flow: " '("auto" "comic-explainer" "show-reference-comic" "starintel-brand" "meme" "tutorial" "architecture" "image-to-video") nil t nil nil "auto")
         (read-file-name "Write Org template: "
                         (file-name-concat starintel-social-root "youtube" "video-source")
                         nil nil "media-plan.org")))
  (make-directory (file-name-directory output) t)
  (write-region (concat (starintel-social-media-template-string description media-kind flow title) "\n") nil output)
  (find-file output))

(defun starintel-social-media-route (description media-kind flow)
  "Show the expert media route for DESCRIPTION."
  (interactive
   (list (read-string "Description: ")
         (completing-read "Media kind: " '("image" "video") nil t nil nil "image")
         (completing-read "Flow: " '("auto" "comic-explainer" "show-reference-comic" "starintel-brand" "meme" "tutorial" "architecture" "image-to-video") nil t nil nil "auto")))
  (message "%s" (starintel-social-media--call "route" description "--kind" media-kind "--flow" flow)))

(defun starintel-social-media-register-gptel-tool ()
  "Register the Org media-template generator as a gptel tool."
  (interactive)
  (unless (or (featurep 'gptel) (require 'gptel nil t))
    (user-error "gptel is not installed"))
  (let ((tool
         (gptel-make-tool
          :name "starintel_media_org_template"
          :function
          (lambda (description &optional media_kind flow title)
            (starintel-social-media-template-string description media_kind flow title))
          :description
          "Generate a canonical StarIntel Org production template from a media description. The deterministic routing expert chooses image/video providers from StarIntel-vs-show references and flow rules."
          :args
          (list '(:name "description" :type string :description "What the image/video should depict and communicate")
                '(:name "media_kind" :type string :enum ["both" "image" "video"] :optional t :description "Output stages to plan")
                '(:name "flow" :type string :enum ["auto" "comic-explainer" "show-reference-comic" "starintel-brand" "meme" "tutorial" "architecture" "image-to-video"] :optional t :description "Production flow profile")
                '(:name "title" :type string :optional t :description "Org document title"))
          :category "starintel")))
    (add-to-list 'gptel-tools tool)
    tool))

(provide 'starintel-social-media)
;;; starintel-social-media.el ends here
