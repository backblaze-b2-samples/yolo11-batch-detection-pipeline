<!-- last_verified: 2026-04-22 -->
# Security

Security principles and implementation for the yolo11-batch-detection-pipeline.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4
- **Client -> B2**: Presigned URLs — inline previews for run artifacts (annotated
  frames, crops) and the `/files` browser; the file download path and the COCO
  export force `Content-Disposition: attachment`. All presigned URLs are
  short-lived (≤ 60 min).

## Upload Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against the image/video allowlist
- Chunked streaming with size enforcement (200MB default)
- Content-type allowlist (jpeg, png, webp, bmp, mp4, mov only)
- Empty file rejection

## Run & File Key Validation

- Run ids validated against a strict hex pattern (`^[a-f0-9]{32}$`)
- Run **source prefixes** are normalized and rejected if they contain `..`
- File-browser keys: empty keys rejected; traversal patterns rejected
  (`../`, `%2e%2e`, backslashes, null bytes)
- **Scoped deletes**: deleting a run removes only `…/runs/{id}/` — never the
  source corpus, other runs, or other apps' prefixes
- The bucket is the only access boundary — every write/list/delete this app
  performs is scoped under `settings.run_prefix`

## Download Safety

- The `/files` download path and the COCO export force
  `Content-Disposition: attachment` (XSS mitigation for downloaded content)
- Inline previews (annotated frames, crops, image/video preview) are served by
  presigned GET without attachment disposition so the browser can render them;
  these are app-generated or user-uploaded media rendered in an isolated `<img>`/
  `<video>`, not executed

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Dependency Security

- Frontend transitive dependency security pins are centralized in the root
  `pnpm.overrides` block so patched versions are enforced consistently across
  workspace packages.

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
