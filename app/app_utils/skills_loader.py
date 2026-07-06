# Copyright 2026 Google LLC
import os


def load_skills() -> str:
    # Dynamically loads and concatenates all markdown files inside the root skills/ directory.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    skills_dir = os.path.join(root_dir, "skills")

    if not os.path.exists(skills_dir):
        return ""

    skills_contents = []
    # Sort files to ensure deterministic concatenation order
    for filename in sorted(os.listdir(skills_dir)):
        if filename.endswith(".md"):
            filepath = os.path.join(skills_dir, filename)
            try:
                with open(filepath, encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        skills_contents.append(content)
            except Exception as e:
                print(f"Error loading skill file {filename}: {e}")

    return "\n\n".join(skills_contents)
