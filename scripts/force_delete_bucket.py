#!/usr/bin/env python3
"""
Force delete MinIO bucket including all versions.

Usage:
    python scripts/force_delete_bucket.py bronze
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.minio_client import MinIOClient


def force_delete_bucket(bucket_name: str):
    """
    Force delete a bucket and all its contents including versions.

    Args:
        bucket_name: Name of bucket to delete
    """
    client = MinIOClient()

    print(f"Force deleting bucket: {bucket_name}")

    # Delete all object versions
    try:
        versions = client.s3_client.list_object_versions(Bucket=bucket_name)

        total_deleted = 0

        # Delete versions
        if 'Versions' in versions:
            print(f"Found {len(versions['Versions'])} versions")
            for version in versions['Versions']:
                try:
                    client.s3_client.delete_object(
                        Bucket=bucket_name,
                        Key=version['Key'],
                        VersionId=version['VersionId']
                    )
                    total_deleted += 1
                    print(f"  ✓ Deleted version: {version['Key']} (v{version['VersionId'][:8]}...)")
                except Exception as e:
                    print(f"  ✗ Error deleting {version['Key']}: {e}")

        # Delete delete markers
        if 'DeleteMarkers' in versions:
            print(f"Found {len(versions['DeleteMarkers'])} delete markers")
            for marker in versions['DeleteMarkers']:
                try:
                    client.s3_client.delete_object(
                        Bucket=bucket_name,
                        Key=marker['Key'],
                        VersionId=marker['VersionId']
                    )
                    total_deleted += 1
                    print(f"  ✓ Deleted marker: {marker['Key']} (v{marker['VersionId'][:8]}...)")
                except Exception as e:
                    print(f"  ✗ Error deleting marker {marker['Key']}: {e}")

        print(f"\nTotal deleted: {total_deleted}")

    except Exception as e:
        print(f"Error listing versions: {e}")

    # Delete current objects (non-versioned)
    try:
        response = client.s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            print(f"\nFound {len(response['Contents'])} current objects")
            for obj in response['Contents']:
                try:
                    client.s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
                    print(f"  ✓ Deleted: {obj['Key']}")
                except Exception as e:
                    print(f"  ✗ Error deleting {obj['Key']}: {e}")
    except Exception as e:
        print(f"Error listing objects: {e}")

    # Finally, delete the bucket
    try:
        client.s3_client.delete_bucket(Bucket=bucket_name)
        print(f"\n✅ Bucket '{bucket_name}' deleted successfully")
    except Exception as e:
        print(f"\n❌ Failed to delete bucket: {e}")
        print("\nTry using MinIO Console:")
        print("  URL: http://localhost:9001")
        print("  User: minioadmin")
        print("  Pass: minioadmin")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Force delete MinIO bucket")
    parser.add_argument("bucket", help="Bucket name to delete")

    args = parser.parse_args()
    force_delete_bucket(args.bucket)
