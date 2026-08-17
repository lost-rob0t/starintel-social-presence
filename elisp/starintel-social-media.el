;;; starintel-social-media.el --- Prolog-RLM media workflow -*- lexical-binding: t; -*-

(require 'comint)
(require 'subr-x)

(defun starintel-social-media--cli-path ()
  "Return the Prolog media-gen CLI path."
  (file-name-concat starintel-social-root "bin" "media-gen.pl"))

(defun starintel-social-media--call (&rest args)
  "Run the Prolog media-gen CLI with ARGS and return stdout."
  (let ((buffer (generate-new-buffer " *media-gen*")))
    (unwind-protect
        (let ((status (apply #'call-process
                             "swipl" nil buffer nil
                             "-q" "-s" (starintel-social-media--cli-path)
                             "--" args)))
          (unless (zerop status)
            (error "media-gen failed: %s"
                   (with-current-buffer buffer (buffer-string))))
          (with-current-buffer buffer
            (string-trim-right (buffer-string))))
      (kill-buffer buffer))))

(defun starintel-social-media-template-string (description &optional media-kind flow title)
  "Return a canonical Org media template for DESCRIPTION using Prolog."
  (starintel-social-media--call
   "template"
   (or title "StarIntel media draft")
   (or media-kind "both")
   (or flow "auto")
   (or description "")))

(defun starintel-social-media-template (title description media-kind flow output)
  "Generate a Prolog media production template and visit OUTPUT."
  (interactive
   (list (read-string "Title: ")
         (read-string "Description: ")
         (completing-read "Media kind: " '("both" "image" "video") nil t nil nil "both")
         (completing-read "Flow: " '("auto" "comic-explainer" "show-reference-comic" "starintel-brand" "meme" "tutorial" "architecture" "image-to-video") nil t nil nil "auto")
         (read-file-name "Write Org template: "
                         (file-name-concat starintel-social-root "youtube" "video-source")
                         nil nil "media-plan.org")))
  (make-directory (file-name-directory output) t)
  (write-region (concat (starintel-social-media-template-string
                         description media-kind flow title)
                        "\n")
                nil output)
  (find-file output))

(defun starintel-social-media-route (description media-kind flow)
  "Show the Prolog expert route for DESCRIPTION."
  (interactive
   (list (read-string "Description: ")
         (completing-read "Media kind: " '("image" "video") nil t nil nil "image")
         (completing-read "Flow: " '("auto" "comic-explainer" "show-reference-comic" "starintel-brand" "meme" "tutorial" "architecture" "image-to-video") nil t nil nil "auto")))
  (message "%s"
           (starintel-social-media--call
            "route" media-kind flow description)))

(defun media-gen-expert-shell ()
  "Open the persistent Prolog media-gen expert shell."
  (interactive)
  (let* ((buffer-name "*media-gen expert*")
         (buffer (get-buffer buffer-name)))
    (unless (and buffer (comint-check-proc buffer))
      (setq buffer
            (make-comint-in-buffer
             "media-gen expert"
             buffer-name
             "swipl"
             nil
             "-q" "-s" (starintel-social-media--cli-path)
             "--" "shell"))
      (with-current-buffer buffer
        (setq-local comint-prompt-regexp "^media-gen?> ")
        (setq-local comint-use-prompt-regexp t)))
    (pop-to-buffer buffer)))

(defalias 'starintel-social-media-expert-shell #'media-gen-expert-shell)

(defun starintel-social-media-register-gptel-tool ()
  "Register the Prolog media-template generator as a gptel tool."
  (interactive)
  (unless (or (featurep 'gptel) (require 'gptel nil t))
    (user-error "gptel is not installed"))
  (let ((tool
         (gptel-make-tool
          :name "starintel_media_org_template"
          :function
          (lambda (description &optional media_kind flow title)
            (starintel-social-media-template-string
             description media_kind flow title))
          :description
          "Generate a canonical media-gen Org production template through the Prolog-RLM application."
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
