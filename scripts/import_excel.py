#!/usr/bin/env python3
"""
Excel/CSV -> Database bulk import helper.

Usage:
  pip install pandas openpyxl xlrd     # openpyxl needed for .xlsx, xlrd for older .xls if required
  python scripts/import_excel.py path/to/file.xlsx --sheet Sheet1
  python scripts/import_excel.py path/to/file.csv

Notes:
 - Column headers in the spreadsheet should match the Pydantic field names used by UserCreate.
 - Required fields: nickname, privacy_consent, confidentiality_consent, real_name, kakao_id,
   phone_number, birth_year, height, residence, education_level, final_education, job_title,
   workplace, workplace_address, religion, smoking_status, preferred_age_range, workplace_matching,
   preferred_smoking
 - Optional fields: referrer_info, mbti, hobbies, additional_info, preferred_religion,
   additional_matching_condition
 - Enum/text normalization is attempted (examples: "흡연" -> enum member).
 - Duplicate rows (same kakao_id or phone_number) will be skipped by default.
 - Use --dry-run to validate without committing.
"""
import argparse
import sys
from typing import List, Dict, Any, Optional
import math
import re
from datetime import datetime

try:
    import pandas as pd
except Exception as e:
    print("pandas is required. Install with: pip install pandas openpyxl")
    raise

from sqlalchemy.orm import Session
from sqlalchemy import or_
import os
import sys

# Ensure project root is on sys.path so `import app` works when running this script directly.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db import SessionLocal
from app import models, schemas


EXPECTED_FIELDS = [
    "nickname", "referrer_info",
    "privacy_consent", "confidentiality_consent",
    "real_name", "kakao_id", "phone_number",
    "birth_year", "height", "residence",
    "education_level", "final_education", "job_title",
    "workplace", "workplace_address",
    "religion", "smoking_status", "mbti", "hobbies", "additional_info",
    # New: prefer explicit min/max year fields preferred_age_min/preferred_age_max preferred over preferred_age_range
    "preferred_age_min", "preferred_age_max", "preferred_age_range",
    "workplace_matching", "preferred_smoking",
    "preferred_religion", "additional_matching_condition"
]


def parse_bool(v) -> Optional[bool]:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "true", "t", "yes", "y", "예", "o", "o"}:
        return True
    if s in {"0", "false", "f", "no", "n", "아니오", "아님"}:
        return False
    return None


def none_if_nan(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Normalize phone numbers to format 010-xxxx-xxxx when possible."""
    if phone is None:
        return None
    s = str(phone).strip()
    # Remove non-digit characters
    digits = re.sub(r"\D+", "", s)
    # If digits missing leading zero (common when Excel strips leading 0), try to add it
    if len(digits) == 10 and not digits.startswith("0"):
        digits = "0" + digits
    # Heuristic: if 11 digits and startswith 010 -> format 010-xxxx-xxxx
    if len(digits) == 11 and digits.startswith("010"):
        return f"{digits[0:3]}-{digits[3:7]}-{digits[7:11]}"
    # If 11 digits but not starting with 010, still try 3-4-4 or 3-3-5 depending on patterns (best-effort)
    if len(digits) == 11:
        return f"{digits[0:3]}-{digits[3:7]}-{digits[7:11]}"
    # If 10 digits and startswith 02 (Seoul) -> 02-xxxx-xxxx
    if len(digits) == 10:
        if digits.startswith("02"):
            return f"{digits[0:2]}-{digits[2:6]}-{digits[6:10]}"
        # Otherwise 3-3-4
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
    # If already looks good (has hyphens), return original stripped
    if "-" in s:
        return s
    # Couldn't reliably format, return digits if any
    return digits if digits else None


def normalize_enum(enum_cls, value):
    """
    More flexible enum normalization:
    - Accepts exact member names or member values
    - Tries common Korean abbreviations/mappings (e.g., '대졸' -> '대학교', '석사' -> '대학원')
    - Strips whitespace and common punctuation before matching
    - Falls back to substring matching where appropriate
    """
    if value is None:
        return None
    # If already enum member
    if isinstance(value, enum_cls):
        return value
    s = str(value).strip()
    # quick-normalize common variants
    norm_map = {
        "대졸": "대학교",
        "학사": "대학교",
        "석사": "대학원",
        "박사": "대학원",
        "무종교": "무교",
        "비흡연": "비흡연",
        "흡연자": "흡연",
        "가끔흡연": "가끔",
        "전자담배": "비흡연",
        "비흡연, 전자담배": "비흡연",
        "비흡연/전자담배": "비흡연",
        "비흡연 전자담배": "비흡연",
    }
    s_key = s.replace(" ", "").replace("/", "").replace(",", "")
    if s in norm_map:
        s = norm_map[s]
    elif s_key in norm_map:
        s = norm_map[s_key]
    else:
        # substring heuristics: e.g., "대졸(학사)", "석사졸업" 등
        if "대졸" in s or "학사" in s:
            s = "대학교"
        elif "석사" in s or "석사졸" in s:
            s = "대학원"
        elif "박사" in s:
            s = "대학원"

    # Try by member name (enum member identifiers)
    try:
        return enum_cls[s]
    except Exception:
        pass

    # Try matching by value (exact)
    for m in enum_cls:
        if str(m.value) == s:
            return m

    # Try case-insensitive value match
    for m in enum_cls:
        if str(m.value).lower() == s.lower():
            return m

    # As a last resort, try constructing with the raw string (works for str-enums)
    try:
        return enum_cls(s)
    except Exception:
        return None


def load_dataframe(path: str, sheet: Optional[str] = None) -> pd.DataFrame:
    if path.lower().endswith((".xls", ".xlsx")):
        if sheet:
            return pd.read_excel(path, sheet_name=sheet, dtype=object)
        return pd.read_excel(path, dtype=object)
    elif path.lower().endswith(".csv"):
        return pd.read_csv(path, dtype=object)
    else:
        # Try excel first, fallback to csv
        try:
            return pd.read_excel(path, dtype=object)
        except Exception:
            return pd.read_csv(path, dtype=object)


def validate_and_prepare_row(row: Dict[str, Any]) -> (Optional[Dict[str, Any]], Optional[str]):
    data = {}
    for field in EXPECTED_FIELDS:
        val = row.get(field, None)
        val = none_if_nan(val)
        # boolean fields
        if field in {"privacy_consent", "confidentiality_consent"}:
            b = parse_bool(val)
            if b is None:
                # If missing or unparsable, default to False (or let validation catch it)
                data[field] = False
            else:
                data[field] = b
            continue
        data[field] = val

    # Convert numeric fields which may come as strings
    if data.get("birth_year") is not None:
        try:
            data["birth_year"] = int(float(data["birth_year"]))
        except Exception:
            pass

    if data.get("height") is not None:
        try:
            data["height"] = int(float(data["height"]))
        except Exception:
            pass

    # If the sheet already provides preferred_age_min / preferred_age_max, accept them directly.
    # This follows the new schema change where preferred ages are stored as full-year integers.
    if data.get("preferred_age_min") is not None:
        try:
            data["preferred_age_min"] = int(float(data["preferred_age_min"]))
        except Exception:
            # leave as-is for validation to catch
            pass
    if data.get("preferred_age_max") is not None:
        try:
            data["preferred_age_max"] = int(float(data["preferred_age_max"]))
        except Exception:
            # leave as-is for validation to catch
            pass

    # Normalize datetime-like values to strings (Excel may parse some cells as datetimes)
    for k, v in list(data.items()):
        if isinstance(v, datetime):
            # Prefer ISO date string
            data[k] = v.strftime("%Y-%m-%d")
        # convert numeric-like to str for fields that expect strings (e.g., phone)
        if k in {"phone_number", "kakao_id", "preferred_age_range"} and v is not None:
            data[k] = str(v).strip()
    # Normalize phone format if present
    if data.get("phone_number"):
        data["phone_number"] = normalize_phone(data["phone_number"])

    # Pre-normalize enum-like fields so Pydantic validation accepts common variants from Excel
    enum_field_map = {
        "education_level": models.EducationLevel,
        "religion": models.Religion,
        "smoking_status": models.SmokingStatus,
        "workplace_matching": models.WorkplaceMatching,
    }

    for ef, enum_cls in enum_field_map.items():
        raw = data.get(ef)
        if raw is None:
            continue
        # If a datetime or number slipped in, stringify it
        if isinstance(raw, datetime):
            raw = raw.strftime("%Y-%m-%d")
        # Try direct normalization
        mem = normalize_enum(enum_cls, raw)
        if mem:
            data[ef] = mem.value
            continue
        # Try splitting common separators and normalize first viable token
        if isinstance(raw, str) and any(sep in raw for sep in [",", "/", ";", "|"]):
            for token in re.split(r"[,/;|]", raw):
                token = token.strip()
                if not token:
                    continue
                mem2 = normalize_enum(enum_cls, token)
                if mem2:
                    data[ef] = mem2.value
                    break
        # Leave as-is if normalization failed (Pydantic will catch it)

    # Pydantic validation
    try:
        user_create = schemas.UserCreate(**data)
    except Exception as e:
        return None, str(e)

    # Convert enums to model enums (models.* are enum.Enum classes)
    prepared = user_create.dict()
    # If Pydantic returned Enum members (schemas enums), extract their .value to plain strings
    for k in ["education_level", "religion", "smoking_status", "workplace_matching"]:
        v = prepared.get(k)
        if v is None:
            continue
        # handle Pydantic Enum instances (from schemas)
        if hasattr(v, "value"):
            prepared[k] = v.value

    # Map single-value enums to model enums
    prepared["education_level"] = normalize_enum(models.EducationLevel, prepared.get("education_level"))
    prepared["religion"] = normalize_enum(models.Religion, prepared.get("religion"))
    prepared["smoking_status"] = normalize_enum(models.SmokingStatus, prepared.get("smoking_status"))
    prepared["workplace_matching"] = normalize_enum(models.WorkplaceMatching, prepared.get("workplace_matching"))

    # preferred_smoking: allow multi-value lists or separators -> normalize each token to SmokingStatus and store CSV of values
    pref_sm_raw = prepared.get("preferred_smoking")
    if pref_sm_raw:
        tokens = []
        if isinstance(pref_sm_raw, (list, tuple)):
            tokens = [str(t).strip() for t in pref_sm_raw if t is not None]
        elif isinstance(pref_sm_raw, str) and any(sep in pref_sm_raw for sep in [",", "/", ";", "|"]):
            tokens = [t.strip() for t in re.split(r"[,/;|]", pref_sm_raw) if t.strip()]
        elif isinstance(pref_sm_raw, str):
            tokens = [pref_sm_raw.strip()]
        norm_vals = []
        for tok in tokens:
            mem = normalize_enum(models.SmokingStatus, tok)
            if mem:
                norm_vals.append(mem.value)
        prepared["preferred_smoking"] = ",".join(norm_vals) if norm_vals else None

    # preferred_religion: allow multi-value lists or separators -> normalize each token to Religion and store CSV
    pref_rel_raw = prepared.get("preferred_religion")
    if pref_rel_raw:
        tokens = []
        if isinstance(pref_rel_raw, (list, tuple)):
            tokens = [str(t).strip() for t in pref_rel_raw if t is not None]
        elif isinstance(pref_rel_raw, str) and any(sep in pref_rel_raw for sep in [",", "/", ";", "|"]):
            tokens = [t.strip() for t in re.split(r"[,/;|]", pref_rel_raw) if t.strip()]
        elif isinstance(pref_rel_raw, str):
            tokens = [pref_rel_raw.strip()]
        norm_vals = []
        for tok in tokens:
            mem = normalize_enum(models.Religion, tok)
            if mem:
                norm_vals.append(mem.value)
        prepared["preferred_religion"] = ",".join(norm_vals) if norm_vals else None

    # If any required enum conversion failed, return error for mandatory enums
    enum_fields = ["education_level", "religion", "smoking_status", "workplace_matching"]
    for ef in enum_fields:
        if getattr(prepared, "get", None) and prepared.get(ef) is None:
            # For required enums, we must ensure presence
            if ef in ["education_level", "religion", "smoking_status", "workplace_matching"]:
                return None, f"Enum conversion failed or missing for field '{ef}'"

    return prepared, None


def bulk_import(path: str, sheet: Optional[str], dry_run: bool = False, chunk_size: int = 1000):
    df = load_dataframe(path, sheet)
    if df.empty:
        print("No rows found in the provided file.")
        return

    # Normalize column names: lower-case and strip spaces to help mapping
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]

    # If headers use human-friendly labels, user must rename columns to field names.
    missing = [f for f in ["nickname", "kakao_id", "phone_number"] if f not in df.columns]
    if missing:
        print("Missing required columns (expected field names):", missing)
        print("Column names found:", list(df.columns))
        print("Please ensure spreadsheet uses the exact field names. See script docstring.")
        return

    # Collect keys to check duplicates in DB
    kakao_ids = set([x for x in df["kakao_id"].astype(str).str.strip().dropna().unique()])
    phone_numbers = set([x for x in df["phone_number"].astype(str).str.strip().dropna().unique()])

    session: Session = SessionLocal()
    try:
        # Query existing users by kakao_id or phone_number
        existing = session.query(models.User).filter(
            or_(models.User.kakao_id.in_(list(kakao_ids)), models.User.phone_number.in_(list(phone_numbers)))
        ).all()
        existing_kakao = {u.kakao_id for u in existing}
        existing_phone = {u.phone_number for u in existing}

        total = len(df)
        to_insert: List[models.User] = []
        skipped_dup = 0
        validation_errors = []

        for idx, row in df.iterrows():
            rowd = {col: (row[col] if col in df.columns else None) for col in EXPECTED_FIELDS}
            # Convert phone/kakao to str
            if rowd.get("kakao_id") is not None:
                rowd["kakao_id"] = str(rowd["kakao_id"]).strip()
            if rowd.get("phone_number") is not None:
                rowd["phone_number"] = str(rowd["phone_number"]).strip()

            # Skip if duplicate in DB
            if rowd.get("kakao_id") in existing_kakao or rowd.get("phone_number") in existing_phone:
                skipped_dup += 1
                continue

            prepared, err = validate_and_prepare_row(rowd)
            if err:
                validation_errors.append({"row": int(idx)+1, "error": err})
                continue

            # Create model instance
            # prepared now contains model enum members for enum fields
            try:
                user_obj = models.User(**prepared)
            except Exception as e:
                validation_errors.append({"row": int(idx)+1, "error": f"Model construction failed: {e}"})
                continue

            to_insert.append(user_obj)

            # Keep existing_kakao/phone updated to avoid inserting same kakao/phone twice from file
            existing_kakao.add(prepared.get("kakao_id"))
            existing_phone.add(prepared.get("phone_number"))

            # Flush in chunks if very large
            if not dry_run and len(to_insert) >= chunk_size:
                session.add_all(to_insert)
                session.commit()
                to_insert = []

        # Final insert
        if not dry_run and to_insert:
            session.add_all(to_insert)
            session.commit()

        print("Import summary:")
        print(f"  Total rows in file: {total}")
        print(f"  Inserted: {0 if dry_run else 'committed to DB (see above count)'}")
        # For more precise inserted count, we can calculate:
        inserted_count = total - skipped_dup - len(validation_errors)
        if dry_run:
            print(f"  Would insert (dry-run): {inserted_count}")
        else:
            print(f"  Inserted (approx): {inserted_count}")
        print(f"  Skipped due to duplicates: {skipped_dup}")
        print(f"  Validation errors: {len(validation_errors)}")
        if validation_errors:
            print("  Examples of validation errors (first 10):")
            for e in validation_errors[:10]:
                print("   ", e)
    except Exception as e:
        session.rollback()
        print("Error during import:", e)
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Import users from Excel/CSV into DB")
    parser.add_argument("path", help="Path to .xlsx/.xls/.csv file")
    parser.add_argument("--sheet", help="Sheet name for Excel files", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not write to DB")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Commit batch size")
    args = parser.parse_args()

    bulk_import(args.path, args.sheet, dry_run=args.dry_run, chunk_size=args.chunk_size)


if __name__ == "__main__":
    main()
