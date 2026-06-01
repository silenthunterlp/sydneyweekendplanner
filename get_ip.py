import subprocess

result = subprocess.run(["curl", "ifconfig.io"], capture_output=True, text=True)
print("Your public IP:", result.stdout.strip())
