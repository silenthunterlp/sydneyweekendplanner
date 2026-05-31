"""
Package SydneyPlanner dev skills into .skill files (zip archives).
Run from the project root or pass paths as arguments.
"""
import zipfile
from pathlib import Path

SKILLS_SRC = Path(
    r"C:\Users\saram\AppData\Roaming\Claude\local-agent-mode-sessions"
    r"\skills-plugin\8d636386-9a0e-4ade-833c-cddf1c9325e7"
    r"\17b67f94-51f9-47e3-ab90-bbb59c6cc52c\skills"
)
SKILLS = [
    "run-sydney-planner",
    "test-sydney-planner",
    "seed-sydney-planner",
    "check-sydney-services",
]
OUT_DIR = Path(__file__).parent.parent / ".claude" / "skills"


def package(skill_name: str, src_root: Path, out_dir: Path) -> Path:
    skill_path = src_root / skill_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{skill_name}.skill"
    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(skill_path.rglob("*")):
            if f.is_file():
                arcname = f.relative_to(skill_path.parent)
                zf.write(f, arcname)
                print(f"  + {arcname}")
    print(f"  => {out_file}\n")
    return out_file


if __name__ == "__main__":
    print(f"Output: {OUT_DIR}\n")
    for skill in SKILLS:
        print(f"Packaging: {skill}")
        package(skill, SKILLS_SRC, OUT_DIR)
    print("Done.")
