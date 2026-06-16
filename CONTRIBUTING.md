# Contributing to GEE-LLM

Thank you for your interest in contributing! This document explains how to report issues, suggest features, and submit pull requests.

---

## 🐛 Reporting Bugs

1. Search [existing issues](https://github.com/AmanSharma000/gee-llm/issues) first.
2. Open a new issue using the **Bug Report** template.
3. Include: OS, Python version, full traceback, and minimal reproduction steps.

---

## 💡 Suggesting Features

Open an issue with the **Feature Request** label. Describe the use case and expected behaviour.

---

## 🔧 Pull Requests

### Setup
```bash
git clone https://github.com/AmanSharma000/gee-llm.git
cd gee-llm
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Workflow
1. Fork the repository.
2. Create a branch: `git checkout -b feature/your-feature-name`
3. Make your changes following the code style below.
4. Run tests: `python -m pytest tests/ -v`
5. Commit with a descriptive message.
6. Open a Pull Request against `main`.

---

## 📝 Code Style

- Follow [PEP 8](https://pep8.org/).
- Use descriptive variable names.
- Add docstrings to all public functions.
- Keep functions focused — one responsibility per function.

---

## ➕ Adding a New GEE Snippet Template

GEE template scripts live in `backend/rag/snippets/`. To add a new one:

1. Create `backend/rag/snippets/your_snippet_name.py`.
2. The script must:
   - Import `ee` and initialize via `ee.Initialize()`.
   - Use the `India_sorted` boundary asset for regional filtering.
   - Store the final result in a variable named `result` (a JSON-serializable dict).
3. Add a corresponding entry to `backend/rag/examples.jsonl` with the fields `query`, `code_file`, and `index`.
4. Test the snippet manually against the live GEE backend before submitting.

---

## 📜 License

By submitting a contribution you agree that it will be licensed under the project's [MIT License](LICENSE).
