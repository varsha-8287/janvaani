import os
import glob
import zipfile
import subprocess
import shutil

BASE_APK = r"apps\mobile\android\app\build\outputs\apk\release\app-release.apk"
DIST_HBC_DIR = r"apps\mobile\dist\_expo\static\js\android"
TEMP_APK = r"apps\mobile\temp_unsigned.apk"
ALIGNED_APK = r"apps\mobile\janvaani-final.apk"
BUILD_TOOLS_DIR = r"C:\Users\varsh\AppData\Local\Android\Sdk\build-tools\36.0.0"
ZIPALIGN = os.path.join(BUILD_TOOLS_DIR, "zipalign.exe")
APKSIGNER = os.path.join(BUILD_TOOLS_DIR, "apksigner.bat")
KEYSTORE = r"C:\Users\varsh\.android\debug.keystore"

# 1. Find the exported bundle
hbc_files = glob.glob(os.path.join(DIST_HBC_DIR, "*.hbc"))
if not hbc_files:
    raise FileNotFoundError("No .hbc bundle found in " + DIST_HBC_DIR)
bundle_file = hbc_files[0]
print(f"Using bundle: {bundle_file} ({os.path.getsize(bundle_file)} bytes)")

# 2. Re-pack APK replacing assets/index.android.bundle and removing META-INF
print("Repacking APK...")
with zipfile.ZipFile(BASE_APK, "r") as zin:
    with zipfile.ZipFile(TEMP_APK, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            # Skip old bundle and old signature files
            if item.filename == "assets/index.android.bundle":
                continue
            if item.filename.startswith("META-INF/"):
                continue
            data = zin.read(item.filename)
            zout.writestr(item, data)
        
        # Add updated bundle
        with open(bundle_file, "rb") as bf:
            bundle_data = bf.read()
        zout.writestr("assets/index.android.bundle", bundle_data)

print(f"Temporary repacked APK created: {TEMP_APK} ({os.path.getsize(TEMP_APK)} bytes)")

# 3. Zipalign
if os.path.exists(ALIGNED_APK):
    os.remove(ALIGNED_APK)

print("Running zipalign...")
res = subprocess.run([ZIPALIGN, "-p", "-f", "4", TEMP_APK, ALIGNED_APK], capture_output=True, text=True)
if res.returncode != 0:
    print("Zipalign error:", res.stderr)
    raise RuntimeError("zipalign failed")
print("Zipalign successful!")

# 4. Sign with apksigner
print("Signing APK with debug keystore...")
sign_cmd = [
    APKSIGNER, "sign",
    "--ks", KEYSTORE,
    "--ks-pass", "pass:android",
    "--key-pass", "pass:android",
    "--ks-key-alias", "androiddebugkey",
    ALIGNED_APK
]
res = subprocess.run(sign_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print("Sign error:", res.stderr, res.stdout)
    raise RuntimeError("apksigner failed")
print("APK signed successfully!")

# 5. Verify signature
res = subprocess.run([APKSIGNER, "verify", ALIGNED_APK], capture_output=True, text=True)
if res.returncode != 0:
    print("Verify error:", res.stderr)
    raise RuntimeError("Verification failed")
print("Verified APK signature scheme successfully!")

# Cleanup temp
if os.path.exists(TEMP_APK):
    os.remove(TEMP_APK)

print(f"Final APK ready: {ALIGNED_APK} ({os.path.getsize(ALIGNED_APK)} bytes)")

