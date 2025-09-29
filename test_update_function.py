#!/usr/bin/env python
"""
Direct test of update_drive_file function to verify OAuth scope fix
"""

import asyncio
from gdrive.drive_tools import update_drive_file
from auth.google_auth import get_google_service


async def test_update():
    """Test the update_drive_file function with all parameters"""

    # Test parameters
    file_id = "1MRfzYeo2HelMr7BTrso-GLCOwRVuDfF2nCdFQ1BhB4E"
    folder_id = "1l3PgdQZZ7pqIPlgd2Pu8hFOCtnwM9pVP"

    # Get the service
    service = await get_google_service(
        "rob.sherman@highway.ai",
        "drive",
        "drive_file",  # Using correct scope
    )

    # Call update_drive_file directly
    result = await update_drive_file(
        service=service,
        user_google_email="rob.sherman@highway.ai",
        file_id=file_id,
        name="Updated Test Document - OAuth Fixed",
        description="Testing update_drive_file with all parameters after fixing OAuth scope issue",
        add_parents=folder_id,
        starred=True,
        writers_can_share=True,
        copy_requires_writer_permission=False,
        properties={
            "test_key": "test_value",
            "updated_by": "mcp_server",
            "update_timestamp": "2025-01-29",
        },
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(test_update())
