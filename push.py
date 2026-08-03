import subprocess
import sys
import datetime

def run_command(command):
    """Execute a shell command (list form, no shell) and return output."""
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        sys.exit(1)

def git_push(commit_msg=None):
    """Stage all changes, commit with message, and push to remote."""
    print("Checking git status...")
    status = run_command(["git", "status", "--porcelain"])

    if not status:
        print("No changes to commit.")
        return

    print("Staging all changes...")
    run_command(["git", "add", "."])

    # Use provided message or generate default
    if not commit_msg:
        commit_msg = f"update {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    print(f"Committing: '{commit_msg}'")
    run_command(["git", "commit", "-m", commit_msg])

    print("Pushing to remote...")
    run_command(["git", "push"])

    print("Done!")

if __name__ == "__main__":
    # Accept commit message from command line arguments
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    git_push(msg)
