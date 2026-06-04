"""
Add or replace bullet points on the Tesla work-experience entry in a user's portfolio.

Usage:
  uv run python scripts/add_tesla_work_bullets.py --dry-run
  uv run python scripts/add_tesla_work_bullets.py
  uv run python scripts/add_tesla_work_bullets.py --append
  uv run python scripts/add_tesla_work_bullets.py --company "Tesla" --email user@example.com
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT / ".env")

from core.database.init import init_db
from core.models.portfolio import Portfolio
from core.models.user import User

DEFAULT_EMAIL = "mujakayadan@outlook.com"
DEFAULT_COMPANY = "tesla"

TESLA_RESPONSIBILITIES: list[str] = [
    "Designed a cross-modal knowledge-distillation pipeline in which an intensity-trained YOLO teacher labeled point-cloud frames to train a YOLOv11 student detector, lifting object detection from 32.8% (SCRFD baseline) to 89.7%.",
    "Built an end-to-end 3D pose pipeline combining SCRFD face detection, MediaPipe / DAD-3DHeads 68-point landmark regression, FLAME parametric mesh fitting, Kabsch similarity alignment, and Open3D ICP refinement; achieving sub-5 mm RMSE on object localization.",
    "Trained a ResNet-34 PointCloudNet on raster-ordered 4-channel (ΔX, ΔY, ΔZ, intensity) tensors with PyTorch Lightning, outputting 6-DoF pose plus confidence; exported to ONNX for shared deployment across a Python batch service and a C++ real-time runtime.",
    "Developed a fisheye camera calibration tool using three coplanar ArUco markers, solving intrinsics (K, D, K_new) and 6-DoF extrinsics via PnP with homography-warped subpixel grid refinement.",
    "Built a real-time gaze-estimation system combining MediaPipe FaceMesh (468 landmarks), iris detection with pupil-threshold fallback, per-eye eyelid-band normalization, EMA-based neutral calibration, and 1-Euro filtering for temporal stability on 1920×1080 near-IR driver video.",
    "Authored a vendor-agnostic point-cloud I/O library supporting .bin / .ply / .pcd / .npy / .npz with auto-discovery, Open3D interactive visualization (density / distance / uniform color schemes), and a standardized (N, 4) [x, y, z, intensity] array convention, reused across three downstream projects.",
    "Deployed a FastAPI inference service with SQLite + Alembic schema migrations tracking model versions, sessions, and per-frame detections; supports both CLI batch processing and package-import inline integration with the upstream analytics platform.",
    "Implemented an async multimodal frame-pairing pipeline aligning point-cloud frames, fisheye cabin video, and gaze CAN signals across UTC / wall-clock / frame-counter clock domains, with sub-second interpolation between gaze-counter transitions and byte-checksum-validated network transfer.",
    "Solved perspective-corrected anatomical head-center estimation by registering FLAME meshes to detected landmarks and benchmarking 13 head-center methods (mapped_landmarks, mesh_centroid, FLAME ear-canal midpoint, raw point cloud, learned correction) with per-bucket yaw / distance error analysis against rig ground truth.",
    "Owned the full vertical of a perception system spanning ToF drivers, real-time C++/Qt tracking, PyTorch training pipelines, ONNX deployment, FastAPI services, SQLite analytics, and fleet-wide, stream dataset orchestration, bridging hardware, ML, and data layers in a single shipping product.",
]


def _company_matches(company: str, needle: str) -> bool:
    return needle.lower() in company.lower()


def _console_safe(text: str) -> str:
    return text.encode("ascii", errors="replace").decode("ascii")


def _merge_responsibilities(existing: list[str], new_bullets: list[str]) -> list[str]:
    seen = {b.strip() for b in existing if b.strip()}
    merged = list(existing)
    for bullet in new_bullets:
        text = bullet.strip()
        if text and text not in seen:
            merged.append(text)
            seen.add(text)
    return merged


async def update_tesla_bullets(
    email: str,
    company_needle: str,
    *,
    bullets: list[str],
    append: bool = False,
    dry_run: bool = False,
) -> None:
    await init_db()
    user = await User.find_one(User.email == email)
    if not user:
        raise SystemExit(f"User not found for email: {email}")

    portfolio = await Portfolio.find_one(Portfolio.user_id == user.id)
    if not portfolio:
        raise SystemExit(f"Portfolio not found for user {user.id}")

    work = list(portfolio.work_experience or [])
    if not work:
        raise SystemExit("Portfolio has no work experience entries.")

    index = next(
        (i for i, w in enumerate(work) if _company_matches(w.company, company_needle)),
        None,
    )
    if index is None:
        companies = [w.company for w in work]
        raise SystemExit(
            f"No work experience matching company {company_needle!r}. "
            f"Found: {companies}"
        )

    entry = work[index]
    before = len(entry.responsibilities or [])
    if append:
        entry.responsibilities = _merge_responsibilities(
            list(entry.responsibilities or []), bullets
        )
    else:
        entry.responsibilities = list(bullets)

    after = len(entry.responsibilities)
    print(f"User: {email} ({user.id})")
    print(f"Portfolio: {portfolio.id}")
    print(
        f"Tesla entry: {entry.job_title!r} @ {entry.company!r} "
        f"({entry.location}, {entry.time})"
    )
    print(f"Responsibilities: {before} -> {after} bullets")

    if dry_run:
        print("Dry run — no database writes.")
        for i, bullet in enumerate(entry.responsibilities, start=1):
            preview = bullet if len(bullet) <= 90 else f"{bullet[:87]}..."
            print(f"  {i}. {_console_safe(preview)}")
        return

    work[index] = entry
    portfolio.work_experience = work
    portfolio.updated_at = datetime.now(UTC)
    await portfolio.save()
    print("Saved portfolio.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="User email")
    parser.add_argument(
        "--company",
        default=DEFAULT_COMPANY,
        help="Substring to match work experience company (default: tesla)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append bullets not already present instead of replacing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing",
    )
    args = parser.parse_args()
    asyncio.run(
        update_tesla_bullets(
            args.email,
            args.company,
            bullets=TESLA_RESPONSIBILITIES,
            append=args.append,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
