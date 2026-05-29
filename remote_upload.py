import os
import paramiko

# === USER SETTINGS ===
SETTINGS = {
    "hostname": "newtons-cradle-2023-pi.local",
    "username": "pi",
    "password": "dpea7266!",
    "remote_folder": "/home/pi/newtons-cradle-2026",
    "file_types": [".py", ".txt", ".ui", ".kv"],
    "include_subfolders": True
}

# === File Upload ===
def get_local_files(file_types=None, include_subfolders=False):
    file_list = []

    if include_subfolders:
        for root, _, files in os.walk("."):
            for f in files:
                if not file_types or os.path.splitext(f)[1] in file_types:
                    file_list.append(os.path.join(root, f))
    else:
        for f in os.listdir("."):
            full_path = os.path.join(".", f)
            if os.path.isfile(full_path):
                if not file_types or os.path.splitext(f)[1] in file_types:
                    file_list.append(full_path)

    return file_list

def upload_files(sftp, local_files, remote_folder):
    try:
        sftp.chdir(remote_folder)
    except IOError:
        sftp.mkdir(remote_folder)
        sftp.chdir(remote_folder)

    for local_path in local_files:
        filename = os.path.basename(local_path)
        remote_path = os.path.join(remote_folder, filename)
        print(f"Uploading {filename}...")
        sftp.put(local_path, remote_path)
    print("✅ Upload complete.")


# === Main Logic ===
def main():
    config = SETTINGS
    files_to_upload = get_local_files(config["file_types"], config["include_subfolders"])

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"Connecting to {config['hostname']}...")
        ssh.connect(config["hostname"], username=config["username"], password=config["password"])
        sftp = ssh.open_sftp()

        upload_files(sftp, files_to_upload, config["remote_folder"])

        sftp.close()
        ssh.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()