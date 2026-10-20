# Security

This project is a local Obsidian vault template plus standard-library Python CLI tools. It does not make network requests.

If you find a security issue, especially path traversal or unintended file deletion in `tools/kb_clean_demo.py`, please use GitHub's private security advisory instead of opening a public issue.

Never commit personal notes, credentials, `.env` files, or `.workbuddy/` backups. The provided `.gitignore` covers the common cases, but review `git status` before publishing.
