import subprocess
import os

profile = subprocess.run(["powershell", "-NoProfile", "-NoLogo", "-Command", "echo $profile"], stdout=subprocess.PIPE, text=True).stdout.rstrip()
path = "/".join(__file__.replace("\\", "/").split("/")[:-1])

mode = "a"
prefix = "\n"

if not os.path.isfile(profile):
  mode = "w"
  prefix = ""

  os.makedirs(os.path.dirname(profile), exist_ok=True)

with open(profile, mode, encoding="utf-8") as f:
  f.write(prefix + "function diamond() { python \"%s\" $args }" % path)
