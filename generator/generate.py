
#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC_DIR = ROOT / "spec"
TEMPLATE = ROOT / "generator" / "prompts" / "generate_client.md"

PLATFORMS = {
    "python": {
        "spec": SPEC_DIR / "platforms" / "python.md",
        "output": ROOT / "clients" / "python",
    },
    "android": {
        "spec": SPEC_DIR / "platforms" / "android.md",
        "output": ROOT / "clients" / "android",
    },
}


def read_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Required file missing: {path}")

    return path.read_text(encoding="utf-8")


def build_prompt(platform: str) -> str:
    config = PLATFORMS[platform]
    template = read_file(TEMPLATE)

    replacements = {
        "{{PLATFORM}}": platform,
        "{{OUTPUT_DIRECTORY}}": str(
            config["output"].relative_to(ROOT)
        ),
        "{{PROTOCOL_SPEC}}": read_file(
            SPEC_DIR / "protocol.md"
        ),
        "{{BEHAVIOR_SPEC}}": read_file(
            SPEC_DIR / "behavior.md"
        ),
        "{{STORAGE_SPEC}}": read_file(
            SPEC_DIR / "storage.md"
        ),
        "{{PLATFORM_SPEC}}": read_file(config["spec"]),
    }

    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)

    for placeholder in replacements:
        if placeholder in template:
            raise ValueError(
                f"Unresolved placeholder: {placeholder}"
            )

    return template


def generate(platform: str) -> None:
    if shutil.which("codex") is None:
        raise RuntimeError(
            "Codex CLI is not installed or not on PATH."
        )

    output = PLATFORMS[platform]["output"]
    output.mkdir(parents=True, exist_ok=True)

    prompt = build_prompt(platform)

    print(f"Generating {platform} client...")
    print(f"Output: {output}")
    print("Invoking Codex...")

    result = subprocess.run(
    [
        "codex",
        "exec",
        "--sandbox",
        "workspace-write",
        "-",
    ],
        input=prompt,
        text=True,
        cwd=ROOT,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Codex generation failed: exit code "
            f"{result.returncode}"
        )

    generated_files = [
        path for path in output.rglob("*")
        if path.is_file()
    ]

    if not generated_files:
        raise RuntimeError(
            f"Codex completed but created no files in {output}"
        )

    print(f"Generation completed: {platform}")
    print(f"Generated files: {len(generated_files)}")
    print("Run platform validation before accepting the output.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Specification-driven messaging client generator"
    )

    parser.add_argument(
        "platform",
        choices=PLATFORMS.keys(),
        help="Client platform to generate",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Assemble the prompt without invoking Codex",
    )

    args = parser.parse_args()

    try:
        prompt = build_prompt(args.platform)

        if args.dry_run:
            print(
                f"Prompt assembled for {args.platform}: "
                f"{len(prompt)} characters"
            )
            print("Dry run successful. Codex was not invoked.")
            return

        generate(args.platform)

    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

