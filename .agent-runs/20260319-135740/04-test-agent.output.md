Updated [tests/test_password_reset.py](/Users/mito/WorkSpace/Python_Project/tests/test_password_reset.py).

Coverage now includes:
- `GET /reset-password?token=...` renders the reset form with the new `confirm_password` input when the token is valid.
- `POST /reset-password` rejects mismatched `password` and `confirm_password`, rerenders the form with the validation error, and does not call the reset service.
- `POST /reset-password` with matching passwords still redirects to `/login?reset=success`, invokes the reset service, and clears the session cookie.
- Existing unit coverage remains for reset token creation, successful password reset, token invalidation, and old access-token invalidation.

Still not covered:
- Browser-level template assertions beyond the presence of the confirmation field.
- FastAPI’s framework-level `422` behavior for a missing `confirm_password` form field.
- End-to-end persistence behavior with a real DB for the reset flow.

Verification commands:
```bash
pytest -q
ruff check .
```

What I could run in this environment:
```bash
.venv/bin/python -m unittest -q tests.test_password_reset
```

Result:
- `unittest` passed: `Ran 7 tests in 0.021s`
- `pytest -q` and `ruff check .` could not run here because `pytest` and `ruff` are not installed in the available environment.