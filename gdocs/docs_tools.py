"""
Google Docs MCP Tools

This module provides MCP tools for interacting with Google Docs API and managing Google Docs via Drive.
"""
import logging
import asyncio
import io

from googleapiclient.http import MediaIoBaseDownload

# Auth & server utilities
from auth.service_decorator import require_google_service, require_multiple_services
from core.utils import extract_office_xml_text, handle_http_errors
from core.server import server
from core.comments import create_comment_tools

# Import helper functions for document operations
from gdocs.docs_helpers import (
    build_text_style,
    create_insert_text_request,
    create_delete_range_request,
    create_format_text_request,
    create_find_replace_request,
    create_insert_table_request,
    create_insert_page_break_request,
    create_insert_image_request,
    create_bullet_list_request,
    validate_operation,
    extract_document_text_simple,
    calculate_text_indices,
)

logger = logging.getLogger(__name__)

@server.tool()
@handle_http_errors("search_docs", is_read_only=True, service_type="docs")
@require_google_service("drive", "drive_read")
async def search_docs(
    service,
    user_google_email: str,
    query: str,
    page_size: int = 10,
) -> str:
    """
    Searches for Google Docs by name using Drive API (mimeType filter).

    Returns:
        str: A formatted list of Google Docs matching the search query.
    """
    logger.info(f"[search_docs] Email={user_google_email}, Query='{query}'")

    escaped_query = query.replace("'", "\\'")

    response = await asyncio.to_thread(
        service.files().list(
            q=f"name contains '{escaped_query}' and mimeType='application/vnd.google-apps.document' and trashed=false",
            pageSize=page_size,
            fields="files(id, name, createdTime, modifiedTime, webViewLink)"
        ).execute
    )
    files = response.get('files', [])
    if not files:
        return f"No Google Docs found matching '{query}'."

    output = [f"Found {len(files)} Google Docs matching '{query}':"]
    for f in files:
        output.append(
            f"- {f['name']} (ID: {f['id']}) Modified: {f.get('modifiedTime')} Link: {f.get('webViewLink')}"
        )
    return "\n".join(output)

@server.tool()
@handle_http_errors("get_doc_content", is_read_only=True, service_type="docs")
@require_multiple_services([
    {"service_type": "drive", "scopes": "drive_read", "param_name": "drive_service"},
    {"service_type": "docs", "scopes": "docs_read", "param_name": "docs_service"}
])
async def get_doc_content(
    drive_service,
    docs_service,
    user_google_email: str,
    document_id: str,
) -> str:
    """
    Retrieves content of a Google Doc or a Drive file (like .docx) identified by document_id.
    - Native Google Docs: Fetches content via Docs API.
    - Office files (.docx, etc.) stored in Drive: Downloads via Drive API and extracts text.

    Returns:
        str: The document content with metadata header.
    """
    logger.info(f"[get_doc_content] Invoked. Document/File ID: '{document_id}' for user '{user_google_email}'")

    # Step 2: Get file metadata from Drive
    file_metadata = await asyncio.to_thread(
        drive_service.files().get(
            fileId=document_id, fields="id, name, mimeType, webViewLink"
        ).execute
    )
    mime_type = file_metadata.get("mimeType", "")
    file_name = file_metadata.get("name", "Unknown File")
    web_view_link = file_metadata.get("webViewLink", "#")

    logger.info(f"[get_doc_content] File '{file_name}' (ID: {document_id}) has mimeType: '{mime_type}'")

    body_text = "" # Initialize body_text

    # Step 3: Process based on mimeType
    if mime_type == "application/vnd.google-apps.document":
        logger.info("[get_doc_content] Processing as native Google Doc.")
        doc_data = await asyncio.to_thread(
            docs_service.documents().get(
                documentId=document_id,
                includeTabsContent=True
            ).execute
        )
        # Tab header format constant
        TAB_HEADER_FORMAT = "\n--- TAB: {tab_name} ---\n"

        def extract_text_from_elements(elements, tab_name=None, depth=0):
            """Extract text from document elements (paragraphs, tables, etc.)"""
            # Prevent infinite recursion by limiting depth
            if depth > 5:
                return ""
            text_lines = []
            if tab_name:
                text_lines.append(TAB_HEADER_FORMAT.format(tab_name=tab_name))

            for element in elements:
                if 'paragraph' in element:
                    paragraph = element.get('paragraph', {})
                    para_elements = paragraph.get('elements', [])
                    current_line_text = ""
                    for pe in para_elements:
                        text_run = pe.get('textRun', {})
                        if text_run and 'content' in text_run:
                            current_line_text += text_run['content']
                    if current_line_text.strip():
                        text_lines.append(current_line_text)
                elif 'table' in element:
                    # Handle table content
                    table = element.get('table', {})
                    table_rows = table.get('tableRows', [])
                    for row in table_rows:
                        row_cells = row.get('tableCells', [])
                        for cell in row_cells:
                            cell_content = cell.get('content', [])
                            cell_text = extract_text_from_elements(cell_content, depth=depth + 1)
                            if cell_text.strip():
                                text_lines.append(cell_text)
            return "".join(text_lines)

        def process_tab_hierarchy(tab, level=0):
            """Process a tab and its nested child tabs recursively"""
            tab_text = ""

            if 'documentTab' in tab:
                tab_title = tab.get('documentTab', {}).get('title', 'Untitled Tab')
                # Add indentation for nested tabs to show hierarchy
                if level > 0:
                    tab_title = "    " * level + tab_title
                tab_body = tab.get('documentTab', {}).get('body', {}).get('content', [])
                tab_text += extract_text_from_elements(tab_body, tab_title)

            # Process child tabs (nested tabs)
            child_tabs = tab.get('childTabs', [])
            for child_tab in child_tabs:
                tab_text += process_tab_hierarchy(child_tab, level + 1)

            return tab_text

        processed_text_lines = []

        # Process main document body
        body_elements = doc_data.get('body', {}).get('content', [])
        main_content = extract_text_from_elements(body_elements)
        if main_content.strip():
            processed_text_lines.append(main_content)

        # Process all tabs
        tabs = doc_data.get('tabs', [])
        for tab in tabs:
            tab_content = process_tab_hierarchy(tab)
            if tab_content.strip():
                processed_text_lines.append(tab_content)

        body_text = "".join(processed_text_lines)
    else:
        logger.info(f"[get_doc_content] Processing as Drive file (e.g., .docx, other). MimeType: {mime_type}")

        export_mime_type_map = {
                # Example: "application/vnd.google-apps.spreadsheet"z: "text/csv",
                # Native GSuite types that are not Docs would go here if this function
                # was intended to export them. For .docx, direct download is used.
        }
        effective_export_mime = export_mime_type_map.get(mime_type)

        request_obj = (
            drive_service.files().export_media(fileId=document_id, mimeType=effective_export_mime)
            if effective_export_mime
            else drive_service.files().get_media(fileId=document_id)
        )

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request_obj)
        loop = asyncio.get_event_loop()
        done = False
        while not done:
            status, done = await loop.run_in_executor(None, downloader.next_chunk)

        file_content_bytes = fh.getvalue()

        office_text = extract_office_xml_text(file_content_bytes, mime_type)
        if office_text:
            body_text = office_text
        else:
            try:
                body_text = file_content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                body_text = (
                    f"[Binary or unsupported text encoding for mimeType '{mime_type}' - "
                    f"{len(file_content_bytes)} bytes]"
                )

    header = (
        f'File: "{file_name}" (ID: {document_id}, Type: {mime_type})\n'
        f'Link: {web_view_link}\n\n--- CONTENT ---\n'
    )
    return header + body_text

@server.tool()
@handle_http_errors("list_docs_in_folder", is_read_only=True, service_type="docs")
@require_google_service("drive", "drive_read")
async def list_docs_in_folder(
    service,
    user_google_email: str,
    folder_id: str = 'root',
    page_size: int = 100
) -> str:
    """
    Lists Google Docs within a specific Drive folder.

    Returns:
        str: A formatted list of Google Docs in the specified folder.
    """
    logger.info(f"[list_docs_in_folder] Invoked. Email: '{user_google_email}', Folder ID: '{folder_id}'")

    rsp = await asyncio.to_thread(
        service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false",
            pageSize=page_size,
            fields="files(id, name, modifiedTime, webViewLink)"
        ).execute
    )
    items = rsp.get('files', [])
    if not items:
        return f"No Google Docs found in folder '{folder_id}'."
    out = [f"Found {len(items)} Docs in folder '{folder_id}':"]
    for f in items:
        out.append(f"- {f['name']} (ID: {f['id']}) Modified: {f.get('modifiedTime')} Link: {f.get('webViewLink')}")
    return "\n".join(out)

@server.tool()
@handle_http_errors("create_doc", service_type="docs")
@require_google_service("docs", "docs_write")
async def create_doc(
    service,
    user_google_email: str,
    title: str,
    content: str = '',
) -> str:
    """
    Creates a new Google Doc and optionally inserts initial content.

    Returns:
        str: Confirmation message with document ID and link.
    """
    logger.info(f"[create_doc] Invoked. Email: '{user_google_email}', Title='{title}'")

    doc = await asyncio.to_thread(service.documents().create(body={'title': title}).execute)
    doc_id = doc.get('documentId')
    if content:
        requests = [{'insertText': {'location': {'index': 1}, 'text': content}}]
        await asyncio.to_thread(service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute)
    link = f"https://docs.google.com/document/d/{doc_id}/edit"
    msg = f"Created Google Doc '{title}' (ID: {doc_id}) for {user_google_email}. Link: {link}"
    logger.info(f"Successfully created Google Doc '{title}' (ID: {doc_id}) for {user_google_email}. Link: {link}")
    return msg


@server.tool()
@handle_http_errors("update_doc_text", service_type="docs")
@require_google_service("docs", "docs_write")
async def update_doc_text(
    service,
    user_google_email: str,
    document_id: str,
    text: str,
    start_index: int,
    end_index: int = None,
) -> str:
    """
    Updates text at a specific location in a Google Doc.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        text: New text to insert or replace with
        start_index: Start position for text update (0-based)
        end_index: End position for text replacement (if not provided, text is inserted)
    
    Returns:
        str: Confirmation message with update details
    """
    logger.info(f"[update_doc_text] Doc={document_id}, start={start_index}, end={end_index}")
    
    requests = []
    
    if end_index is not None and end_index > start_index:
        # Replace text: delete old text, then insert new text
        requests.extend([
            create_delete_range_request(start_index, end_index),
            create_insert_text_request(start_index, text)
        ])
        operation = f"Replaced text from index {start_index} to {end_index}"
    else:
        # Insert text at position
        requests.append(create_insert_text_request(start_index, text))
        operation = f"Inserted text at index {start_index}"
    
    await asyncio.to_thread(
        service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute
    )
    
    link = f"https://docs.google.com/document/d/{document_id}/edit"
    return f"{operation} in document {document_id}. Text length: {len(text)} characters. Link: {link}"

@server.tool()
@handle_http_errors("find_and_replace_doc", service_type="docs")
@require_google_service("docs", "docs_write")
async def find_and_replace_doc(
    service,
    user_google_email: str,
    document_id: str,
    find_text: str,
    replace_text: str,
    match_case: bool = False,
) -> str:
    """
    Finds and replaces text throughout a Google Doc.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        find_text: Text to search for
        replace_text: Text to replace with
        match_case: Whether to match case exactly
    
    Returns:
        str: Confirmation message with replacement count
    """
    logger.info(f"[find_and_replace_doc] Doc={document_id}, find='{find_text}', replace='{replace_text}'")
    
    requests = [create_find_replace_request(find_text, replace_text, match_case)]
    
    result = await asyncio.to_thread(
        service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute
    )
    
    # Extract number of replacements from response
    replacements = 0
    if 'replies' in result and result['replies']:
        reply = result['replies'][0]
        if 'replaceAllText' in reply:
            replacements = reply['replaceAllText'].get('occurrencesChanged', 0)
    
    link = f"https://docs.google.com/document/d/{document_id}/edit"
    return f"Replaced {replacements} occurrence(s) of '{find_text}' with '{replace_text}' in document {document_id}. Link: {link}"

@server.tool()
@handle_http_errors("format_doc_text", service_type="docs")
@require_google_service("docs", "docs_write")
async def format_doc_text(
    service,
    user_google_email: str,
    document_id: str,
    start_index: int,
    end_index: int,
    bold: bool = None,
    italic: bool = None,
    underline: bool = None,
    font_size: int = None,
    font_family: str = None,
) -> str:
    """
    Applies text formatting to a specific range in a Google Doc.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        start_index: Start position of text to format (0-based)
        end_index: End position of text to format
        bold: Whether to make text bold (True/False/None to leave unchanged)
        italic: Whether to make text italic (True/False/None to leave unchanged)
        underline: Whether to underline text (True/False/None to leave unchanged)
        font_size: Font size in points
        font_family: Font family name (e.g., "Arial", "Times New Roman")
    
    Returns:
        str: Confirmation message with formatting details
    """
    logger.info(f"[format_doc_text] Doc={document_id}, range={start_index}-{end_index}")
    
    format_request = create_format_text_request(
        start_index, end_index, bold, italic, underline, font_size, font_family
    )
    
    if not format_request:
        return "No formatting changes specified. Please provide at least one formatting option."
    
    requests = [format_request]
    
    await asyncio.to_thread(
        service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute
    )
    
    # Build format changes description
    format_changes = []
    if bold is not None:
        format_changes.append(f"bold: {bold}")
    if italic is not None:
        format_changes.append(f"italic: {italic}")
    if underline is not None:
        format_changes.append(f"underline: {underline}")
    if font_size is not None:
        format_changes.append(f"font size: {font_size}pt")
    if font_family is not None:
        format_changes.append(f"font family: {font_family}")
    
    changes_str = ', '.join(format_changes)
    link = f"https://docs.google.com/document/d/{document_id}/edit"
    return f"Applied formatting ({changes_str}) to text from index {start_index} to {end_index} in document {document_id}. Link: {link}"

@server.tool()
@handle_http_errors("insert_doc_elements", service_type="docs")
@require_google_service("docs", "docs_write")
async def insert_doc_elements(
    service,
    user_google_email: str,
    document_id: str,
    element_type: str,
    index: int,
    rows: int = None,
    columns: int = None,
    list_type: str = None,
    text: str = None,
) -> str:
    """
    Inserts structural elements like tables, lists, or page breaks into a Google Doc.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        element_type: Type of element to insert ("table", "list", "page_break")
        index: Position to insert element (0-based)
        rows: Number of rows for table (required for table)
        columns: Number of columns for table (required for table)
        list_type: Type of list ("UNORDERED", "ORDERED") (required for list)
        text: Initial text content for list items
    
    Returns:
        str: Confirmation message with insertion details
    """
    logger.info(f"[insert_doc_elements] Doc={document_id}, type={element_type}, index={index}")
    
    requests = []
    
    if element_type == "table":
        if not rows or not columns:
            return "Error: 'rows' and 'columns' parameters are required for table insertion."
        
        requests.append(create_insert_table_request(index, rows, columns))
        description = f"table ({rows}x{columns})"
        
    elif element_type == "list":
        if not list_type:
            return "Error: 'list_type' parameter is required for list insertion ('UNORDERED' or 'ORDERED')."
        
        if not text:
            text = "List item"
        
        # Insert text first, then create list
        requests.extend([
            create_insert_text_request(index, text + '\n'),
            create_bullet_list_request(index, index + len(text), list_type)
        ])
        description = f"{list_type.lower()} list"
        
    elif element_type == "page_break":
        requests.append(create_insert_page_break_request(index))
        description = "page break"
        
    else:
        return f"Error: Unsupported element type '{element_type}'. Supported types: 'table', 'list', 'page_break'."
    
    await asyncio.to_thread(
        service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute
    )
    
    link = f"https://docs.google.com/document/d/{document_id}/edit"
    return f"Inserted {description} at index {index} in document {document_id}. Link: {link}"

@server.tool()
@handle_http_errors("insert_doc_image", service_type="docs")
@require_multiple_services([
    {"service_type": "docs", "scopes": "docs_write", "param_name": "docs_service"},
    {"service_type": "drive", "scopes": "drive_read", "param_name": "drive_service"}
])
async def insert_doc_image(
    docs_service,
    drive_service,
    user_google_email: str,
    document_id: str,
    image_source: str,
    index: int,
    width: int = None,
    height: int = None,
) -> str:
    """
    Inserts an image into a Google Doc from Drive or a URL.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        image_source: Drive file ID or public image URL
        index: Position to insert image (0-based)
        width: Image width in points (optional)
        height: Image height in points (optional)
    
    Returns:
        str: Confirmation message with insertion details
    """
    logger.info(f"[insert_doc_image] Doc={document_id}, source={image_source}, index={index}")
    
    # Determine if source is a Drive file ID or URL
    is_drive_file = not (image_source.startswith('http://') or image_source.startswith('https://'))
    
    if is_drive_file:
        # Verify Drive file exists and get metadata
        try:
            file_metadata = await asyncio.to_thread(
                drive_service.files().get(
                    fileId=image_source, 
                    fields="id, name, mimeType"
                ).execute
            )
            mime_type = file_metadata.get('mimeType', '')
            if not mime_type.startswith('image/'):
                return f"Error: File {image_source} is not an image (MIME type: {mime_type})."
            
            image_uri = f"https://drive.google.com/uc?id={image_source}"
            source_description = f"Drive file {file_metadata.get('name', image_source)}"
        except Exception as e:
            return f"Error: Could not access Drive file {image_source}: {str(e)}"
    else:
        image_uri = image_source
        source_description = "URL image"
    
    # Use helper function to create request
    request = create_insert_image_request(index, image_uri, width, height)
    requests = [request]
    
    await asyncio.to_thread(
        docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute
    )
    
    size_info = ""
    if width or height:
        size_info = f" (size: {width or 'auto'}x{height or 'auto'} points)"
    
    link = f"https://docs.google.com/document/d/{document_id}/edit"
    return f"Inserted {source_description}{size_info} at index {index} in document {document_id}. Link: {link}"

@server.tool()
@handle_http_errors("insert_doc_image_from_drive", service_type="docs")
@require_multiple_services([
    {"service_type": "drive", "scopes": "drive_read", "param_name": "drive_service"},
    {"service_type": "docs", "scopes": "docs_write", "param_name": "docs_service"}
])
async def insert_doc_image_from_drive(
    drive_service,
    docs_service,
    user_google_email: str,
    document_id: str,
    drive_file_name: str,
    index: int,
    width: int = None,
    height: int = None,
) -> str:
    """
    Searches for an image in Google Drive by name and inserts it into a Google Doc.
    Checks permissions first and provides helpful error messages if the image isn't publicly shared.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        drive_file_name: Name of the image file in Google Drive (e.g., "product_roadmap_2025.png")
        index: Position to insert image (0-based)
        width: Image width in points (optional)
        height: Image height in points (optional)
    
    Returns:
        str: Confirmation message with insertion details or error with instructions
    """
    logger.info(f"[insert_doc_image_from_drive] Doc={document_id}, file={drive_file_name}, index={index}")
    
    # Build search query for the specific file name
    escaped_name = drive_file_name.replace("'", "\\'")
    search_query = f"name = '{escaped_name}'"
    
    # Search for the file in Drive with permission information
    list_params = {
        "q": search_query,
        "pageSize": 5,
        "fields": "files(id, name, mimeType, webViewLink, permissions, shared)",
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }
    
    search_results = await asyncio.to_thread(
        drive_service.files().list(**list_params).execute
    )
    
    files = search_results.get('files', [])
    if not files:
        return f"❌ Error: File '{drive_file_name}' not found in Google Drive"
    
    # Use the first matching file
    file_info = files[0]
    file_id = file_info.get('id')
    file_name = file_info.get('name')
    mime_type = file_info.get('mimeType', '')
    
    # Check if it's an image file
    if not mime_type.startswith('image/'):
        logger.warning(f"File '{drive_file_name}' has MIME type '{mime_type}' which may not be an image")
    
    # Check permissions to see if file has "anyone with link" permission
    permissions = file_info.get('permissions', [])
    has_public_link = any(
        p.get('type') == 'anyone' and p.get('role') in ['reader', 'writer', 'commenter']
        for p in permissions
    )
    
    if not has_public_link:
        # File is not publicly accessible - provide helpful error message
        error_msg = [
            f"❌ **Permission Error**: Cannot insert image '{file_name}' into Google Doc",
            "",
            "**Issue**: The image is not shared with 'Anyone with the link'",
            "The Google Docs API requires images to be publicly accessible to insert them.",
            "",
            "**How to fix this:**",
            "1. Go to your Google Drive: https://drive.google.com",
            f"2. Find the file '{file_name}'",
            "3. Right-click on the file and select 'Share'",
            "4. Under 'General access', change from 'Restricted' to 'Anyone with the link'",
            "5. Set the permission to 'Viewer'",
            "6. Click 'Done'",
            "",
            f"**Direct link to file**: https://drive.google.com/file/d/{file_id}/view",
            "",
            "After changing the permissions, try inserting the image again."
        ]
        return "\n".join(error_msg)
    
    # File has public access - proceed with insertion
    # Use the correct Drive URL format for publicly shared images
    image_uri = f"https://drive.google.com/uc?export=view&id={file_id}"
    
    # Use helper function to create request
    request = create_insert_image_request(index, image_uri, width, height)
    requests = [request]
    
    try:
        await asyncio.to_thread(
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute
        )
        
        size_info = ""
        if width or height:
            size_info = f" (size: {width or 'auto'}x{height or 'auto'} points)"
        
        link = f"https://docs.google.com/document/d/{document_id}/edit"
        return f"✅ Successfully inserted Drive image '{file_name}' (ID: {file_id}){size_info} at index {index} in document {document_id}. Link: {link}"
        
    except Exception as e:
        error_str = str(e)
        if "publicly accessible" in error_str or "forbidden" in error_str.lower():
            # Even though we checked permissions, the API might still reject it
            # This can happen if the sharing was just changed
            error_msg = [
                f"❌ **API Error**: Failed to insert image '{file_name}'",
                "",
                f"Error details: {error_str}",
                "",
                "**Possible causes:**",
                "1. The sharing permissions were recently changed and haven't propagated yet",
                "2. The file is in a shared drive with restricted access",
                "3. The image format is not supported",
                "",
                "**Try these solutions:**",
                "1. Wait a few seconds and try again",
                "2. Verify the file shows 'Anyone with the link' in Google Drive sharing settings",
                f"3. Try using the direct URL with insert_doc_image_url: https://drive.google.com/uc?export=view&id={file_id}",
                "",
                f"**File link**: https://drive.google.com/file/d/{file_id}/view"
            ]
            return "\n".join(error_msg)
        else:
            # Some other error occurred
            return f"❌ Error inserting image '{file_name}': {e}"

@server.tool()
@handle_http_errors("insert_doc_image_url", service_type="docs")
@require_google_service("docs", "docs_write")
async def insert_doc_image_url(
    service,
    user_google_email: str,
    document_id: str,
    image_url: str,
    index: int,
    width: int = None,
    height: int = None,
) -> str:
    """
    Inserts an image from a URL into a Google Doc.
    Simplified version that only works with URLs, not Drive files.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        image_url: Public image URL (must start with http:// or https://)
        index: Position to insert image (0-based)
        width: Image width in points (optional)
        height: Image height in points (optional)
    
    Returns:
        str: Confirmation message with insertion details
    """
    logger.info(f"[insert_doc_image_url] Doc={document_id}, url={image_url}, index={index}")
    
    if not (image_url.startswith('http://') or image_url.startswith('https://')):
        return "Error: image_url must be a valid HTTP/HTTPS URL"
    
    # Use helper function to create request
    request = create_insert_image_request(index, image_url, width, height)
    requests = [request]
    
    await asyncio.to_thread(
        service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute
    )
    
    size_info = ""
    if width or height:
        size_info = f" (size: {width or 'auto'}x{height or 'auto'} points)"
    
    link = f"https://docs.google.com/document/d/{document_id}/edit"
    return f"Inserted image from URL{size_info} at index {index} in document {document_id}. Link: {link}"

@server.tool()
@handle_http_errors("update_doc_headers_footers", service_type="docs")
@require_google_service("docs", "docs_write")
async def update_doc_headers_footers(
    service,
    user_google_email: str,
    document_id: str,
    section_type: str,
    content: str,
    header_footer_type: str = "DEFAULT",
) -> str:
    """
    Updates headers or footers in a Google Doc.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        section_type: Type of section to update ("header" or "footer")
        content: Text content for the header/footer
        header_footer_type: Type of header/footer ("DEFAULT", "FIRST_PAGE_ONLY", "EVEN_PAGE")
    
    Returns:
        str: Confirmation message with update details
    """
    logger.info(f"[update_doc_headers_footers] Doc={document_id}, type={section_type}")
    
    if section_type not in ["header", "footer"]:
        return "Error: section_type must be 'header' or 'footer'."
    
    if header_footer_type not in ["DEFAULT", "FIRST_PAGE_ONLY", "EVEN_PAGE"]:
        return "Error: header_footer_type must be 'DEFAULT', 'FIRST_PAGE_ONLY', or 'EVEN_PAGE'."
    
    # First, get the document to find existing header/footer
    doc = await asyncio.to_thread(
        service.documents().get(documentId=document_id).execute
    )
    
    # Find the appropriate header or footer
    headers = doc.get('headers', {})
    footers = doc.get('footers', {})
    
    target_section = None
    section_id = None
    
    if section_type == "header":
        # Look for existing header of the specified type
        for hid, header in headers.items():
            target_section = header
            section_id = hid
            break  # Use first available header for now
    else:
        # Look for existing footer of the specified type
        for fid, footer in footers.items():
            target_section = footer
            section_id = fid
            break  # Use first available footer for now
    
    if not target_section:
        return f"Error: No {section_type} found in document. Please create a {section_type} first in Google Docs."
    
    # Extract any existing text content to replace
    existing_text = ""
    content_elements = target_section.get('content', [])
    for element in content_elements:
        if 'paragraph' in element:
            para_elements = element.get('paragraph', {}).get('elements', [])
            for elem in para_elements:
                if 'textRun' in elem:
                    text_content = elem.get('textRun', {}).get('content', '')
                    # Skip just newlines
                    if text_content.strip():
                        existing_text = text_content.strip()
                        break
    
    requests = []
    
    # Use different strategies based on whether there's existing content
    if existing_text:
        # Use replaceAllText to replace existing content in the header/footer
        requests.append({
            'replaceAllText': {
                'containsText': {
                    'text': existing_text,
                    'matchCase': False
                },
                'replaceText': content
            }
        })
    else:
        # For empty headers/footers, we need to insert text
        # Get the first valid index position in the header/footer
        if content_elements:
            for element in content_elements:
                if 'paragraph' in element:
                    start_index = element.get('startIndex', 0)
                    # Insert at the beginning of the paragraph
                    requests.append({
                        'insertText': {
                            'location': {
                                'segmentId': section_id,  # Target the specific header/footer
                                'index': start_index
                            },
                            'text': content
                        }
                    })
                    break
    
    # Execute the requests if we have any
    if requests:
        await asyncio.to_thread(
            service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute
        )
        
        link = f"https://docs.google.com/document/d/{document_id}/edit"
        return f"Updated {section_type} content in document {document_id}. Link: {link}"
    
    return f"Error: Could not find content structure in {section_type} to update."

@server.tool()
@handle_http_errors("smart_format_text", service_type="docs")
@require_google_service("docs", "docs_write")
async def smart_format_text(
    service,
    user_google_email: str,
    document_id: str,
    target_text: str,
    occurrence: int = 1,
    bold: bool = None,
    italic: bool = None,
    underline: bool = None,
    font_size: int = None,
    font_family: str = None,
) -> str:
    """
    Finds and formats specific text in a Google Doc by searching for it.
    No need to know exact indices - just specify the text to format.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        target_text: Text to find and format
        occurrence: Which occurrence to format (1 for first, 2 for second, etc.)
        bold: Whether to make text bold (True/False/None to leave unchanged)
        italic: Whether to make text italic (True/False/None to leave unchanged)
        underline: Whether to underline text (True/False/None to leave unchanged)
        font_size: Font size in points
        font_family: Font family name (e.g., "Arial", "Times New Roman")
    
    Returns:
        str: Confirmation message with formatting details
    """
    logger.info(f"[smart_format_text] Doc={document_id}, target='{target_text}', occurrence={occurrence}")
    
    # First, get the document to extract text
    doc = await asyncio.to_thread(
        service.documents().get(documentId=document_id).execute
    )
    
    # Extract plain text using helper function
    full_text = extract_document_text_simple(doc)
    
    # Find the text indices using helper function
    start_index, end_index = calculate_text_indices(full_text, target_text, occurrence)
    
    if start_index == -1:
        return f"Text '{target_text}' not found (occurrence {occurrence}) in document {document_id}"
    
    # Apply formatting using the helper function
    format_request = create_format_text_request(
        start_index, end_index, bold, italic, underline, font_size, font_family
    )
    
    if not format_request:
        return "No formatting changes specified. Please provide at least one formatting option."
    
    requests = [format_request]
    
    await asyncio.to_thread(
        service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute
    )
    
    # Build format changes description
    format_changes = []
    if bold is not None:
        format_changes.append(f"bold: {bold}")
    if italic is not None:
        format_changes.append(f"italic: {italic}")
    if underline is not None:
        format_changes.append(f"underline: {underline}")
    if font_size is not None:
        format_changes.append(f"font size: {font_size}pt")
    if font_family is not None:
        format_changes.append(f"font family: {font_family}")
    
    changes_str = ', '.join(format_changes)
    link = f"https://docs.google.com/document/d/{document_id}/edit"
    return f"Applied formatting ({changes_str}) to '{target_text}' (occurrence {occurrence}) in document {document_id}. Link: {link}"

@server.tool()
@handle_http_errors("get_doc_text_positions", service_type="docs", is_read_only=True)
@require_google_service("docs", "docs_read")
async def get_doc_text_positions(
    service,
    user_google_email: str,
    document_id: str,
    search_text: str,
    max_occurrences: int = 10,
) -> str:
    """
    Finds all positions of specific text in a Google Doc.
    Useful for understanding document structure before applying edits.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to search
        search_text: Text to find positions for
        max_occurrences: Maximum number of occurrences to return
    
    Returns:
        str: List of all positions where the text appears
    """
    logger.info(f"[get_doc_text_positions] Doc={document_id}, search='{search_text}'")
    
    # Get the document
    doc = await asyncio.to_thread(
        service.documents().get(documentId=document_id).execute
    )
    
    # Extract plain text using helper function
    full_text = extract_document_text_simple(doc)
    
    # Find all occurrences
    positions = []
    for i in range(1, max_occurrences + 1):
        start_index, end_index = calculate_text_indices(full_text, search_text, i)
        if start_index == -1:
            break
        positions.append({
            'occurrence': i,
            'start_index': start_index,
            'end_index': end_index,
            'preview': full_text[max(0, start_index-20):min(len(full_text), end_index+20)]
        })
    
    if not positions:
        return f"Text '{search_text}' not found in document {document_id}"
    
    # Format results
    results = [f"Found {len(positions)} occurrence(s) of '{search_text}':"]
    for pos in positions:
        preview = pos['preview'].replace('\n', '\\n')
        results.append(
            f"  {pos['occurrence']}. Index {pos['start_index']}-{pos['end_index']}: "
            f"...{preview}..."
        )
    
    link = f"https://docs.google.com/document/d/{document_id}/edit"
    results.append(f"\nDocument link: {link}")
    return '\n'.join(results)

@server.tool()
@handle_http_errors("extract_doc_plain_text", service_type="docs", is_read_only=True)
@require_google_service("docs", "docs_read")
async def extract_doc_plain_text(
    service,
    user_google_email: str,
    document_id: str,
    include_tables: bool = True,
) -> str:
    """
    Extracts plain text content from a Google Doc using simplified extraction.
    Useful for text analysis, search, or preparing content for other operations.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document
        include_tables: Whether to include text from tables
    
    Returns:
        str: Plain text content of the document
    """
    logger.info(f"[extract_doc_plain_text] Doc={document_id}")
    
    # Get the document
    doc = await asyncio.to_thread(
        service.documents().get(documentId=document_id).execute
    )
    
    # Get document title
    title = doc.get('title', 'Untitled Document')
    
    # Extract plain text using helper function
    plain_text = extract_document_text_simple(doc)
    
    # Count some basic statistics
    char_count = len(plain_text)
    word_count = len(plain_text.split())
    line_count = plain_text.count('\n') + 1
    
    link = f"https://docs.google.com/document/d/{document_id}/edit"
    
    return (
        f"Document: {title}\n"
        f"Statistics: {char_count} characters, {word_count} words, {line_count} lines\n"
        f"Link: {link}\n\n"
        f"--- PLAIN TEXT CONTENT ---\n"
        f"{plain_text}"
    )

@server.tool()
@handle_http_errors("smart_replace_and_format", service_type="docs")
@require_google_service("docs", "docs_write")
async def smart_replace_and_format(
    service,
    user_google_email: str,
    document_id: str,
    find_text: str,
    replace_text: str,
    bold: bool = None,
    italic: bool = None,
    underline: bool = None,
    font_size: int = None,
    font_family: str = None,
    match_case: bool = False,
) -> str:
    """
    Finds, replaces, and formats text in a single operation.
    Combines replacement and formatting for efficiency.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        find_text: Text to search for
        replace_text: Text to replace with
        bold: Apply bold to replaced text
        italic: Apply italic to replaced text
        underline: Apply underline to replaced text
        font_size: Font size for replaced text
        font_family: Font family for replaced text
        match_case: Whether to match case exactly
    
    Returns:
        str: Confirmation message with operation details
    """
    logger.info(f"[smart_replace_and_format] Doc={document_id}, find='{find_text}', replace='{replace_text}'")
    
    # First, get the document to understand structure
    doc = await asyncio.to_thread(
        service.documents().get(documentId=document_id).execute
    )
    
    # Extract text to find positions before replacement
    full_text = extract_document_text_simple(doc)
    
    # Count occurrences that will be replaced
    occurrences = 0
    search_text = find_text if match_case else find_text.lower()
    compare_text = full_text if match_case else full_text.lower()
    pos = 0
    while True:
        pos = compare_text.find(search_text, pos)
        if pos == -1:
            break
        occurrences += 1
        pos += len(search_text)
    
    if occurrences == 0:
        return f"Text '{find_text}' not found in document {document_id}"
    
    # Build requests - first replace, then format if needed
    requests = []
    
    # Replace all text
    requests.append(create_find_replace_request(find_text, replace_text, match_case))
    
    # If formatting is requested, we need to find and format the replaced text
    if any([bold is not None, italic is not None, underline is not None, 
            font_size is not None, font_family is not None]):
        
        # Note: After replacement, we'd need to re-fetch the document to get new indices
        # For now, we'll apply the formatting in a second batch update
        
        # Execute the replacement first
        await asyncio.to_thread(
            service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute
        )
        
        # Re-fetch document with replaced text
        doc = await asyncio.to_thread(
            service.documents().get(documentId=document_id).execute
        )
        
        # Extract new text
        new_text = extract_document_text_simple(doc)
        
        # Find all occurrences of the replaced text and format them
        format_requests = []
        for i in range(1, occurrences + 1):
            start_index, end_index = calculate_text_indices(new_text, replace_text, i)
            if start_index != -1:
                format_request = create_format_text_request(
                    start_index, end_index, bold, italic, underline, font_size, font_family
                )
                if format_request:
                    format_requests.append(format_request)
        
        if format_requests:
            await asyncio.to_thread(
                service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': format_requests}
                ).execute
            )
        
        # Build format description
        format_changes = []
        if bold is not None:
            format_changes.append(f"bold: {bold}")
        if italic is not None:
            format_changes.append(f"italic: {italic}")
        if underline is not None:
            format_changes.append(f"underline: {underline}")
        if font_size is not None:
            format_changes.append(f"font size: {font_size}pt")
        if font_family is not None:
            format_changes.append(f"font family: {font_family}")
        
        format_str = f" and formatted ({', '.join(format_changes)})" if format_changes else ""
        link = f"https://docs.google.com/document/d/{document_id}/edit"
        return f"Replaced {occurrences} occurrence(s) of '{find_text}' with '{replace_text}'{format_str} in document {document_id}. Link: {link}"
    
    else:
        # Just replacement, no formatting
        result = await asyncio.to_thread(
            service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute
        )
        
        link = f"https://docs.google.com/document/d/{document_id}/edit"
        return f"Replaced {occurrences} occurrence(s) of '{find_text}' with '{replace_text}' in document {document_id}. Link: {link}"

@server.tool()
@handle_http_errors("batch_update_doc", service_type="docs")
@require_google_service("docs", "docs_write")
async def batch_update_doc(
    service,
    user_google_email: str,
    document_id: str,
    operations: list,
) -> str:
    """
    Executes multiple document operations in a single atomic batch update.
    
    Args:
        user_google_email: User's Google email address
        document_id: ID of the document to update
        operations: List of operation dictionaries. Each operation should contain:
                   - type: Operation type ('insert_text', 'delete_text', 'replace_text', 'format_text', 'insert_table', 'insert_page_break')
                   - Additional parameters specific to each operation type
    
    Example operations:
        [
            {"type": "insert_text", "index": 1, "text": "Hello World"},
            {"type": "format_text", "start_index": 1, "end_index": 12, "bold": true},
            {"type": "insert_table", "index": 20, "rows": 2, "columns": 3}
        ]
    
    Returns:
        str: Confirmation message with batch operation results
    """
    logger.info(f"[batch_update_doc] Doc={document_id}, operations={len(operations)}")
    
    if not operations:
        return "Error: No operations provided. Please provide at least one operation."
    
    requests = []
    operation_descriptions = []
    
    for i, op in enumerate(operations):
        # Validate operation using helper function
        is_valid, error = validate_operation(op)
        if not is_valid:
            return f"Error: Operation {i+1}: {error}"
        
        op_type = op.get('type')
        
        try:
            if op_type == 'insert_text':
                requests.append(create_insert_text_request(op['index'], op['text']))
                operation_descriptions.append(f"insert text at {op['index']}")
                
            elif op_type == 'delete_text':
                requests.append(create_delete_range_request(op['start_index'], op['end_index']))
                operation_descriptions.append(f"delete text {op['start_index']}-{op['end_index']}")
                
            elif op_type == 'replace_text':
                requests.extend([
                    create_delete_range_request(op['start_index'], op['end_index']),
                    create_insert_text_request(op['start_index'], op['text'])
                ])
                operation_descriptions.append(f"replace text {op['start_index']}-{op['end_index']}")
                
            elif op_type == 'format_text':
                format_request = create_format_text_request(
                    op['start_index'], op['end_index'],
                    op.get('bold'), op.get('italic'), op.get('underline'),
                    op.get('font_size'), op.get('font_family')
                )
                if format_request:
                    requests.append(format_request)
                    # Build format description
                    format_changes = []
                    if op.get('bold') is not None:
                        format_changes.append(f"bold: {op['bold']}")
                    if op.get('italic') is not None:
                        format_changes.append(f"italic: {op['italic']}")
                    if op.get('underline') is not None:
                        format_changes.append(f"underline: {op['underline']}")
                    if op.get('font_size') is not None:
                        format_changes.append(f"font size: {op['font_size']}pt")
                    if op.get('font_family') is not None:
                        format_changes.append(f"font family: {op['font_family']}")
                    operation_descriptions.append(f"format text {op['start_index']}-{op['end_index']} ({', '.join(format_changes)})")
                
            elif op_type == 'insert_table':
                requests.append(create_insert_table_request(op['index'], op['rows'], op['columns']))
                operation_descriptions.append(f"insert {op['rows']}x{op['columns']} table at {op['index']}")
                
            elif op_type == 'insert_page_break':
                requests.append(create_insert_page_break_request(op['index']))
                operation_descriptions.append(f"insert page break at {op['index']}")
                
            elif op_type == 'find_replace':
                requests.append(create_find_replace_request(
                    op['find_text'], op['replace_text'], op.get('match_case', False)
                ))
                operation_descriptions.append(f"find/replace '{op['find_text']}' → '{op['replace_text']}'")
                
        except Exception as e:
            return f"Error: Operation {i+1} ({op_type}) failed: {str(e)}"
    
    # Execute all operations in a single batch
    result = await asyncio.to_thread(
        service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute
    )
    
    # Extract results information
    replies_count = len(result.get('replies', []))
    
    operations_summary = ', '.join(operation_descriptions[:3])  # Show first 3 operations
    if len(operation_descriptions) > 3:
        operations_summary += f" and {len(operation_descriptions) - 3} more"
    
    link = f"https://docs.google.com/document/d/{document_id}/edit"
    return f"Successfully executed {len(operations)} operations ({operations_summary}) on document {document_id}. API replies: {replies_count}. Link: {link}"


# Create comment management tools for documents
_comment_tools = create_comment_tools("document", "document_id")

# Extract and register the functions
read_doc_comments = _comment_tools['read_comments']
create_doc_comment = _comment_tools['create_comment']
reply_to_comment = _comment_tools['reply_to_comment']
resolve_comment = _comment_tools['resolve_comment']
