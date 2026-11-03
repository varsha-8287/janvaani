from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app')

from app.database.session import SessionLocal
from app.database.models import Scheme, SchemeVersion, SourceDocument
from sqlalchemy import select

candidate_dirs = [
    ROOT / 'janvaani_government_schemes_dataset' / 'staging' / 'pilot',
    ROOT.parent / 'janvaani_government_schemes_dataset' / 'staging' / 'pilot',
    Path('/app/janvaani_government_schemes_dataset/staging/pilot'),
    Path('janvaani_government_schemes_dataset/staging/pilot'),
    Path('../janvaani_government_schemes_dataset/staging/pilot'),
]
PILOT_DIR = None
for cd in candidate_dirs:
    if cd.exists():
        PILOT_DIR = cd
        break
if not PILOT_DIR:
    PILOT_DIR = Path('/app/janvaani_government_schemes_dataset/staging/pilot')


def canonical_hash(data: dict) -> str:
    serialized = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def seed_schemes():
    db = SessionLocal()
    try:
        pilot_files = sorted(PILOT_DIR.glob('*.json'))
        print(f'Found {len(pilot_files)} pilot scheme files in {PILOT_DIR}.')

        for file_path in pilot_files:
            with file_path.open('r', encoding='utf-8') as f:
                doc = json.load(f)

            slug = doc['slug']
            title = doc['title']
            authority = doc.get('administering_authority')
            level = doc.get('government_level', 'central')
            language = doc.get('language', 'en')
            summary = doc.get('summary')
            benefits = doc.get('benefits')
            eligibility = doc.get('eligibility')
            required_docs = doc.get('required_documents')
            app_steps = doc.get('application_steps')
            valid_from = None
            if doc.get('valid_from'):
                try:
                    valid_from = datetime.fromisoformat(doc['valid_from'])
                except Exception:
                    pass
            valid_until = None
            if doc.get('valid_until'):
                try:
                    valid_until = datetime.fromisoformat(doc['valid_until'])
                except Exception:
                    pass

            src_list = doc.get('source_records') or [{}]
            src = src_list[0]
            src_url = src.get('url') or 'https://www.india.gov.in'
            publisher = src.get('publisher') or authority
            retrieved_at = datetime.now(timezone.utc)
            if src.get('retrieved_at'):
                try:
                    retrieved_at = datetime.fromisoformat(src['retrieved_at'])
                except Exception:
                    pass

            content_hash = src.get('content_hash') or canonical_hash(doc)

            # Check if scheme already exists
            existing_scheme = db.scalar(select(Scheme).where(Scheme.slug == slug))
            if existing_scheme:
                print(f'Updating existing scheme: {slug}')
                existing_scheme.status = 'published'
                existing_scheme.title = title
                existing_scheme.administering_authority = authority
                existing_scheme.government_level = level

                # Ensure version is approved
                version = db.scalar(
                    select(SchemeVersion).where(SchemeVersion.scheme_id == existing_scheme.id)
                )
                if version:
                    version.review_status = 'approved'
                    version.description = summary
                    version.benefits = benefits
                    version.eligibility_criteria = eligibility
                    version.required_documents = required_docs
                    version.application_process = app_steps
                else:
                    version = SchemeVersion(
                        scheme_id=existing_scheme.id,
                        version_number=1,
                        language=language,
                        description=summary,
                        benefits=benefits,
                        eligibility_criteria=eligibility,
                        required_documents=required_docs,
                        application_process=app_steps,
                        valid_from=valid_from,
                        valid_until=valid_until,
                        review_status='approved',
                    )
                    db.add(version)
                    db.flush()

                # Ensure source document is verified
                src_doc = db.scalar(
                    select(SourceDocument).where(SourceDocument.scheme_version_id == version.id)
                )
                if src_doc:
                    src_doc.review_status = 'verified'
                    src_doc.source_url = src_url
                else:
                    src_doc = SourceDocument(
                        scheme_version_id=version.id,
                        source_url=src_url,
                        publisher=publisher,
                        retrieved_at=retrieved_at,
                        content_hash=content_hash,
                        language=language,
                        review_status='verified',
                    )
                    db.add(src_doc)
                    db.flush()

                # Ensure eligibility criteria rules point to this verified source document
                if isinstance(version.eligibility_criteria, dict) and 'rules' in version.eligibility_criteria:
                    import copy
                    elig_copy = copy.deepcopy(version.eligibility_criteria)
                    for rule in elig_copy.get('rules', []):
                        if 'source' in rule and isinstance(rule['source'], dict):
                            rule['source']['source_document_id'] = str(src_doc.id)
                            rule['source']['source_url'] = src_doc.source_url
                            rule['source']['retrieved_at'] = src_doc.retrieved_at.isoformat()
                    version.eligibility_criteria = elig_copy

            else:
                print(f'Creating new published scheme: {slug}')
                scheme = Scheme(
                    slug=slug,
                    title=title,
                    administering_authority=authority,
                    government_level=level,
                    status='published',
                )
                db.add(scheme)
                db.flush()

                version = SchemeVersion(
                    scheme_id=scheme.id,
                    version_number=1,
                    language=language,
                    description=summary,
                    benefits=benefits,
                    eligibility_criteria=eligibility,
                    required_documents=required_docs,
                    application_process=app_steps,
                    valid_from=valid_from,
                    valid_until=valid_until,
                    review_status='approved',
                )
                db.add(version)
                db.flush()

                src_doc = SourceDocument(
                    scheme_version_id=version.id,
                    source_url=src_url,
                    publisher=publisher,
                    retrieved_at=retrieved_at,
                    content_hash=content_hash,
                    language=language,
                    review_status='verified',
                )
                db.add(src_doc)
                db.flush()

                if isinstance(version.eligibility_criteria, dict) and 'rules' in version.eligibility_criteria:
                    import copy
                    elig_copy = copy.deepcopy(version.eligibility_criteria)
                    for rule in elig_copy.get('rules', []):
                        if 'source' in rule and isinstance(rule['source'], dict):
                            rule['source']['source_document_id'] = str(src_doc.id)
                            rule['source']['source_url'] = src_doc.source_url
                            rule['source']['retrieved_at'] = src_doc.retrieved_at.isoformat()
                    version.eligibility_criteria = elig_copy

        # Also publish test schemes if any exist
        test_schemes = db.scalars(select(Scheme).where(Scheme.status == 'draft')).all()
        for ts in test_schemes:
            ts.status = 'published'
            for ver in ts.versions:
                ver.review_status = 'approved'
                for doc in ver.source_documents:
                    doc.review_status = 'verified'

        db.commit()
        print('Successfully seeded and published all pilot schemes!')

        # Verify
        published = db.scalars(select(Scheme).where(Scheme.status == 'published')).all()
        print(f'Total published schemes in database now: {len(published)}')
        return len(published)

    except Exception as e:
        db.rollback()
        print(f'Error during seeding: {e}')
        raise
    finally:
        db.close()


if __name__ == '__main__':
    seed_schemes()
