<!-- last_verified: 2026-03-10 -->
# App Workflows

User journeys inside the application.

## Run a Batch Detection (primary)

- User uploads source images/videos (or already has media on a B2 prefix)
- Navigates to `/runs` and opens **New Run**
- Picks a source prefix (defaults to `…/source/`), task (detect/segment), and a min-confidence
- Submits → `POST /runs` registers the run and starts the async pipeline; the UI routes to the detail page
- Detail page polls live status while the run progresses (LISTING → DETECTING → ANNOTATING → CROPPING → READY)
- On READY the annotated frames + crops + COCO dataset are on B2
- See: [Batch Detection Runs](features/batch-detection.md)

## Browse Results & Export

- On `/runs/[id]`, the user drags the **confidence slider** to re-filter the stored detections client-side (no re-run)
- The annotated-frame gallery and per-class crop gallery update with the threshold
- **Export COCO** opens the presigned `instances.json` dataset for download
- **Delete** removes only this run's prefix on B2
- See: [Runs Library](features/runs-library.md)

## Upload Source Media

- User navigates to `/upload`
- Drops or selects images/short videos in the dropzone
- Client validates file size (max 200MB) and type (image/video)
- Progress bar shows per-file upload status; files land under `…/source/`
- On success: toast + green checkmark; on failure: red status with the reason
- See: [File Upload](features/file-upload.md)

## Browse and Manage Files (full bucket)

- User navigates to `/files`
- Page loads the file list (sorted most recent first) as a tree view
- Hover a file row to preview / download / delete
- **Preview**: opens a dialog with image/video preview + metadata panel
- **Download**: presigned URL, browser downloads the file
- **Delete**: removes the object from B2
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- `GET /runs/stats` loads pipeline aggregates (polls every 4s while a run is active)
- Stat cards: runs, images processed, detections, distinct classes
- Footprint card: source-vs-derived B2 multiplier + total crops generated
- Recent-runs table: latest runs with a live status badge
- See: [Dashboard](features/dashboard.md)
