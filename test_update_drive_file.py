#!/usr/bin/env python
"""
Test script for the new update_drive_file functionality.
This demonstrates how to use the new function to:
1. Move a file to a different folder
2. Rename a file
3. Update file metadata
4. Manage sharing permissions
"""

# Example usage (would be called via MCP):

# 1. Move a Google Doc from root to a specific folder
# update_drive_file(
#     user_google_email="user@example.com",
#     file_id="abc123",  # The Google Doc ID
#     add_parents="folder456"  # Target folder ID
#     remove_parents="root"  # Remove from root
# )

# 2. Rename a file and add description
# update_drive_file(
#     user_google_email="user@example.com",
#     file_id="abc123",
#     name="Q4 2024 Report - Final",
#     description="Quarterly financial report including revenue projections"
# )

# 3. Star a file and set sharing permissions
# update_drive_file(
#     user_google_email="user@example.com",
#     file_id="abc123",
#     starred=True,
#     writers_can_share=False,  # Only owner can share
#     copy_requires_writer_permission=True  # Restrict copying
# )

# 4. Add custom properties for organization
# update_drive_file(
#     user_google_email="user@example.com",
#     file_id="abc123",
#     properties={
#         "project": "Q4-2024",
#         "department": "Finance",
#         "status": "Final",
#         "review_date": "2024-12-15"
#     }
# )

# 5. Move to trash (soft delete)
# update_drive_file(
#     user_google_email="user@example.com",
#     file_id="abc123",
#     trashed=True
# )

# 6. Complex update - move, rename, and update metadata
# update_drive_file(
#     user_google_email="user@example.com",
#     file_id="abc123",
#     name="2024 Annual Report - Approved",
#     description="Board-approved annual report",
#     add_parents="approved_docs_folder",
#     remove_parents="drafts_folder",
#     starred=True,
#     properties={
#         "approval_date": "2024-12-20",
#         "approved_by": "Board of Directors"
#     }
# )

if __name__ == "__main__":
    print("This is a demonstration script showing update_drive_file usage.")
    print(
        "The function is available via the MCP server when running with --tools drive"
    )
    print("\nKey features of update_drive_file:")
    print("  • Move files between folders (add_parents/remove_parents)")
    print("  • Rename files and update descriptions")
    print("  • Star/unstar files")
    print("  • Manage trash status")
    print("  • Control sharing permissions")
    print("  • Add custom properties for metadata")
    print("\nThe function is in the 'extended' tool tier for Google Drive.")
