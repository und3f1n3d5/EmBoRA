# PowerShell guide: upload the EUMAS 2026 camera-ready package to GitHub

Repository: https://github.com/und3f1n3d5/EmBoRA
Recommended release/tag: `eumas2026-camera-ready`

This guide assumes Windows PowerShell. Run the commands one block at a time and check the output before moving on.

## 0. What should be uploaded

The camera-ready package contains:

- `eumas2026_article_camera_ready.pdf` - final PDF for submission;
- `eumas2026_article_camera_ready.tex` - LaTeX source;
- `eumas2026_references_camera_ready.bib` and `.bbl` - bibliography files;
- `figures/` - figure files, including the restored submitted architecture overview;
- `tables/` - generated tables;
- `github_materials/` - code, compact results, configs, tests, manifests and reproducibility materials;
- README / changelog / package notes.

For Springer submission, upload the archive you received from ChatGPT. For GitHub, either commit the unpacked camera-ready folder or attach the archive to a GitHub release. The safest approach is to do both: commit the folder and attach the zip to a release.

## 1. Install prerequisites

Check that Git is installed:

```powershell
git --version
```

Optional but strongly recommended: install GitHub CLI (`gh`) from https://cli.github.com/ and then check:

```powershell
gh --version
```

Login to GitHub CLI:

```powershell
gh auth login
```

Choose:

1. GitHub.com
2. HTTPS
3. Login with a web browser

## 2. Put the archive in a convenient folder

Create a working folder:

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\Desktop\EmBoRA_camera_ready"
```

Move or copy the downloaded archive there. Suppose the archive is in Downloads:

```powershell
Copy-Item "$HOME\Downloads\eumas2026_camera_ready_submission_package_corrected.zip" "$HOME\Desktop\EmBoRA_camera_ready\"
```

Go to the folder:

```powershell
cd "$HOME\Desktop\EmBoRA_camera_ready"
```

Unpack the archive:

```powershell
Expand-Archive -Force ".\eumas2026_camera_ready_submission_package_corrected.zip" ".\package"
```

Check that files are there:

```powershell
Get-ChildItem ".\package" -Recurse | Select-Object -First 20
```

## 3. Clone the repository

If you do not have the repository locally:

```powershell
git clone https://github.com/und3f1n3d5/EmBoRA.git
cd EmBoRA
```

If you already have it locally, go to the repository folder instead:

```powershell
cd "PATH_TO_YOUR_LOCAL_REPO\EmBoRA"
git pull
```

## 4. Create a clean branch

```powershell
git checkout -b camera-ready-eumas2026
```

If the branch already exists locally:

```powershell
git checkout camera-ready-eumas2026
git pull
```

## 5. Copy the camera-ready materials into the repository

Recommended location in the repository:

```powershell
New-Item -ItemType Directory -Force -Path ".\paper\eumas2026_camera_ready"
Copy-Item -Recurse -Force "$HOME\Desktop\EmBoRA_camera_ready\package\eumas_camera_ready_corrected\*" ".\paper\eumas2026_camera_ready\"
```

If the unpacked folder has a slightly different top-level name, inspect it:

```powershell
Get-ChildItem "$HOME\Desktop\EmBoRA_camera_ready\package"
```

Then adjust the path in the `Copy-Item` command accordingly.

Check the copied files:

```powershell
Get-ChildItem ".\paper\eumas2026_camera_ready" | Select-Object Name, Length
```

## 6. Check file sizes before commit

GitHub blocks individual files larger than 100 MB. Check for large files:

```powershell
Get-ChildItem ".\paper\eumas2026_camera_ready" -Recurse | Where-Object {$_.Length -gt 95MB} | Select-Object FullName, Length
```

If this command prints nothing, you are safe.

If it prints a file larger than 100 MB, do not commit that file directly. Either remove it from the folder and attach it only to the GitHub release, or set up Git LFS.

## 7. Review the changed files

```powershell
git status
```

You should see the new `paper/eumas2026_camera_ready/` folder.

Add files:

```powershell
git add paper/eumas2026_camera_ready
```

Commit:

```powershell
git commit -m "Add EUMAS 2026 camera-ready paper package"
```

Push the branch:

```powershell
git push -u origin camera-ready-eumas2026
```

## 8. Merge to main or keep a branch

For a simple public artifact, merge via GitHub Pull Request:

```powershell
gh pr create --title "Add EUMAS 2026 camera-ready paper package" --body "Adds the camera-ready LaTeX/PDF package, figures, tables, code snapshot and reproducibility materials for the accepted EUMAS 2026 paper."
```

Open the link printed by `gh`, review the PR, and click **Merge pull request**.

Then update local main:

```powershell
git checkout main
git pull
```

If you do not want a PR, you can push directly to main, but the PR route is safer.

## 9. Create a tag

After the materials are on `main`:

```powershell
git tag -a eumas2026-camera-ready -m "EUMAS 2026 camera-ready artifact package"
git push origin eumas2026-camera-ready
```

## 10. Create a GitHub release and attach the archive

From anywhere on your computer, run:

```powershell
gh release create eumas2026-camera-ready `
  "$HOME\Desktop\EmBoRA_camera_ready\eumas2026_camera_ready_submission_package_corrected.zip" `
  ".\paper\eumas2026_camera_ready\eumas2026_article_camera_ready.pdf" `
  --title "EUMAS 2026 camera-ready artifact package" `
  --notes "Camera-ready paper package for the accepted EUMAS 2026 full paper. Includes LaTeX source, PDF, figures, tables, code snapshot, compact experiment results, tests, manifests, and reproducibility notes."
```

If PowerShell complains about line breaks, use the one-line version:

```powershell
gh release create eumas2026-camera-ready "$HOME\Desktop\EmBoRA_camera_ready\eumas2026_camera_ready_submission_package_corrected.zip" ".\paper\eumas2026_camera_ready\eumas2026_article_camera_ready.pdf" --title "EUMAS 2026 camera-ready artifact package" --notes "Camera-ready paper package for the accepted EUMAS 2026 full paper. Includes LaTeX source, PDF, figures, tables, code snapshot, compact experiment results, tests, manifests, and reproducibility notes."
```

## 11. If GitHub CLI is not installed

1. Push the branch and tag using Git commands from steps 7-9.
2. Open the repository in browser.
3. Go to **Releases** -> **Draft a new release**.
4. Choose tag `eumas2026-camera-ready`.
5. Title: `EUMAS 2026 camera-ready artifact package`.
6. Attach:
   - `eumas2026_camera_ready_submission_package_corrected.zip`;
   - `eumas2026_article_camera_ready.pdf`.
7. Publish release.

## 12. Final pre-submission checklist

Before uploading to Springer:

- Open `eumas2026_article_camera_ready.pdf` and check that Figure 1 is the submitted architecture overview, not the simplified linear schematic.
- Check that the paper is 17 pages: main text ends on page 15 and references occupy pages 15-17.
- Check that the archive contains `.tex`, `.bib`, `.bbl`, `figures/`, `tables/`, and `github_materials/`.
- Confirm that the GitHub repository is public or at least accessible to reviewers/proceedings editors.
- Keep the final archive unchanged after submission. If you change anything, create a new zip, commit, tag, and release again.

