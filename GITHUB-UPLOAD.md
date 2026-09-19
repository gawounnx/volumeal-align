# VoluMeal Align GitHub upload

This package excludes local secrets, logs, caches, training images, and unused training checkpoints.

## Upload with Git LFS

1. Install GitHub Desktop and Git LFS.
2. In GitHub Desktop, clone `gawounnx/volumeal-align`.
3. Extract this package and copy all files, including `.gitattributes` and `.gitignore`, into the cloned folder.
4. Open Terminal in the repository folder and run:

   ```bash
   git lfs install
   git lfs track "backend/weights/*.onnx"
   git lfs track "backend/weights/**/best.onnx"
   git add .
   git commit -m "Add VoluMeal Align application"
   git push origin main
   ```

5. Do not add `backend/.env`. Configure secrets in Render only.

## Render

Create a Blueprint from the repository root. `render.yaml` creates the backend, frontend, and PostgreSQL database.

Required manual environment variables for `volumeal-backend`:

- `OPENAI_API_KEY` after the OpenAI recognition adapter is implemented.

## Source upload status — 2026-09-16

The initial source upload excludes ONNX weights and the local upload archive. The weights remain in the local workspace and require a separate Git LFS upload; no placeholder model files are committed. Image analysis is unavailable until the model artifacts are provisioned and validated.

OpenAI integration is not implemented. The Blueprint asks for `OPENAI_API_KEY` to store it in the backend environment only; saving the key does not enable OpenAI requests.

Use Render New > Blueprint and select this repository to create the backend, frontend, and database together. Review the service plans and displayed charges before deploying. Confirm the actual backend URL matches the frontend `API_BACKEND_URL` and rebuild the frontend if it differs.
