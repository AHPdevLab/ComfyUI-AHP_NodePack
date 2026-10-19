# Changelog

All notable changes to comfyuiAHP_nodepack are recorded here.
Versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-19

First release.

### Added

- **AHP Folder Picker**: a Browse Folder button opens the system folder
  chooser. The output is a folder path with no quotation marks.
- **AHP Load Image**: loads an image from a path. Outputs the image, its
  mask, the full path and the directory. Has Browse Image and Preview Image
  buttons. The preview is a plain RGB image, with transparency shown on white.
- **AHP Markdown Note**: a Markdown note with a live preview. Supports
  tables, task lists, footnotes, definition lists, math (LaTeX shown as
  MathML) and right-to-left languages.
- **AHP Image Crop Fit Canvas**: centres a cut-out product on a padded
  canvas. Five scaling modes, including smart fit for very wide, low objects.
  Outputs an image and a mask.

### Notes

- The pack loader skips a node that fails to import, so one broken node does
  not stop the others.
- The Markdown note needs the libraries in `requirements.txt`. Without them
  the node still appears, and it reports what to install.
- The image crop logic is adapted from a script by Ali Haghighat Panah. See
  the file header and the README.
