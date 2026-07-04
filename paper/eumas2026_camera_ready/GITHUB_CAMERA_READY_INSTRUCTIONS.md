# What to do on GitHub before/around camera-ready submission

Repository: https://github.com/und3f1n3d5/EmBoRA

Recommended steps:

1. Update the repository with the final camera-ready article materials:
   - `eumas2026_article_camera_ready.tex`
   - `eumas2026_references_camera_ready.bib`
   - final PDF
   - figures used in the paper
   - scripts/configs/results needed to reproduce the reported tables and figures.

2. Commit the final artifact state and record the commit hash:
   ```bash
   git status
   git add .
   git commit -m "Camera-ready artifacts for EUMAS 2026"
   git rev-parse HEAD
   git push
   ```

3. Create a stable tag/release, for example:
   ```bash
   git tag -a eumas2026-camera-ready -m "EUMAS 2026 camera-ready artifact"
   git push origin eumas2026-camera-ready
   ```

4. In the GitHub release page, attach this archive and the final PDF. If you use Zenodo, connect the repository and mint a DOI for the release. A DOI is useful but was not required in the acceptance email.

5. If the final commit hash differs from the hash mentioned in the paper manifests, do not change experimental claims in the article. The paper currently cites the run-manifest snapshot for experiment reproducibility; the GitHub release is the publication-level bundle.
