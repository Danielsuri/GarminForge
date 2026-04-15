#!/usr/bin/env python3
"""
GarminForge user management CLI.

Usage:
    python manage.py list
    python manage.py show <email>
    python manage.py create <email> [--name NAME] [--password PASSWORD]
    python manage.py delete <email> [--yes]
    python manage.py set-password <email> [--password PASSWORD]

Environment:
    GARMINFORGE_DB_PATH — path to SQLite database (default: ~/.garminforge.db)
"""
from __future__ import annotations

import argparse
import getpass
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get_db():
    from web.db import SessionLocal
    return SessionLocal()


def _fmt_row(label: str, value: object) -> None:
    print(f"  {label:<22} {value}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_list(args: argparse.Namespace) -> None:
    from web.models import User
    db = _get_db()
    try:
        users = db.query(User).order_by(User.created_at).all()
    finally:
        db.close()

    if not users:
        print("No users found.")
        return

    header = f"{'EMAIL':<36}  {'NAME':<22}  {'GOOGLE':<6}  {'APPLE':<6}  {'VERIFIED':<8}  {'CREATED'}"
    print(header)
    print("-" * len(header))
    for u in users:
        print(
            f"{u.email:<36}  "
            f"{(u.display_name or ''):<22}  "
            f"{'yes' if u.google_sub else 'no':<6}  "
            f"{'yes' if u.apple_sub else 'no':<6}  "
            f"{'yes' if u.is_verified else 'no':<8}  "
            f"{str(u.created_at)[:19]}"
        )
    print(f"\n{len(users)} user(s) total.")


def cmd_show(args: argparse.Namespace) -> None:
    from web.models import User
    db = _get_db()
    try:
        user = db.query(User).filter_by(email=args.email.strip().lower()).first()
    finally:
        db.close()

    if not user:
        print(f"No user found with email: {args.email}", file=sys.stderr)
        sys.exit(1)

    print(f"\nUser: {user.email}")
    print("-" * 50)
    _fmt_row("ID", user.id)
    _fmt_row("Display name", user.display_name or "(none)")
    _fmt_row("Password set", "yes" if user.hashed_password else "no")
    _fmt_row("Google linked", "yes" if user.google_sub else "no")
    _fmt_row("Apple linked", "yes" if user.apple_sub else "no")
    _fmt_row("Verified", user.is_verified)
    _fmt_row("Questionnaire done", user.questionnaire_completed)
    _fmt_row("Fitness level", user.fitness_level or "(none)")
    _fmt_row("Fitness rank", user.fitness_rank or "(none)")
    _fmt_row("Preferred lang", user.preferred_lang or "(none)")
    _fmt_row("Created at", user.created_at)
    _fmt_row("Last login", user.last_login_at or "(never)")
    print()


def cmd_create(args: argparse.Namespace) -> None:
    from web.auth_utils import hash_password
    from web.models import User
    db = _get_db()
    try:
        email = args.email.strip().lower()
        if db.query(User).filter_by(email=email).first():
            print(f"Error: a user with email '{email}' already exists.", file=sys.stderr)
            sys.exit(1)

        password = args.password
        if not password:
            password = getpass.getpass("Password (leave blank for no password): ")

        user = User(
            email=email,
            display_name=args.name or None,
            hashed_password=hash_password(password) if password else None,
            is_verified=True,
            questionnaire_completed=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created user: {user.email} (id={user.id})")
    finally:
        db.close()


def cmd_delete(args: argparse.Namespace) -> None:
    from web.models import User
    db = _get_db()
    try:
        email = args.email.strip().lower()
        user = db.query(User).filter_by(email=email).first()
        if not user:
            print(f"No user found with email: {email}", file=sys.stderr)
            sys.exit(1)

        if not args.yes:
            confirm = input(f"Delete '{email}' and all their data? [y/N] ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                return

        db.delete(user)
        db.commit()
        print(f"Deleted user: {email}")
    finally:
        db.close()


def cmd_set_password(args: argparse.Namespace) -> None:
    from web.auth_utils import hash_password
    from web.models import User
    db = _get_db()
    try:
        email = args.email.strip().lower()
        user = db.query(User).filter_by(email=email).first()
        if not user:
            print(f"No user found with email: {email}", file=sys.stderr)
            sys.exit(1)

        password = args.password
        if not password:
            password = getpass.getpass(f"New password for {email}: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("Passwords do not match.", file=sys.stderr)
                sys.exit(1)

        if len(password) < 8:
            print("Password must be at least 8 characters.", file=sys.stderr)
            sys.exit(1)

        user.hashed_password = hash_password(password)
        db.commit()
        print(f"Password updated for: {email}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GarminForge user management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    sub.add_parser("list", help="List all users")

    # show
    p_show = sub.add_parser("show", help="Show details for a user")
    p_show.add_argument("email", help="User email address")

    # create
    p_create = sub.add_parser("create", help="Create a new user")
    p_create.add_argument("email", help="User email address")
    p_create.add_argument("--name", help="Display name")
    p_create.add_argument("--password", help="Password (prompted if omitted)")

    # delete
    p_delete = sub.add_parser("delete", help="Delete a user and all their data")
    p_delete.add_argument("email", help="User email address")
    p_delete.add_argument("--yes", action="store_true", help="Skip confirmation prompt")

    # set-password
    p_setpw = sub.add_parser("set-password", help="Set or reset a user's password")
    p_setpw.add_argument("email", help="User email address")
    p_setpw.add_argument("--password", help="New password (prompted if omitted)")

    args = parser.parse_args()
    {
        "list": cmd_list,
        "show": cmd_show,
        "create": cmd_create,
        "delete": cmd_delete,
        "set-password": cmd_set_password,
    }[args.command](args)


if __name__ == "__main__":
    main()
