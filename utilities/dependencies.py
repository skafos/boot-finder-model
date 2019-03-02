"""Module to help ensure that dependencies are installed correctly."""
import os
import sys
from subprocess import check_output


def _try_install(timeout):
    try:
        # try installing, give it 3 mins to try and install 
        output = check_output(["pip", "install", "-r", "/home/jovyan/requirements.txt"], timeout=timeout)
        
    except Exception as e:
        print(f"Exception encountered while installing dependencies: {e}", flush=True)
        raise e

def install(timeout=300, retries=2):
    # Install all dependencies inside requirements.txt
    print("Checking and installing required python dependencies in requirements.txt", flush=True)
    try:
        _try_install(timeout)
        # Load pkg directly from site-packages (avoid restart kernel)  
        if not os.path.exists(".local/site-packages/"):
            os.makedirs(".local/site-packages/")
        sys.path.append(".local/site-packages/")
    except Exception as e:
        raise e
    print("Done", flush=True)
