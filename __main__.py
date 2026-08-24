import os
import sys
import json
import zipfile
import subprocess

sub: str

while True:
  if os.path.isdir(sub := "src/main/java"):
    resp = "src/main/resources"
    break
  elif os.path.isdir(sub := "src"):
    resp = "resources"
    break
  else:
    path = os.path.dirname(os.getcwd())

    if path.replace("\\", "/").strip("/").count("/") <= 1:
      print("error: not in a project directory")
      sys.exit(1)

    os.chdir(path)

if len(sys.argv) == 1:
  task = 'build'
elif len(sys.argv) == 2 and sys.argv[1] in ('build', 'run'):
  task = sys.argv[1]
elif len(sys.argv) == 3 and sys.argv[1] == 'take':
  group, artifact, *version = sys.argv[2].split(":", 3)

  path = os.path.expanduser("~/.gradle/caches/modules-2/files-2.1/%s/%s" % (group, artifact))

  if not os.path.isdir(path):
    print("Library %s:%s not found" % (group, artifact))
    sys.exit(1)

  if version: path += "/" + version[0]
  else:       path += "/" + (version := os.listdir(path))[0]

  if not os.path.isdir(path):
    print("Library version %s:%s:%s not found" % (group, artifact, version[0]))
    sys.exit(1)

  entries = os.listdir(path)

  for id in entries:
    entryPath = path + "/" + id

    if os.path.isdir(entryPath):
      entryFiles = os.listdir(entryPath)

      for fn in entryFiles:
        if (
            fn.endswith(".jar") and
            not fn.endswith("-sources.jar") and
            not fn.endswith("-javadocs.jar") and
            not fn.endswith("-javadoc.jar")
        ):
          efPath = entryPath + "/" + fn

          with open(efPath, "rb") as src:
            with open(os.getcwd() + "/libs/%s" % fn, "wb") as dest:
              dest.write(src.read())

          print("Library %s:%s:%s copied into 'libs/%s'" % (group, artifact, version[0], fn))
          sys.exit(0)

  print("Failed to find library JAR")
  sys.exit(1)
else:
  print("usage: diamond [build | run]")
  print("       diamond take <(lib)>")

  sys.exit(2)

if not os.path.isfile("build.diamond"):
  print("error: no build.diamond file")
  sys.exit(4)

with open("build.diamond", "r", encoding='utf-8') as f:
  c = f.read()

lines = c.splitlines()
properties = {}

for line in lines:
  if line.strip() == '':
    continue

  key, _, value = line.partition("=")
  properties[key.strip()] = json.loads(value)

if 'no_version' in properties:
  if properties['no_version'] != 1:
    print("error: 'no_version' must be 1")
    sys.exit(7)

  if 'version' in properties:
    print("error: 'no_version' cannot be present along with 'version'")
    sys.exit(7)
elif 'version' not in properties:
  print("error: build properties don't include 'version'")
  sys.exit(6)

os.makedirs("build", exist_ok=True)
os.makedirs("build/libs", exist_ok=True)
os.makedirs("build/classes", exist_ok=True)
os.makedirs("build/generated", exist_ok=True)

def add(path: str, files: list, filechecker = lambda _: True) -> list:
  if os.path.isdir(path):
    inside = os.listdir(path)

    for fn in inside:
      add(path + "/" + fn, files)
  elif filechecker(path):
    files.append(path)

  return files

output = subprocess.run([
  "javac",
  "-source", "25",
  "-target", "25",
  "-cp", ";".join([os.path.abspath(l) for l in properties['libs']]) if 'libs' in properties else (os.getcwd() + "/libs/*"),
  "-sourcepath", os.getcwd() + "/%s/" % sub,
  "-encoding", "UTF8",
  "-d", os.getcwd() + "/build/classes",
  "-s", os.getcwd() + "/build/generated",
  "-deprecation",
  *add(sub, [], lambda path: path.endswith(".java"))
], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8').stdout

if output:
  print()
  print(output, end='')

for line in output.splitlines():
  if " error: " in line.split("  ")[0].split("\t")[0]:
    print("\n-----------------\nCOMPILATION ERROR\n")
    sys.exit(3)

jarfile = "build/libs/%s%s.jar" % (os.path.basename(os.getcwd()), ("-" + properties['version']) if 'version' in properties else "")

with open(jarfile, 'wb') as data:
  zip = zipfile.ZipFile(data, 'w', compression=zipfile.ZIP_DEFLATED)

  paths = add("build/classes", [])
  for path in paths:
    zip.write(path, path.removeprefix('build/classes/'))

  if 'main_class' in properties:
    zip.writestr("META-INF/MANIFEST.MF", f"""
Manifest-Version: 1.0
Main-Class: {properties['main_class']}

"""[1:-1])
  else:
    zip.writestr("META-INF/MANIFEST.MF", f"""
Manifest-Version: 1.0

"""[1:-1])

  paths = add(resp, [])
  for path in paths:
    zip.write(path, path.removeprefix(resp))

  zip.filename = "%s.jar" % os.path.basename(os.getcwd())
  zip.close()

#subprocess.run(["tar", "-cf", "../../" + jarfile, "*"], cwd=os.getcwd() + "/build/classes")

print("\n-------------\nBUILD SUCCESS\n")

if task == 'run':
  if 'main_class' not in properties:
    print("error: build properties don't include 'main_class'; cannot use run")
    sys.exit(5)

  subprocess.run([
    "java",
    "-Dfile.encoding=UTF-8",
    "-Dsun.stdout.encoding=UTF-8",
    "-Dsun.stderr.encoding=UTF-8",
    "-cp", "%s;%s" % (os.getcwd() + "/libs/*", jarfile),
    properties['main_class']
  ])
