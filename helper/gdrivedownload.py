import os
import gdown


def download_gdrive_video(
    url: str,
    output_dir: str = "downloads",
    filename: str | None = None
):
    """
    Download a video/file from Google Drive using gdown.

    Args:
        url: Google Drive share URL
        output_dir: Folder to save file
        filename: Optional custom filename
    """

    os.makedirs(output_dir, exist_ok=True)

    # If filename not provided,
    # gdown will use original file name
    if filename:
        output_path = os.path.join(output_dir, filename)
    else:
        output_path = output_dir

    print(f"\nDownloading from Google Drive...\n")

    gdown.download(
        url=url,
        output=output_path,
        quiet=False,
        fuzzy=True  # Helps parse different drive URL formats
    )

    print("\nDownload complete.\n")


# Example usage
download_gdrive_video(
    url="https://drive.google.com/file/d/FILE_ID/view?usp=sharing"
)