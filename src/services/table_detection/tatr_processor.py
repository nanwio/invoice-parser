"""Table Transformer (TATR) processor for table structure detection.

Microsoft's DETR-based model optimized for GPU inference.
Detects table structures (rows, columns, cells) in document images.
"""

import asyncio
from typing import List, Dict, Any, Tuple
import numpy as np
import torch
from PIL import Image
from loguru import logger
from transformers import AutoImageProcessor, TableTransformerForObjectDetection


class TableCell:
    """Represents a detected table cell with position and structure info."""

    def __init__(self, bbox: List[float], row: int, col: int, row_span: int = 1, col_span: int = 1):
        self.bbox = bbox  # [x1, y1, x2, y2] in absolute coordinates
        self.row = row
        self.col = col
        self.row_span = row_span
        self.col_span = col_span

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox,
            "row": self.row,
            "col": self.col,
            "row_span": self.row_span,
            "col_span": self.col_span
        }


class TableDetection:
    """Represents a detected table with its cells."""

    def __init__(self, table_bbox: List[float], cells: List[TableCell]):
        self.bbox = table_bbox  # [x1, y1, x2, y2]
        self.cells = cells

    @property
    def num_rows(self) -> int:
        return max(cell.row + cell.row_span for cell in self.cells) if self.cells else 0

    @property
    def num_cols(self) -> int:
        return max(cell.col + cell.col_span for cell in self.cells) if self.cells else 0


class TATRProcessor:
    """Table Transformer processor with GPU optimization."""

    MODEL_NAME = "microsoft/table-transformer-structure-recognition"

    def __init__(self, device: str = None, confidence_threshold: float = 0.7):
        """Initialize TATR with GPU support.

        Args:
            device: 'cuda' or 'cpu' (auto-detect if None)
            confidence_threshold: Min confidence for cell detection (0.7 recommended)
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.confidence_threshold = confidence_threshold

        logger.info(f"Loading Table Transformer model on {self.device}...")

        self.image_processor = AutoImageProcessor.from_pretrained(self.MODEL_NAME)
        self.model = TableTransformerForObjectDetection.from_pretrained(self.MODEL_NAME)
        self.model.to(self.device)
        self.model.eval()

        # Enable inference optimizations
        if self.device == "cuda":
            torch.backends.cudnn.benchmark = True

        logger.info(f"Table Transformer initialized (device={self.device}, threshold={confidence_threshold})")

    async def detect_tables_async(self, image: Image.Image) -> List[TableDetection]:
        """Detect table structures in image (async wrapper).

        Args:
            image: PIL Image (RGB)

        Returns:
            List of TableDetection objects
        """
        return await asyncio.to_thread(self._detect_tables_sync, image)

    def _detect_tables_sync(self, image: Image.Image) -> List[TableDetection]:
        """Synchronous table detection (runs in thread pool)."""

        # Preprocess image
        inputs = self.image_processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Post-process predictions
        target_sizes = torch.tensor([image.size[::-1]]).to(self.device)  # (height, width)
        results = self.image_processor.post_process_object_detection(
            outputs,
            threshold=self.confidence_threshold,
            target_sizes=target_sizes
        )[0]

        # Extract table structures
        tables = self._parse_table_structure(results, image.size)

        logger.debug(f"Detected {len(tables)} tables with total {sum(len(t.cells) for t in tables)} cells")

        return tables

    def _parse_table_structure(self, results: Dict, image_size: Tuple[int, int]) -> List[TableDetection]:
        """Parse TATR output into structured table objects.

        TATR detects: table, table row, table column, table projected row header, table spanning cell
        We focus on: table (bounding box) + cells (intersection of rows/cols)
        """
        boxes = results["boxes"].cpu().numpy()
        labels = results["labels"].cpu().numpy()
        scores = results["scores"].cpu().numpy()

        # Get label mapping
        id2label = self.model.config.id2label

        # Separate detections by type
        table_boxes = []
        row_boxes = []
        col_boxes = []

        for box, label, score in zip(boxes, labels, scores):
            label_name = id2label[label]

            if label_name == "table":
                table_boxes.append(box)
            elif label_name == "table row":
                row_boxes.append(box)
            elif label_name == "table column":
                col_boxes.append(box)

        # Create table detections
        tables = []

        for table_box in table_boxes:
            # Get rows and columns within this table
            table_rows = self._filter_boxes_in_table(row_boxes, table_box)
            table_cols = self._filter_boxes_in_table(col_boxes, table_box)

            # Sort rows top-to-bottom, columns left-to-right
            table_rows = sorted(table_rows, key=lambda b: b[1])  # sort by y1
            table_cols = sorted(table_cols, key=lambda b: b[0])  # sort by x1

            # Generate cells from row/col intersections
            cells = self._generate_cells(table_rows, table_cols)

            tables.append(TableDetection(table_box.tolist(), cells))

        return tables

    def _filter_boxes_in_table(self, boxes: List[np.ndarray], table_box: np.ndarray) -> List[np.ndarray]:
        """Filter boxes that are inside the table boundary."""
        filtered = []
        tx1, ty1, tx2, ty2 = table_box

        for box in boxes:
            bx1, by1, bx2, by2 = box
            # Check if box center is inside table
            center_x = (bx1 + bx2) / 2
            center_y = (by1 + by2) / 2

            if tx1 <= center_x <= tx2 and ty1 <= center_y <= ty2:
                filtered.append(box)

        return filtered

    def _generate_cells(self, rows: List[np.ndarray], cols: List[np.ndarray]) -> List[TableCell]:
        """Generate cell objects from row/column intersections."""
        cells = []

        for row_idx, row_box in enumerate(rows):
            for col_idx, col_box in enumerate(cols):
                # Cell bbox is intersection of row and column
                x1 = float(col_box[0])
                y1 = float(row_box[1])
                x2 = float(col_box[2])
                y2 = float(row_box[3])

                cell = TableCell(
                    bbox=[x1, y1, x2, y2],
                    row=row_idx,
                    col=col_idx
                )
                cells.append(cell)

        return cells
