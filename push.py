import subprocess
import sys
import datetime

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(e.stderr)
        sys.exit(1)

def git_push():
    print("Checking git status...")
    status = run_command("git status")
    
    if "nothing to commit, working tree clean" in status:
        print("No changes to commit.")
        return

    print(status)
    
    print("\nStaging all changes...")
    run_command("git add .")
    
    commit_msg = input("\nEnter commit message (default: 'update'): ").strip()
    if not commit_msg:
        commit_msg = f"update {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"Committing with message: '{commit_msg}'...")
    run_command(f'git commit -m "{commit_msg}"')
    
    print("Pushing to remote...")
    run_command("git push")
    
    print("\nSuccess! Changes pushed to remote.")

if __name__ == "__main__":
    git_push()
