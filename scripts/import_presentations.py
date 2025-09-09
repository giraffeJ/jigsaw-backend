#!/usr/bin/env python3
"""
Import historical presentation/matching history from Excel/CSV.

Expected row format (per the user's description):
- col 0: receiver_nickname (the person who received the presentation)
- col 1: shown_nickname (the person who was shown to the receiver)
- col 2: receiver_accept (string: '수락'/'거절' or 'Y'/'N' etc)
- col 3: shown_accept (optional) (string: '수락'/'거절' or 'Y'/'N')

This script will:
- Map nicknames to user IDs via DB lookup
- Create Presentation rows:
  * requester_id = shown_user_id
  * candidate_id = receiver_user_id
  * outcome:
      - if receiver_accept is decline -> set outcome=DECLINED
      - if receiver_accept is accept and shown_accept absent -> outcome=PENDING (decision awaited)
      - if receiver_accept is accept and shown_accept present:
          - if both accepted -> outcome=ACCEPTED
          - if shown declined -> outcome=DECLINED
- Set decided_at to now for rows where decision(s) exist.
- Rendered_message will be left empty (imported history likely does not contain the exact template)
"""
import argparse
import sys
import os
import math
from datetime import datetime

try:
    import pandas as pd
except Exception:
    print("Please install pandas (pip install pandas)")
    raise

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db import SessionLocal
from app import crud, models

def parse_accept(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in {"수락", "y", "yes", "accept", "o", "예"}:
        return "accepted"
    if s in {"거절", "n", "no", "decline", "아니오"}:
        return "declined"
    return None

def import_file(path, sheet=None, dry_run=False):
    if path.lower().endswith((".xls", ".xlsx")):
        df = pd.read_excel(path, sheet_name=sheet, dtype=object)
    else:
        df = pd.read_csv(path, dtype=object)

    df = df.fillna(value=None)
    session = SessionLocal()
    inserted = 0
    errors = []
    try:
        for idx, row in df.iterrows():
            receiver = row.iloc[0]
            shown = row.iloc[1] if len(row) > 1 else None
            receiver_accept = row.iloc[2] if len(row) > 2 else None
            shown_accept = row.iloc[3] if len(row) > 3 else None

            if not receiver or not shown:
                errors.append({"row": int(idx)+1, "error": "missing receiver or shown nickname"})
                continue

            recv_user = session.query(models.User).filter(models.User.nickname == str(receiver).strip()).first()
            shown_user = session.query(models.User).filter(models.User.nickname == str(shown).strip()).first()
            if not recv_user or not shown_user:
                errors.append({"row": int(idx)+1, "error": f"user not found receiver={receiver} shown={shown}"})
                continue

            recv_dec = parse_accept(receiver_accept)
            shown_dec = parse_accept(shown_accept)

            # Build presentation record: requester=shown_user (who was shown), candidate=receiver (who received)
            outcome = models.PresentationOutcome.PENDING
            decided_at = None
            if recv_dec == "declined":
                outcome = models.PresentationOutcome.DECLINED
                decided_at = datetime.utcnow()
            elif recv_dec == "accepted":
                if shown_dec is None:
                    outcome = models.PresentationOutcome.PENDING
                else:
                    if shown_dec == "accepted":
                        outcome = models.PresentationOutcome.ACCEPTED
                    else:
                        outcome = models.PresentationOutcome.DECLINED
                    decided_at = datetime.utcnow()

            if dry_run:
                inserted += 1
                continue

            p = models.Presentation(
                requester_id=shown_user.id,
                candidate_id=recv_user.id,
                plan_id=None,
                template_key=None,
                template_version=None,
                rendered_message=None,
                outcome=outcome,
                presented_at=datetime.utcnow(),
                decided_at=decided_at,
            )
            session.add(p)
            inserted += 1
        if not dry_run:
            session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()

    print("Import finished. inserted:", inserted, "errors:", len(errors))
    if errors:
        print("Examples:", errors[:10])

def main():
    parser = argparse.ArgumentParser(description="Import presentation history from Excel/CSV")
    parser.add_argument("path", help="path to file")
    parser.add_argument("--sheet", help="sheet name for excel", default=None)
    parser.add_argument("--dry-run", action="store_true", help="do not write to DB")
    args = parser.parse_args()
    import_file(args.path, sheet=args.sheet, dry_run=args.dry_run)

if __name__ == '__main__':
    main()
