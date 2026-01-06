# Step 3 (Workflow helpers + minimal UI)

Adds API endpoints:
- GET /workflow/states
- GET /content/{id}/allowed

Adds minimal Next.js pages:
- /content/new
- /content/[id]

## Note on CORS
The pages call `http://127.0.0.1:8000` directly.
If CORS blocks it in your environment, we'll add a Step 3.1 pack to enable CORS for local dev.
