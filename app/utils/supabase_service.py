from app.utils.supabase_client import supabase
import os


def upload_file(file_path: str, bucket_name: str = "uploads") -> str | None:
    """Upload file lên Supabase Storage và trả về public URL."""
    file_name = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        res = supabase.storage.from_(bucket_name).upload(file_name, f)

    if res.status_code == 200:
        # Lấy public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        print(f"Uploaded {file_name} successfully!")
        print(f"Public URL: {public_url}")
        return public_url

    print("Upload failed:", res)
    return None
