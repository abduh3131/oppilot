import os, sys, subprocess, time, shutil, json, re, textwrap

HOME = os.path.expanduser("~")
OP = os.path.join(HOME, "openpilot")
ADAPT = os.path.join(HOME, "dev", "op-jetson-adapters")
PYBIN = os.path.join(OP, ".venv", "bin", "python")
RUN_ALL = os.path.join(ADAPT, "tools", "run_all.sh")

def run(cmd, check=True, shell=False, env=None):
    print(">>", cmd if isinstance(cmd,str) else " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, shell=shell, env=env)

def ensure_packages():
    run(["sudo","apt","update"])
    run(["sudo","apt","install","-y","git","python3-venv","python3-pip","build-essential","python3-dev","libzmq3-dev","capnproto","libcapnp-dev","v4l-utils"])

def ensure_openpilot():
    if not os.path.isdir(OP):
        run(["git","clone","--recurse-submodules","https://github.com/commaai/openpilot.git", OP])
    # official setup (creates .venv and builds cereal/capnp etc)
    run(["bash","-lc", f"cd {OP} && chmod +x tools/op.sh && tools/op.sh setup"])

def pip_install_into_op(*pkgs):
    run([PYBIN,"-m","pip","install","-U","pip","wheel","setuptools"])
    if pkgs:
        run([PYBIN,"-m","pip","install","--only-binary=:all:"] + list(pkgs))

def ensure_adapters():
    if not os.path.isdir(ADAPT):
        print("\nAdapters repo not found at", ADAPT)
        win_guess = "/mnt/c/Users/Abduh/Downloads/astratest/op-jetson-adapters"
        src = input(f"Enter path to your adapters (or press Enter to copy from {win_guess} if it exists): ").strip() or win_guess
        if os.path.isdir(src):
            os.makedirs(os.path.dirname(ADAPT), exist_ok=True)
            run(["cp","-r",src,ADAPT])
        else:
            print(f"Path not found: {src}")
            sys.exit(1)

    # write idempotent run_all.sh (uses openpilot Python + sets PYTHONPATH)
    os.makedirs(os.path.join(ADAPT,"tools"), exist_ok
