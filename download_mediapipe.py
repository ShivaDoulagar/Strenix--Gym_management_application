import os
import requests
from urllib.parse import urljoin

# Base URL for MediaPipe files
BASE_URL = "https://cdn.jsdelivr.net/npm/@mediapipe/pose@0.5.1675469404/"
FILES = [
    "pose.js",
    "pose_solution_packed_assets_loader.js",
    "pose_solution_wasm_bin.js",
    "pose_solution_wasm_bin.wasm",
    "pose_solution_simd_wasm_bin.js",
    "pose_solution_simd_wasm_bin.wasm",
    "pose_solution_packed_assets.data",
    "pose_web.binarypb",
    "pose_landmark_heavy.tflite"
]

# Create directory if it doesn't exist
os.makedirs("static/mediapipe", exist_ok=True)

def download_file(url, filepath):
    print(f"Downloading {os.path.basename(filepath)}...")
    try:
        response = requests.get(url, allow_redirects=True)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"Successfully downloaded {os.path.basename(filepath)}")
            return True
        else:
            print(f"Failed to download {os.path.basename(filepath)} - Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading {os.path.basename(filepath)}: {str(e)}")
        return False

# Download each file from the base URL
for file in FILES:
    url = urljoin(BASE_URL, file)
    filepath = os.path.join("static/mediapipe", file)
    download_file(url, filepath)

# Download camera_utils and drawing_utils from their respective packages
utils_files = {
    "camera_utils.js": "https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils@0.3/camera_utils.js",
    "drawing_utils.js": "https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils@0.3/drawing_utils.js"
}

for filename, url in utils_files.items():
    filepath = os.path.join("static/mediapipe", filename)
    download_file(url, filepath)

print("Download process completed!") 