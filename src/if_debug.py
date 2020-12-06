import debugpy
from os import environ as env

def attach_debugger_if_dev():
    if "DEBUG" in env and env["DEBUG"] == "True":
        debugpy.listen(("0.0.0.0", 5678))
        print("⏳ VS Code debugger can now be attached ⏳", flush=True)
        debugpy.wait_for_client()
        print("🎉 VS Code debugger attached, enjoy debugging 🎉", flush=True)