#!/usr/bin/env python3
"""Download MobileNet SSD model for person detection."""

import os
import urllib.request
import sys


def download_file(url, filename):
    """Download file with progress."""
    print(f"Downloading {filename}...")
    
    def progress_hook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        sys.stdout.write(f"\r{percent}%")
        sys.stdout.flush()
    
    urllib.request.urlretrieve(url, filename, progress_hook)
    print(f"\nDownloaded {filename}")


def main():
    # Model files
    prototxt_url = "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/MobileNetSSD_deploy.prototxt"
    caffemodel_url = "https://github.com/chuanqi305/MobileNet-SSD/raw/master/MobileNetSSD_deploy.caffemodel"
    
    prototxt_file = "MobileNetSSD_deploy.prototxt"
    caffemodel_file = "MobileNetSSD_deploy.caffemodel"
    
    # Check if files exist
    if os.path.exists(prototxt_file) and os.path.exists(caffemodel_file):
        print("Model files already exist!")
        return
    
    # Download
    try:
        if not os.path.exists(prototxt_file):
            download_file(prototxt_url, prototxt_file)
        
        if not os.path.exists(caffemodel_file):
            download_file(caffemodel_url, caffemodel_file)
        
        print("\nModel download complete!")
        print(f"Files: {prototxt_file}, {caffemodel_file}")
        
    except Exception as e:
        print(f"Error downloading model: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
