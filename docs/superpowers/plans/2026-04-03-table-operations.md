# Complete Table Operations for batch_update_doc

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 7 new table operations and enhance the existing `update_table_cell_style` operation in `batch_update_doc` to enable full table manipulation without document replacement.

**Architecture:** Each operation follows the existing 5-file pattern: Pydantic schema in `operation_schemas.py`, request builder in `docs_helpers.py`, validation entry in `docs_helpers.py:validate_operation()`, batch dispatch in `batch_operation_manager.py`, and parameter validation in `validation_manager.py` where needed. All operations share a common `tableCellLocation` or `tableRange` structure with optional `tab_id`.

**Tech Stack:** Python 3.10+, Pydantic v2 (discriminated unions), Google Docs API v1 batchUpdate

---

### Task 1: Enhance `update_table_cell_style` with padding and content_alignment

**Files:**
- Modify: `gdocs/docs_helpers.py` — `build_table_cell_style()` (line 594) and `create_update_table_cell_style_request()` (line 914)
- Modify: `gdocs/operation_schemas.py` — `UpdateTableCellStyleOperation` (line 125)
- Modify: `gdocs/managers/batch_operation_manager.py` — dispatch clause (line 447) and `get_supported_operations()` (line 879)
- Modify: `gdocs/managers/validation_manager.py` — `validate_table_cell_style_params()` (line 742)
- Modify: `gdocs/docs_tools.py` — docstring for `update_table_cell_style` (line 1078)
- Test: `tests/gdocs/test_table_cell_style.py`

- [ ] **Step 1: Write failing tests for padding and content_alignment**

Add to `tests/gdocs/test_table_cell_style.py`:

```python
class TestBuildTableCellStylePadding:
    def test_padding_all_sides(self):
        style, fields = build_table_cell_style(
            padding_top=4.0,
            padding_bottom=4.0,
            padding_left=6.0,
            padding_right=6.0,
        )
        assert style["paddingTop"] == {"magnitude": 4.0, "unit": "PT"}
        assert style["paddingBottom"] == {"magnitude": 4.0, "unit": "PT"}
        assert style["paddingLeft"] == {"magnitude": 6.0, "unit": "PT"}
        assert style["paddingRight"] == {"magnitude": 6.0, "unit": "PT"}
        assert set(fields) == {"paddingTop", "paddingBottom", "paddingLeft", "paddingRight"}

    def test_content_alignment(self):
        style, fields = build_table_cell_style(content_alignment="MIDDLE")
        assert style["contentAlignment"] == "MIDDLE"
        assert fields == ["contentAlignment"]

    def test_combined_background_and_padding(self):
        style, fields = build_table_cell_style(
            background_color="#0B1F3A",
            padding_top=4.0,
        )
        assert "backgroundColor" in style
        assert "paddingTop" in style
        assert "backgroundColor" in fields
        assert "paddingTop" in fields


class TestValidateTableCellStylePaddingAndAlignment:
    @pytest.fixture()
    def vm(self):
        return ValidationManager()

    def test_padding_only_is_valid(self, vm):
        is_valid, _ = vm.validate_table_cell_style_params(padding_top=4.0)
        assert is_valid

    def test_content_alignment_only_is_valid(self, vm):
        is_valid, _ = vm.validate_table_cell_style_params(content_alignment="TOP")
        assert is_valid

    def test_invalid_content_alignment(self, vm):
        is_valid, msg = vm.validate_table_cell_style_params(content_alignment="INVALID")
        assert not is_valid
        assert "content_alignment" in msg

    def test_negative_padding_rejected(self, vm):
        is_valid, msg = vm.validate_table_cell_style_params(padding_top=-1.0)
        assert not is_valid
        assert "padding" in msg.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/gdocs/test_table_cell_style.py -x -q`
Expected: FAIL — `build_table_cell_style()` does not accept `padding_top` etc.

- [ ] **Step 3: Update `build_table_cell_style` in `docs_helpers.py`**

Add parameters to the function signature and body at line 594:

```python
def build_table_cell_style(
    background_color: str = None,
    border_color: str = None,
    border_width: float = None,
    padding_top: float = None,
    padding_bottom: float = None,
    padding_left: float = None,
    padding_right: float = None,
    content_alignment: str = None,
) -> tuple[Dict[str, Any], list[str]]:
```

Add after the `backgroundColor` block (before `return`):

```python
    for padding_val, padding_name in (
        (padding_top, "paddingTop"),
        (padding_bottom, "paddingBottom"),
        (padding_left, "paddingLeft"),
        (padding_right, "paddingRight"),
    ):
        if padding_val is not None:
            table_cell_style[padding_name] = {"magnitude": padding_val, "unit": "PT"}
            fields.append(padding_name)

    if content_alignment is not None:
        table_cell_style["contentAlignment"] = content_alignment
        fields.append("contentAlignment")
```

- [ ] **Step 4: Update `create_update_table_cell_style_request` in `docs_helpers.py`**

Add parameters to the function signature at line 914 and pass them through:

```python
def create_update_table_cell_style_request(
    table_start_index: int,
    background_color: str = None,
    border_color: str = None,
    border_width: float = None,
    row_index: int = None,
    column_index: int = None,
    row_span: int = None,
    column_span: int = None,
    tab_id: Optional[str] = None,
    padding_top: float = None,
    padding_bottom: float = None,
    padding_left: float = None,
    padding_right: float = None,
    content_alignment: str = None,
) -> Optional[Dict[str, Any]]:
```

Update the `build_table_cell_style` call:

```python
    table_cell_style, fields = build_table_cell_style(
        background_color=background_color,
        border_color=border_color,
        border_width=border_width,
        padding_top=padding_top,
        padding_bottom=padding_bottom,
        padding_left=padding_left,
        padding_right=padding_right,
        content_alignment=content_alignment,
    )
```

- [ ] **Step 5: Update `validate_table_cell_style_params` in `validation_manager.py`**

Add parameters to the function signature at line 742:

```python
    def validate_table_cell_style_params(
        self,
        background_color: Optional[str] = None,
        border_color: Optional[str] = None,
        border_width: Optional[float] = None,
        row_index: Optional[int] = None,
        column_index: Optional[int] = None,
        row_span: Optional[int] = None,
        column_span: Optional[int] = None,
        padding_top: Optional[float] = None,
        padding_bottom: Optional[float] = None,
        padding_left: Optional[float] = None,
        padding_right: Optional[float] = None,
        content_alignment: Optional[str] = None,
    ) -> Tuple[bool, str]:
```

Update the "at least one style param" check at line 767:

```python
        if all(
            param is None
            for param in (
                background_color, border_color, border_width,
                padding_top, padding_bottom, padding_left, padding_right,
                content_alignment,
            )
        ):
            return (
                False,
                "At least one table cell style parameter must be provided "
                "(background_color, border_color, border_width, padding_*, or content_alignment)",
            )
```

Add validation for padding and alignment after the `border_width` check:

```python
        for padding_val, padding_name in (
            (padding_top, "padding_top"),
            (padding_bottom, "padding_bottom"),
            (padding_left, "padding_left"),
            (padding_right, "padding_right"),
        ):
            if padding_val is not None:
                if not isinstance(padding_val, (int, float)):
                    return (
                        False,
                        f"{padding_name} must be a number, got {type(padding_val).__name__}",
                    )
                if padding_val < 0:
                    return False, f"{padding_name} must be non-negative, got {padding_val}"

        if content_alignment is not None:
            valid_alignments = ("TOP", "MIDDLE", "BOTTOM")
            if content_alignment not in valid_alignments:
                return (
                    False,
                    f"content_alignment must be one of {valid_alignments}, got '{content_alignment}'",
                )
```

- [ ] **Step 6: Update Pydantic schema in `operation_schemas.py`**

At line 125, add fields to `UpdateTableCellStyleOperation`:

```python
class UpdateTableCellStyleOperation(StrictDocOperation):
    type: Literal["update_table_cell_style"]
    table_start_index: int
    background_color: Optional[str] = None
    border_color: Optional[str] = None
    border_width: Optional[float] = None
    row_index: Optional[int] = None
    column_index: Optional[int] = None
    row_span: Optional[int] = None
    column_span: Optional[int] = None
    padding_top: Optional[float] = None
    padding_bottom: Optional[float] = None
    padding_left: Optional[float] = None
    padding_right: Optional[float] = None
    content_alignment: Optional[str] = None
```

- [ ] **Step 7: Update batch dispatch in `batch_operation_manager.py`**

At line 447, update the dispatch clause to pass new params through validation and request building:

```python
        elif op_type == "update_table_cell_style":
            is_valid, error_msg = (
                self.validation_manager.validate_table_cell_style_params(
                    background_color=op.get("background_color"),
                    border_color=op.get("border_color"),
                    border_width=op.get("border_width"),
                    row_index=op.get("row_index"),
                    column_index=op.get("column_index"),
                    row_span=op.get("row_span"),
                    column_span=op.get("column_span"),
                    padding_top=op.get("padding_top"),
                    padding_bottom=op.get("padding_bottom"),
                    padding_left=op.get("padding_left"),
                    padding_right=op.get("padding_right"),
                    content_alignment=op.get("content_alignment"),
                )
            )
            if not is_valid:
                raise ValueError(error_msg)

            request = create_update_table_cell_style_request(
                table_start_index=op["table_start_index"],
                background_color=op.get("background_color"),
                border_color=op.get("border_color"),
                border_width=op.get("border_width"),
                row_index=op.get("row_index"),
                column_index=op.get("column_index"),
                row_span=op.get("row_span"),
                column_span=op.get("column_span"),
                tab_id=tab_id,
                padding_top=op.get("padding_top"),
                padding_bottom=op.get("padding_bottom"),
                padding_left=op.get("padding_left"),
                padding_right=op.get("padding_right"),
                content_alignment=op.get("content_alignment"),
            )
```

Also update the description builder to include new style params:

```python
            style_changes = []
            for param, name in [
                ("background_color", "background"),
                ("border_color", "border color"),
                ("border_width", "border width"),
                ("padding_top", "padding-top"),
                ("padding_bottom", "padding-bottom"),
                ("padding_left", "padding-left"),
                ("padding_right", "padding-right"),
                ("content_alignment", "alignment"),
            ]:
                if op.get(param) is not None:
                    value = f"{op[param]}pt" if "padding" in param or param == "border_width" else op[param]
                    style_changes.append(f"{name}: {value}")
```

Update `get_supported_operations()` optional list for `update_table_cell_style`:

```python
                "update_table_cell_style": {
                    "required": ["table_start_index"],
                    "optional": [
                        "background_color",
                        "border_color",
                        "border_width",
                        "row_index",
                        "column_index",
                        "row_span",
                        "column_span",
                        "padding_top",
                        "padding_bottom",
                        "padding_left",
                        "padding_right",
                        "content_alignment",
                    ],
                    "description": "Apply table cell styling to an entire table or a targeted cell range",
                },
```

- [ ] **Step 8: Update batch_update_doc docstring in `docs_tools.py`**

At line 1078, update the `update_table_cell_style` entry:

```
      update_table_cell_style
                       - required: table_start_index (int)
                         optional: background_color, border_color, border_width,
                                   row_index, column_index, row_span, column_span,
                                   padding_top, padding_bottom, padding_left,
                                   padding_right, content_alignment (TOP|MIDDLE|BOTTOM)
                         Use inspect_doc_structure to find table_start_index from
                         table_details[].start_index. If row/column values are
                         omitted, the style is applied to the entire table.
```

- [ ] **Step 9: Update validation_manager batch validation dispatch**

At line 1129, add the new params to the `validate_table_cell_style_params` call:

```python
                is_valid, error_msg = self.validate_table_cell_style_params(
                    op.get("background_color"),
                    op.get("border_color"),
                    op.get("border_width"),
                    op.get("row_index"),
                    op.get("column_index"),
                    op.get("row_span"),
                    op.get("column_span"),
                    op.get("padding_top"),
                    op.get("padding_bottom"),
                    op.get("padding_left"),
                    op.get("padding_right"),
                    op.get("content_alignment"),
                )
```

- [ ] **Step 10: Run all tests**

Run: `uv run python -m pytest tests/gdocs/test_table_cell_style.py -v`
Expected: ALL PASS

- [ ] **Step 11: Commit**

```bash
git add gdocs/docs_helpers.py gdocs/operation_schemas.py gdocs/managers/batch_operation_manager.py gdocs/managers/validation_manager.py gdocs/docs_tools.py tests/gdocs/test_table_cell_style.py
git commit -m "feat(gdocs): add padding and content_alignment to update_table_cell_style"
```

---

### Task 2: Add `insert_table_row` and `delete_table_row` operations

**Files:**
- Modify: `gdocs/docs_helpers.py` — add `create_insert_table_row_request()` and `create_delete_table_row_request()`, update `validate_operation()`
- Modify: `gdocs/operation_schemas.py` — add schemas, update Union
- Modify: `gdocs/managers/batch_operation_manager.py` — add dispatch clauses, update supported_types
- Modify: `gdocs/docs_tools.py` — add to docstring
- Create: `tests/gdocs/test_table_row_operations.py`

- [ ] **Step 1: Write failing tests**

Create `tests/gdocs/test_table_row_operations.py`:

```python
"""
Tests for insert_table_row and delete_table_row operations in batch_update_doc.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from gdocs.docs_helpers import (
    create_insert_table_row_request,
    create_delete_table_row_request,
    validate_operation,
)
from gdocs.managers.batch_operation_manager import BatchOperationManager


class TestCreateInsertTableRowRequest:
    def test_insert_below(self):
        result = create_insert_table_row_request(
            table_start_index=122, row_index=2, insert_below=True
        )
        inner = result["insertTableRow"]
        assert inner["tableCellLocation"]["tableStartLocation"] == {"index": 122}
        assert inner["tableCellLocation"]["rowIndex"] == 2
        assert inner["tableCellLocation"]["columnIndex"] == 0
        assert inner["insertBelow"] is True

    def test_insert_above(self):
        result = create_insert_table_row_request(
            table_start_index=122, row_index=0, insert_below=False
        )
        assert result["insertTableRow"]["insertBelow"] is False

    def test_with_tab_id(self):
        result = create_insert_table_row_request(
            table_start_index=122, row_index=1, tab_id="t.0"
        )
        location = result["insertTableRow"]["tableCellLocation"]["tableStartLocation"]
        assert location["tabId"] == "t.0"

    def test_default_insert_below_is_true(self):
        result = create_insert_table_row_request(
            table_start_index=122, row_index=2
        )
        assert result["insertTableRow"]["insertBelow"] is True


class TestCreateDeleteTableRowRequest:
    def test_basic(self):
        result = create_delete_table_row_request(
            table_start_index=122, row_index=5
        )
        inner = result["deleteTableRow"]
        assert inner["tableCellLocation"]["tableStartLocation"] == {"index": 122}
        assert inner["tableCellLocation"]["rowIndex"] == 5
        assert inner["tableCellLocation"]["columnIndex"] == 0

    def test_with_tab_id(self):
        result = create_delete_table_row_request(
            table_start_index=122, row_index=3, tab_id="t.0"
        )
        location = result["deleteTableRow"]["tableCellLocation"]["tableStartLocation"]
        assert location["tabId"] == "t.0"


class TestValidateOperation:
    def test_insert_table_row_valid(self):
        is_valid, _ = validate_operation({
            "type": "insert_table_row",
            "table_start_index": 122,
            "row_index": 2,
        })
        assert is_valid

    def test_insert_table_row_missing_row_index(self):
        is_valid, msg = validate_operation({
            "type": "insert_table_row",
            "table_start_index": 122,
        })
        assert not is_valid
        assert "row_index" in msg

    def test_delete_table_row_valid(self):
        is_valid, _ = validate_operation({
            "type": "delete_table_row",
            "table_start_index": 122,
            "row_index": 5,
        })
        assert is_valid


class TestBatchManagerIntegration:
    @pytest.fixture()
    def manager(self):
        return BatchOperationManager(Mock())

    def test_build_insert_table_row_request(self, manager):
        request, desc = manager._build_operation_request(
            {
                "type": "insert_table_row",
                "table_start_index": 122,
                "row_index": 2,
                "insert_below": True,
            },
            "insert_table_row",
        )
        assert "insertTableRow" in request
        assert "insert row" in desc.lower()

    def test_build_delete_table_row_request(self, manager):
        request, desc = manager._build_operation_request(
            {
                "type": "delete_table_row",
                "table_start_index": 122,
                "row_index": 5,
            },
            "delete_table_row",
        )
        assert "deleteTableRow" in request
        assert "delete row" in desc.lower()

    @pytest.mark.asyncio
    async def test_end_to_end_insert_table_row(self, manager):
        manager._execute_batch_requests = AsyncMock(return_value={"replies": [{}]})
        success, _, meta = await manager.execute_batch_operations(
            "doc-123",
            [{"type": "insert_table_row", "table_start_index": 122, "row_index": 2}],
        )
        assert success

    def test_supported_operations_include_row_ops(self, manager):
        supported = manager.get_supported_operations()["supported_operations"]
        assert "insert_table_row" in supported
        assert "delete_table_row" in supported
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/gdocs/test_table_row_operations.py -x -q`
Expected: FAIL — import errors

- [ ] **Step 3: Add helper functions in `docs_helpers.py`**

Add these functions near the existing `create_insert_table_request` (after line 911):

```python
def create_insert_table_row_request(
    table_start_index: int,
    row_index: int,
    insert_below: bool = True,
    tab_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an insertTableRow request for Google Docs API.

    Args:
        table_start_index: Start index of the target table
        row_index: Reference row (zero-based)
        insert_below: Insert below (True) or above (False) the reference row
        tab_id: Optional ID of the tab to target
    """
    location: Dict[str, Any] = {"index": table_start_index}
    if tab_id:
        location["tabId"] = tab_id

    return {
        "insertTableRow": {
            "tableCellLocation": {
                "tableStartLocation": location,
                "rowIndex": row_index,
                "columnIndex": 0,
            },
            "insertBelow": insert_below,
        }
    }


def create_delete_table_row_request(
    table_start_index: int,
    row_index: int,
    tab_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a deleteTableRow request for Google Docs API.

    Args:
        table_start_index: Start index of the target table
        row_index: Row to delete (zero-based)
        tab_id: Optional ID of the tab to target
    """
    location: Dict[str, Any] = {"index": table_start_index}
    if tab_id:
        location["tabId"] = tab_id

    return {
        "deleteTableRow": {
            "tableCellLocation": {
                "tableStartLocation": location,
                "rowIndex": row_index,
                "columnIndex": 0,
            }
        }
    }
```

- [ ] **Step 4: Add to `validate_operation()` in `docs_helpers.py`**

Add to the `required_fields` dict at line 1438:

```python
        "insert_table_row": ["table_start_index", "row_index"],
        "delete_table_row": ["table_start_index", "row_index"],
```

- [ ] **Step 5: Add Pydantic schemas in `operation_schemas.py`**

Add before the `BatchDocOperation` union:

```python
class InsertTableRowOperation(StrictDocOperation):
    type: Literal["insert_table_row"]
    table_start_index: int
    row_index: int
    insert_below: bool = True


class DeleteTableRowOperation(StrictDocOperation):
    type: Literal["delete_table_row"]
    table_start_index: int
    row_index: int
```

Add `InsertTableRowOperation` and `DeleteTableRowOperation` to the `Union` in `BatchDocOperation`.

- [ ] **Step 6: Add dispatch clauses in `batch_operation_manager.py`**

Add imports:

```python
    create_insert_table_row_request,
    create_delete_table_row_request,
```

Add dispatch clauses before the `else` block:

```python
        elif op_type == "insert_table_row":
            request = create_insert_table_row_request(
                table_start_index=op["table_start_index"],
                row_index=op["row_index"],
                insert_below=op.get("insert_below", True),
                tab_id=tab_id,
            )
            direction = "below" if op.get("insert_below", True) else "above"
            description = f"insert row {direction} row {op['row_index']} in table at {op['table_start_index']}"

        elif op_type == "delete_table_row":
            request = create_delete_table_row_request(
                table_start_index=op["table_start_index"],
                row_index=op["row_index"],
                tab_id=tab_id,
            )
            description = f"delete row {op['row_index']} from table at {op['table_start_index']}"
```

Add to `supported_types` list and `get_supported_operations()`:

```python
                "insert_table_row": {
                    "required": ["table_start_index", "row_index"],
                    "optional": ["insert_below", "tab_id"],
                    "description": "Insert a row above or below a reference row in a table",
                },
                "delete_table_row": {
                    "required": ["table_start_index", "row_index"],
                    "optional": ["tab_id"],
                    "description": "Delete a row from a table",
                },
```

- [ ] **Step 7: Update docstring in `docs_tools.py`**

Add after the `insert_table` entry (line 1086):

```
      insert_table_row - required: table_start_index (int), row_index (int)
                         optional: insert_below (bool, default true), tab_id
      delete_table_row - required: table_start_index (int), row_index (int)
                         optional: tab_id
```

- [ ] **Step 8: Run all tests**

Run: `uv run python -m pytest tests/gdocs/test_table_row_operations.py tests/gdocs/test_table_cell_style.py -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add gdocs/docs_helpers.py gdocs/operation_schemas.py gdocs/managers/batch_operation_manager.py gdocs/docs_tools.py tests/gdocs/test_table_row_operations.py
git commit -m "feat(gdocs): add insert_table_row and delete_table_row to batch_update_doc"
```

---

### Task 3: Add `insert_table_column` and `delete_table_column` operations

**Files:**
- Modify: `gdocs/docs_helpers.py` — add helpers, update `validate_operation()`
- Modify: `gdocs/operation_schemas.py` — add schemas, update Union
- Modify: `gdocs/managers/batch_operation_manager.py` — add dispatch, update supported_types
- Modify: `gdocs/docs_tools.py` — add to docstring
- Create: `tests/gdocs/test_table_column_operations.py`

- [ ] **Step 1: Write failing tests**

Create `tests/gdocs/test_table_column_operations.py`:

```python
"""
Tests for insert_table_column and delete_table_column operations in batch_update_doc.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from gdocs.docs_helpers import (
    create_insert_table_column_request,
    create_delete_table_column_request,
    validate_operation,
)
from gdocs.managers.batch_operation_manager import BatchOperationManager


class TestCreateInsertTableColumnRequest:
    def test_insert_right(self):
        result = create_insert_table_column_request(
            table_start_index=122, column_index=1, insert_right=True
        )
        inner = result["insertTableColumn"]
        assert inner["tableCellLocation"]["tableStartLocation"] == {"index": 122}
        assert inner["tableCellLocation"]["rowIndex"] == 0
        assert inner["tableCellLocation"]["columnIndex"] == 1
        assert inner["insertRight"] is True

    def test_insert_left(self):
        result = create_insert_table_column_request(
            table_start_index=122, column_index=0, insert_right=False
        )
        assert result["insertTableColumn"]["insertRight"] is False

    def test_with_tab_id(self):
        result = create_insert_table_column_request(
            table_start_index=122, column_index=1, tab_id="t.0"
        )
        location = result["insertTableColumn"]["tableCellLocation"]["tableStartLocation"]
        assert location["tabId"] == "t.0"


class TestCreateDeleteTableColumnRequest:
    def test_basic(self):
        result = create_delete_table_column_request(
            table_start_index=122, column_index=2
        )
        inner = result["deleteTableColumn"]
        assert inner["tableCellLocation"]["tableStartLocation"] == {"index": 122}
        assert inner["tableCellLocation"]["rowIndex"] == 0
        assert inner["tableCellLocation"]["columnIndex"] == 2

    def test_with_tab_id(self):
        result = create_delete_table_column_request(
            table_start_index=122, column_index=2, tab_id="t.0"
        )
        location = result["deleteTableColumn"]["tableCellLocation"]["tableStartLocation"]
        assert location["tabId"] == "t.0"


class TestValidateOperation:
    def test_insert_table_column_valid(self):
        is_valid, _ = validate_operation({
            "type": "insert_table_column",
            "table_start_index": 122,
            "column_index": 1,
        })
        assert is_valid

    def test_delete_table_column_valid(self):
        is_valid, _ = validate_operation({
            "type": "delete_table_column",
            "table_start_index": 122,
            "column_index": 2,
        })
        assert is_valid


class TestBatchManagerIntegration:
    @pytest.fixture()
    def manager(self):
        return BatchOperationManager(Mock())

    def test_build_insert_table_column_request(self, manager):
        request, desc = manager._build_operation_request(
            {
                "type": "insert_table_column",
                "table_start_index": 122,
                "column_index": 1,
                "insert_right": True,
            },
            "insert_table_column",
        )
        assert "insertTableColumn" in request
        assert "insert column" in desc.lower()

    def test_build_delete_table_column_request(self, manager):
        request, desc = manager._build_operation_request(
            {
                "type": "delete_table_column",
                "table_start_index": 122,
                "column_index": 2,
            },
            "delete_table_column",
        )
        assert "deleteTableColumn" in request
        assert "delete column" in desc.lower()

    @pytest.mark.asyncio
    async def test_end_to_end_insert_table_column(self, manager):
        manager._execute_batch_requests = AsyncMock(return_value={"replies": [{}]})
        success, _, meta = await manager.execute_batch_operations(
            "doc-123",
            [{"type": "insert_table_column", "table_start_index": 122, "column_index": 1}],
        )
        assert success

    def test_supported_operations_include_column_ops(self, manager):
        supported = manager.get_supported_operations()["supported_operations"]
        assert "insert_table_column" in supported
        assert "delete_table_column" in supported
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/gdocs/test_table_column_operations.py -x -q`
Expected: FAIL

- [ ] **Step 3: Add helper functions in `docs_helpers.py`**

```python
def create_insert_table_column_request(
    table_start_index: int,
    column_index: int,
    insert_right: bool = True,
    tab_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an insertTableColumn request for Google Docs API.

    Args:
        table_start_index: Start index of the target table
        column_index: Reference column (zero-based)
        insert_right: Insert right (True) or left (False) of the reference column
        tab_id: Optional ID of the tab to target
    """
    location: Dict[str, Any] = {"index": table_start_index}
    if tab_id:
        location["tabId"] = tab_id

    return {
        "insertTableColumn": {
            "tableCellLocation": {
                "tableStartLocation": location,
                "rowIndex": 0,
                "columnIndex": column_index,
            },
            "insertRight": insert_right,
        }
    }


def create_delete_table_column_request(
    table_start_index: int,
    column_index: int,
    tab_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a deleteTableColumn request for Google Docs API.

    Args:
        table_start_index: Start index of the target table
        column_index: Column to delete (zero-based)
        tab_id: Optional ID of the tab to target
    """
    location: Dict[str, Any] = {"index": table_start_index}
    if tab_id:
        location["tabId"] = tab_id

    return {
        "deleteTableColumn": {
            "tableCellLocation": {
                "tableStartLocation": location,
                "rowIndex": 0,
                "columnIndex": column_index,
            }
        }
    }
```

- [ ] **Step 4: Add to `validate_operation()` required_fields**

```python
        "insert_table_column": ["table_start_index", "column_index"],
        "delete_table_column": ["table_start_index", "column_index"],
```

- [ ] **Step 5: Add Pydantic schemas in `operation_schemas.py`**

```python
class InsertTableColumnOperation(StrictDocOperation):
    type: Literal["insert_table_column"]
    table_start_index: int
    column_index: int
    insert_right: bool = True


class DeleteTableColumnOperation(StrictDocOperation):
    type: Literal["delete_table_column"]
    table_start_index: int
    column_index: int
```

Add both to the `BatchDocOperation` Union.

- [ ] **Step 6: Add dispatch clauses in `batch_operation_manager.py`**

Add imports:

```python
    create_insert_table_column_request,
    create_delete_table_column_request,
```

Add dispatch clauses:

```python
        elif op_type == "insert_table_column":
            request = create_insert_table_column_request(
                table_start_index=op["table_start_index"],
                column_index=op["column_index"],
                insert_right=op.get("insert_right", True),
                tab_id=tab_id,
            )
            direction = "right of" if op.get("insert_right", True) else "left of"
            description = f"insert column {direction} column {op['column_index']} in table at {op['table_start_index']}"

        elif op_type == "delete_table_column":
            request = create_delete_table_column_request(
                table_start_index=op["table_start_index"],
                column_index=op["column_index"],
                tab_id=tab_id,
            )
            description = f"delete column {op['column_index']} from table at {op['table_start_index']}"
```

Add to `supported_types` list and `get_supported_operations()`:

```python
                "insert_table_column": {
                    "required": ["table_start_index", "column_index"],
                    "optional": ["insert_right", "tab_id"],
                    "description": "Insert a column left or right of a reference column in a table",
                },
                "delete_table_column": {
                    "required": ["table_start_index", "column_index"],
                    "optional": ["tab_id"],
                    "description": "Delete a column from a table",
                },
```

- [ ] **Step 7: Update docstring in `docs_tools.py`**

Add after the row operation entries:

```
      insert_table_column
                       - required: table_start_index (int), column_index (int)
                         optional: insert_right (bool, default true), tab_id
      delete_table_column
                       - required: table_start_index (int), column_index (int)
                         optional: tab_id
```

- [ ] **Step 8: Run all tests**

Run: `uv run python -m pytest tests/gdocs/test_table_column_operations.py tests/gdocs/test_table_row_operations.py tests/gdocs/test_table_cell_style.py -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add gdocs/docs_helpers.py gdocs/operation_schemas.py gdocs/managers/batch_operation_manager.py gdocs/docs_tools.py tests/gdocs/test_table_column_operations.py
git commit -m "feat(gdocs): add insert/delete_table_column to batch_update_doc"
```

---

### Task 4: Add `merge_table_cells` and `unmerge_table_cells` operations

**Files:**
- Modify: `gdocs/docs_helpers.py` — add helpers, update `validate_operation()`
- Modify: `gdocs/operation_schemas.py` — add schemas, update Union
- Modify: `gdocs/managers/batch_operation_manager.py` — add dispatch, update supported_types
- Modify: `gdocs/docs_tools.py` — add to docstring
- Create: `tests/gdocs/test_table_merge_operations.py`

- [ ] **Step 1: Write failing tests**

Create `tests/gdocs/test_table_merge_operations.py`:

```python
"""
Tests for merge_table_cells and unmerge_table_cells operations in batch_update_doc.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from gdocs.docs_helpers import (
    create_merge_table_cells_request,
    create_unmerge_table_cells_request,
    validate_operation,
)
from gdocs.managers.batch_operation_manager import BatchOperationManager


class TestCreateMergeTableCellsRequest:
    def test_basic_merge(self):
        result = create_merge_table_cells_request(
            table_start_index=122,
            row_index=0,
            column_index=0,
            row_span=1,
            column_span=3,
        )
        inner = result["mergeTableCells"]
        table_range = inner["tableRange"]
        assert table_range["tableCellLocation"]["tableStartLocation"] == {"index": 122}
        assert table_range["tableCellLocation"]["rowIndex"] == 0
        assert table_range["tableCellLocation"]["columnIndex"] == 0
        assert table_range["rowSpan"] == 1
        assert table_range["columnSpan"] == 3

    def test_with_tab_id(self):
        result = create_merge_table_cells_request(
            table_start_index=122,
            row_index=0,
            column_index=0,
            row_span=2,
            column_span=2,
            tab_id="t.0",
        )
        location = result["mergeTableCells"]["tableRange"]["tableCellLocation"]["tableStartLocation"]
        assert location["tabId"] == "t.0"


class TestCreateUnmergeTableCellsRequest:
    def test_basic_unmerge(self):
        result = create_unmerge_table_cells_request(
            table_start_index=122,
            row_index=0,
            column_index=0,
            row_span=1,
            column_span=3,
        )
        inner = result["unmergeTableCells"]
        assert inner["tableRange"]["rowSpan"] == 1
        assert inner["tableRange"]["columnSpan"] == 3

    def test_with_tab_id(self):
        result = create_unmerge_table_cells_request(
            table_start_index=122,
            row_index=0,
            column_index=0,
            row_span=1,
            column_span=3,
            tab_id="t.0",
        )
        location = result["unmergeTableCells"]["tableRange"]["tableCellLocation"]["tableStartLocation"]
        assert location["tabId"] == "t.0"


class TestValidateOperation:
    def test_merge_valid(self):
        is_valid, _ = validate_operation({
            "type": "merge_table_cells",
            "table_start_index": 122,
            "row_index": 0,
            "column_index": 0,
            "row_span": 1,
            "column_span": 3,
        })
        assert is_valid

    def test_merge_missing_row_span(self):
        is_valid, msg = validate_operation({
            "type": "merge_table_cells",
            "table_start_index": 122,
            "row_index": 0,
            "column_index": 0,
            "column_span": 3,
        })
        assert not is_valid
        assert "row_span" in msg

    def test_unmerge_valid(self):
        is_valid, _ = validate_operation({
            "type": "unmerge_table_cells",
            "table_start_index": 122,
            "row_index": 0,
            "column_index": 0,
            "row_span": 1,
            "column_span": 3,
        })
        assert is_valid


class TestBatchManagerIntegration:
    @pytest.fixture()
    def manager(self):
        return BatchOperationManager(Mock())

    def test_build_merge_request(self, manager):
        request, desc = manager._build_operation_request(
            {
                "type": "merge_table_cells",
                "table_start_index": 122,
                "row_index": 0,
                "column_index": 0,
                "row_span": 1,
                "column_span": 3,
            },
            "merge_table_cells",
        )
        assert "mergeTableCells" in request
        assert "merge" in desc.lower()

    def test_build_unmerge_request(self, manager):
        request, desc = manager._build_operation_request(
            {
                "type": "unmerge_table_cells",
                "table_start_index": 122,
                "row_index": 0,
                "column_index": 0,
                "row_span": 1,
                "column_span": 3,
            },
            "unmerge_table_cells",
        )
        assert "unmergeTableCells" in request
        assert "unmerge" in desc.lower()

    @pytest.mark.asyncio
    async def test_end_to_end_merge(self, manager):
        manager._execute_batch_requests = AsyncMock(return_value={"replies": [{}]})
        success, _, _ = await manager.execute_batch_operations(
            "doc-123",
            [{
                "type": "merge_table_cells",
                "table_start_index": 122,
                "row_index": 0,
                "column_index": 0,
                "row_span": 1,
                "column_span": 3,
            }],
        )
        assert success

    def test_supported_operations_include_merge_ops(self, manager):
        supported = manager.get_supported_operations()["supported_operations"]
        assert "merge_table_cells" in supported
        assert "unmerge_table_cells" in supported
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/gdocs/test_table_merge_operations.py -x -q`
Expected: FAIL

- [ ] **Step 3: Add helper functions in `docs_helpers.py`**

```python
def _build_table_range(
    table_start_index: int,
    row_index: int,
    column_index: int,
    row_span: int,
    column_span: int,
    tab_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a tableRange object used by merge/unmerge requests."""
    location: Dict[str, Any] = {"index": table_start_index}
    if tab_id:
        location["tabId"] = tab_id

    return {
        "tableRange": {
            "tableCellLocation": {
                "tableStartLocation": location,
                "rowIndex": row_index,
                "columnIndex": column_index,
            },
            "rowSpan": row_span,
            "columnSpan": column_span,
        }
    }


def create_merge_table_cells_request(
    table_start_index: int,
    row_index: int,
    column_index: int,
    row_span: int,
    column_span: int,
    tab_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a mergeTableCells request for Google Docs API.

    Args:
        table_start_index: Start index of the target table
        row_index: Start row of merge range (zero-based)
        column_index: Start column of merge range (zero-based)
        row_span: Number of rows to merge
        column_span: Number of columns to merge
        tab_id: Optional ID of the tab to target
    """
    return {"mergeTableCells": _build_table_range(
        table_start_index, row_index, column_index, row_span, column_span, tab_id
    )}


def create_unmerge_table_cells_request(
    table_start_index: int,
    row_index: int,
    column_index: int,
    row_span: int,
    column_span: int,
    tab_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an unmergeTableCells request for Google Docs API.

    Args:
        table_start_index: Start index of the target table
        row_index: Start row of unmerge range (zero-based)
        column_index: Start column of unmerge range (zero-based)
        row_span: Number of rows to unmerge
        column_span: Number of columns to unmerge
        tab_id: Optional ID of the tab to target
    """
    return {"unmergeTableCells": _build_table_range(
        table_start_index, row_index, column_index, row_span, column_span, tab_id
    )}
```

- [ ] **Step 4: Add to `validate_operation()` required_fields**

```python
        "merge_table_cells": ["table_start_index", "row_index", "column_index", "row_span", "column_span"],
        "unmerge_table_cells": ["table_start_index", "row_index", "column_index", "row_span", "column_span"],
```

- [ ] **Step 5: Add Pydantic schemas in `operation_schemas.py`**

```python
class MergeTableCellsOperation(StrictDocOperation):
    type: Literal["merge_table_cells"]
    table_start_index: int
    row_index: int
    column_index: int
    row_span: int
    column_span: int


class UnmergeTableCellsOperation(StrictDocOperation):
    type: Literal["unmerge_table_cells"]
    table_start_index: int
    row_index: int
    column_index: int
    row_span: int
    column_span: int
```

Add both to the `BatchDocOperation` Union.

- [ ] **Step 6: Add dispatch clauses and imports in `batch_operation_manager.py`**

Add imports:

```python
    create_merge_table_cells_request,
    create_unmerge_table_cells_request,
```

Add dispatch clauses:

```python
        elif op_type == "merge_table_cells":
            request = create_merge_table_cells_request(
                table_start_index=op["table_start_index"],
                row_index=op["row_index"],
                column_index=op["column_index"],
                row_span=op["row_span"],
                column_span=op["column_span"],
                tab_id=tab_id,
            )
            description = (
                f"merge cells at ({op['row_index']},{op['column_index']}) "
                f"span {op['row_span']}x{op['column_span']} in table at {op['table_start_index']}"
            )

        elif op_type == "unmerge_table_cells":
            request = create_unmerge_table_cells_request(
                table_start_index=op["table_start_index"],
                row_index=op["row_index"],
                column_index=op["column_index"],
                row_span=op["row_span"],
                column_span=op["column_span"],
                tab_id=tab_id,
            )
            description = (
                f"unmerge cells at ({op['row_index']},{op['column_index']}) "
                f"span {op['row_span']}x{op['column_span']} in table at {op['table_start_index']}"
            )
```

Add to `supported_types` list and `get_supported_operations()`:

```python
                "merge_table_cells": {
                    "required": ["table_start_index", "row_index", "column_index", "row_span", "column_span"],
                    "optional": ["tab_id"],
                    "description": "Merge a range of table cells into a single cell",
                },
                "unmerge_table_cells": {
                    "required": ["table_start_index", "row_index", "column_index", "row_span", "column_span"],
                    "optional": ["tab_id"],
                    "description": "Unmerge previously merged table cells",
                },
```

- [ ] **Step 7: Update docstring in `docs_tools.py`**

```
      merge_table_cells
                       - required: table_start_index (int), row_index (int),
                                   column_index (int), row_span (int), column_span (int)
                         optional: tab_id
      unmerge_table_cells
                       - required: table_start_index (int), row_index (int),
                                   column_index (int), row_span (int), column_span (int)
                         optional: tab_id
```

- [ ] **Step 8: Run all tests**

Run: `uv run python -m pytest tests/gdocs/test_table_merge_operations.py tests/gdocs/test_table_column_operations.py tests/gdocs/test_table_row_operations.py tests/gdocs/test_table_cell_style.py -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add gdocs/docs_helpers.py gdocs/operation_schemas.py gdocs/managers/batch_operation_manager.py gdocs/docs_tools.py tests/gdocs/test_table_merge_operations.py
git commit -m "feat(gdocs): add merge/unmerge_table_cells to batch_update_doc"
```

---

### Task 5: Add `update_table_column_properties` operation

**Files:**
- Modify: `gdocs/docs_helpers.py` — add helper, update `validate_operation()`
- Modify: `gdocs/operation_schemas.py` — add schema, update Union
- Modify: `gdocs/managers/batch_operation_manager.py` — add dispatch, update supported_types
- Modify: `gdocs/docs_tools.py` — add to docstring
- Create: `tests/gdocs/test_table_column_properties.py`

- [ ] **Step 1: Write failing tests**

Create `tests/gdocs/test_table_column_properties.py`:

```python
"""
Tests for update_table_column_properties operation in batch_update_doc.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from gdocs.docs_helpers import (
    create_update_table_column_properties_request,
    validate_operation,
)
from gdocs.managers.batch_operation_manager import BatchOperationManager


class TestCreateUpdateTableColumnPropertiesRequest:
    def test_fixed_width(self):
        result = create_update_table_column_properties_request(
            table_start_index=122,
            column_indices=[0],
            width=150.0,
            width_type="FIXED_WIDTH",
        )
        inner = result["updateTableColumnProperties"]
        assert inner["tableStartLocation"] == {"index": 122}
        assert inner["columnIndices"] == [0]
        assert inner["tableColumnProperties"]["width"] == {
            "magnitude": 150.0,
            "unit": "PT",
        }
        assert inner["tableColumnProperties"]["widthType"] == "FIXED_WIDTH"
        assert "width" in inner["fields"]
        assert "widthType" in inner["fields"]

    def test_evenly_distributed(self):
        result = create_update_table_column_properties_request(
            table_start_index=122,
            column_indices=[0, 1, 2],
            width_type="EVENLY_DISTRIBUTED",
        )
        inner = result["updateTableColumnProperties"]
        assert inner["tableColumnProperties"]["widthType"] == "EVENLY_DISTRIBUTED"
        assert inner["columnIndices"] == [0, 1, 2]

    def test_with_tab_id(self):
        result = create_update_table_column_properties_request(
            table_start_index=122,
            column_indices=[0],
            width=100.0,
            tab_id="t.0",
        )
        assert result["updateTableColumnProperties"]["tableStartLocation"]["tabId"] == "t.0"

    def test_width_only(self):
        result = create_update_table_column_properties_request(
            table_start_index=122,
            column_indices=[0],
            width=200.0,
        )
        inner = result["updateTableColumnProperties"]
        assert "width" in inner["fields"]


class TestValidateOperation:
    def test_valid(self):
        is_valid, _ = validate_operation({
            "type": "update_table_column_properties",
            "table_start_index": 122,
            "column_indices": [0],
        })
        assert is_valid

    def test_missing_column_indices(self):
        is_valid, msg = validate_operation({
            "type": "update_table_column_properties",
            "table_start_index": 122,
        })
        assert not is_valid
        assert "column_indices" in msg


class TestBatchManagerIntegration:
    @pytest.fixture()
    def manager(self):
        return BatchOperationManager(Mock())

    def test_build_request(self, manager):
        request, desc = manager._build_operation_request(
            {
                "type": "update_table_column_properties",
                "table_start_index": 122,
                "column_indices": [0],
                "width": 150.0,
                "width_type": "FIXED_WIDTH",
            },
            "update_table_column_properties",
        )
        assert "updateTableColumnProperties" in request
        assert "column" in desc.lower()

    @pytest.mark.asyncio
    async def test_end_to_end(self, manager):
        manager._execute_batch_requests = AsyncMock(return_value={"replies": [{}]})
        success, _, _ = await manager.execute_batch_operations(
            "doc-123",
            [{
                "type": "update_table_column_properties",
                "table_start_index": 122,
                "column_indices": [0],
                "width": 150.0,
            }],
        )
        assert success

    def test_supported_operations_include_column_properties(self, manager):
        supported = manager.get_supported_operations()["supported_operations"]
        assert "update_table_column_properties" in supported
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/gdocs/test_table_column_properties.py -x -q`
Expected: FAIL

- [ ] **Step 3: Add helper function in `docs_helpers.py`**

```python
def create_update_table_column_properties_request(
    table_start_index: int,
    column_indices: list[int],
    width: float = None,
    width_type: str = None,
    tab_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an updateTableColumnProperties request for Google Docs API.

    Args:
        table_start_index: Start index of the target table
        column_indices: List of column indices to update (zero-based)
        width: Column width in points
        width_type: "FIXED_WIDTH" or "EVENLY_DISTRIBUTED"
        tab_id: Optional ID of the tab to target
    """
    location: Dict[str, Any] = {"index": table_start_index}
    if tab_id:
        location["tabId"] = tab_id

    properties: Dict[str, Any] = {}
    fields = []

    if width is not None:
        properties["width"] = {"magnitude": width, "unit": "PT"}
        fields.append("width")

    if width_type is not None:
        properties["widthType"] = width_type
        fields.append("widthType")

    return {
        "updateTableColumnProperties": {
            "tableStartLocation": location,
            "columnIndices": column_indices,
            "tableColumnProperties": properties,
            "fields": ",".join(fields),
        }
    }
```

- [ ] **Step 4: Add to `validate_operation()` required_fields**

```python
        "update_table_column_properties": ["table_start_index", "column_indices"],
```

- [ ] **Step 5: Add Pydantic schema in `operation_schemas.py`**

```python
class UpdateTableColumnPropertiesOperation(StrictDocOperation):
    type: Literal["update_table_column_properties"]
    table_start_index: int
    column_indices: list[int]
    width: Optional[float] = None
    width_type: Optional[str] = None
```

Add to the `BatchDocOperation` Union.

- [ ] **Step 6: Add dispatch clause and imports in `batch_operation_manager.py`**

Add import:

```python
    create_update_table_column_properties_request,
```

Add dispatch clause:

```python
        elif op_type == "update_table_column_properties":
            request = create_update_table_column_properties_request(
                table_start_index=op["table_start_index"],
                column_indices=op["column_indices"],
                width=op.get("width"),
                width_type=op.get("width_type"),
                tab_id=tab_id,
            )
            description = (
                f"update column properties for columns {op['column_indices']} "
                f"in table at {op['table_start_index']}"
            )
```

Add to `supported_types` list and `get_supported_operations()`:

```python
                "update_table_column_properties": {
                    "required": ["table_start_index", "column_indices"],
                    "optional": ["width", "width_type", "tab_id"],
                    "description": "Set column width and distribution for table columns",
                },
```

- [ ] **Step 7: Update docstring in `docs_tools.py`**

```
      update_table_column_properties
                       - required: table_start_index (int), column_indices (list[int])
                         optional: width (float, points), width_type
                                   (FIXED_WIDTH|EVENLY_DISTRIBUTED), tab_id
```

- [ ] **Step 8: Run all table tests**

Run: `uv run python -m pytest tests/gdocs/test_table_column_properties.py tests/gdocs/test_table_merge_operations.py tests/gdocs/test_table_column_operations.py tests/gdocs/test_table_row_operations.py tests/gdocs/test_table_cell_style.py -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add gdocs/docs_helpers.py gdocs/operation_schemas.py gdocs/managers/batch_operation_manager.py gdocs/docs_tools.py tests/gdocs/test_table_column_properties.py
git commit -m "feat(gdocs): add update_table_column_properties to batch_update_doc"
```

---

### Task 6: Run full test suite and final verification

- [ ] **Step 1: Run the full gdocs test suite**

Run: `uv run python -m pytest tests/gdocs/ -v --tb=short`
Expected: All tests pass (except the pre-existing golden file failure in `test_strikethrough.py`)

- [ ] **Step 2: Run ruff linting and formatting**

Run: `uv run ruff check gdocs/ tests/gdocs/ && uv run ruff format --check gdocs/ tests/gdocs/`
Expected: No errors. Fix any issues found.

- [ ] **Step 3: Verify operation count**

The `batch_update_doc` tool should now support 28 operation types (21 existing + 7 new):
- `insert_table_row`
- `delete_table_row`
- `insert_table_column`
- `delete_table_column`
- `merge_table_cells`
- `unmerge_table_cells`
- `update_table_column_properties`

Plus enhanced `update_table_cell_style` with `padding_*` and `content_alignment`.

- [ ] **Step 4: Final commit if any lint/format fixes**

```bash
git add -A
git commit -m "style: auto-fix ruff lint and format"
```
