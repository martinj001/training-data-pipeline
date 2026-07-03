import sys, json, os, subprocess

d = json.load(sys.stdin)
fp = d.get("tool_input", {}).get("file_path", "")
repo = r"c:\Users\marti\dev\training-data-pipeline"
plans_dir = os.path.join(repo, "data", "plans")

fp_norm = os.path.normcase(fp.replace("/", os.sep))
plans_norm = os.path.normcase(plans_dir)

if fp and fp_norm.startswith(plans_norm) and fp.endswith(".md"):
    fname = os.path.basename(fp)
    subprocess.run(["git", "-C", repo, "add", fp])
    result = subprocess.run(
        ["git", "-C", repo, "commit", "-m", f"Auto-update plan file: {fname}"],
        capture_output=True, text=True
    )
    if "nothing to commit" not in result.stdout:
        subprocess.run(["git", "-C", repo, "push"])
