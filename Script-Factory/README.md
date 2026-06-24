# Script‑Factory

**Script‑Factory** is a backend service designed to generate, store, and manage custom scripts on‑demand. It provides a RESTful API that allows clients to:

- Define script parameters and templates.
- Generate scripts dynamically based on user input.
- Store generated scripts in a version‑controlled repository.
- Retrieve, update, or delete scripts securely.

The service is built with modularity and extensibility in mind, making it easy to add new scripting languages, integrate with CI/CD pipelines, and enforce organizational policies.

## Key Features

- **Dynamic Script Generation** – Create scripts from templates using provided variables.
- **Version Control** – All scripts are committed to a Git repository for history tracking.
- **Secure Execution** – Scripts can be sandboxed or executed on demand with strict permission controls.
- **Extensible Architecture** – Plug‑in support for additional languages and execution environments.

## Getting Started

1. Clone the repository.
2. Install dependencies (`pip install -r requirements.txt` or similar).
3. Run the service (`uvicorn main:app --reload`).
4. Use the API endpoints documented in the Swagger UI (`/docs`).

For detailed usage instructions, refer to the project's documentation.
