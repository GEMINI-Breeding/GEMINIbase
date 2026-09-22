"""
Reset a user's password from the machine running the stack.

For the case the web app can't cover: the only admin forgot their
password and there is no email server to send a reset link. An admin can
reset anyone else's password in Admin → Users; this is for when nobody
can sign in. It runs inside the API container, so only someone with
access to the machine running the stack can use it:

    docker exec geminibase-rest-api poetry run \\
        python -m gemini.rest_api.reset_password you@example.com

Without ``--password`` a strong one is generated and printed once. The
account is re-activated, so a locked-out admin can sign straight back in.
"""
from __future__ import annotations

import argparse
import secrets
import sys
from typing import List, Optional


def reset_password(email: str, password: Optional[str] = None) -> str:
    """Set ``email``'s password (generated if None). Returns the password."""
    from gemini.api.user import User

    user = User.get(email=email)
    if user is None:
        raise LookupError(f"No user with email {email!r}")
    new_password = password or secrets.token_urlsafe(12)
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if user.update(password=new_password, is_active=True) is None:
        raise RuntimeError("The password could not be updated (see the log above)")
    return new_password


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m gemini.rest_api.reset_password",
        description="Reset a GEMINI user's password (no email needed).",
    )
    parser.add_argument("email")
    parser.add_argument(
        "--password",
        help="New password (min 8 characters). Omit to generate one.",
    )
    args = parser.parse_args(argv)
    try:
        new_password = reset_password(args.email, args.password)
    except (LookupError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.password:
        print(f"Password reset for {args.email}.")
    else:
        print(f"Password reset for {args.email}. New password: {new_password}")
        print("Sign in with it, then change it under Settings → Password.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
