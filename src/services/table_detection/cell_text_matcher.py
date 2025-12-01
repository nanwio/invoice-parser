"""Cell-text matching using vectorized IoU and centroid fallback.

Matches OCR-detected text boxes to table cells using:
1. IoU (Intersection over Union) for overlapping texts
2. Centroid containment for small texts in large cells

Performance: <100ms for typical invoice (200 texts, 50 cells)
"""

from typing import List, Dict, Tuple
import numpy as np
from loguru import logger


class TextBox:
    """OCR-detected text with bounding box."""

    def __init__(self, text: str, bbox: List[float], confidence: float = 1.0):
        self.text = text
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence

    @property
    def centroid(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)


class CellTextMatcher:
    """Matches OCR texts to table cells using hybrid strategy."""

    @staticmethod
    def vectorized_iou(boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
        """Compute IoU between two sets of boxes using pure numpy vectorization.

        Args:
            boxes1: Array of shape (N, 4) with format [x1, y1, x2, y2]
            boxes2: Array of shape (M, 4) with format [x1, y1, x2, y2]

        Returns:
            IoU matrix of shape (N, M)

        Performance: ~0.5ms for 200x50 boxes on CPU
        """
        boxes1_exp = boxes1[:, np.newaxis, :]  # (N, 1, 4)
        boxes2_exp = boxes2[np.newaxis, :, :]  # (1, M, 4)

        # Compute intersection coordinates
        x1_inter = np.maximum(boxes1_exp[:, :, 0], boxes2_exp[:, :, 0])
        y1_inter = np.maximum(boxes1_exp[:, :, 1], boxes2_exp[:, :, 1])
        x2_inter = np.minimum(boxes1_exp[:, :, 2], boxes2_exp[:, :, 2])
        y2_inter = np.minimum(boxes1_exp[:, :, 3], boxes2_exp[:, :, 3])

        # Compute intersection area
        inter_width = np.maximum(0.0, x2_inter - x1_inter)
        inter_height = np.maximum(0.0, y2_inter - y1_inter)
        inter_area = inter_width * inter_height

        # Compute areas
        area1 = (boxes1[:, 2] - boxes1[:, 0]) * (boxes1[:, 3] - boxes1[:, 1])
        area2 = (boxes2[:, 2] - boxes2[:, 0]) * (boxes2[:, 3] - boxes2[:, 1])

        # Compute union
        union_area = area1[:, np.newaxis] + area2[np.newaxis, :] - inter_area

        # Compute IoU (avoid division by zero)
        iou = np.divide(inter_area, union_area, out=np.zeros_like(inter_area), where=union_area > 0)

        return iou

    @staticmethod
    def point_in_box(points: np.ndarray, boxes: np.ndarray) -> np.ndarray:
        """Check if points are inside boxes (vectorized).

        Args:
            points: Array of shape (N, 2) with format [x, y]
            boxes: Array of shape (M, 4) with format [x1, y1, x2, y2]

        Returns:
            Boolean matrix of shape (N, M)
        """
        points_exp = points[:, np.newaxis, :]  # (N, 1, 2)
        boxes_exp = boxes[np.newaxis, :, :]    # (1, M, 4)

        x_in = (points_exp[:, :, 0] >= boxes_exp[:, :, 0]) & (points_exp[:, :, 0] <= boxes_exp[:, :, 2])
        y_in = (points_exp[:, :, 1] >= boxes_exp[:, :, 1]) & (points_exp[:, :, 1] <= boxes_exp[:, :, 3])

        return x_in & y_in

    @staticmethod
    def match_texts_to_cells(
        text_boxes: List[TextBox],
        cell_boxes: List[Tuple[int, int, List[float]]],  # [(row, col, bbox), ...]
        iou_threshold: float = 0.5,
        use_centroid_fallback: bool = True
    ) -> Dict[Tuple[int, int], List[str]]:
        """Match text boxes to table cells using hybrid strategy.

        Strategy:
        1. Primary: IoU-based matching (texts with significant overlap)
        2. Fallback: Centroid-based matching (small texts in large cells)

        Args:
            text_boxes: List of TextBox objects from OCR
            cell_boxes: List of (row, col, bbox) tuples from TATR
            iou_threshold: Minimum IoU for matching (default 0.5)
            use_centroid_fallback: Enable centroid fallback for unmatched texts

        Returns:
            Dict mapping (row, col) to list of text strings
        """
        if not text_boxes or not cell_boxes:
            return {}

        # Convert to numpy arrays
        text_bbox_array = np.array([tb.bbox for tb in text_boxes], dtype=np.float32)
        cell_bbox_array = np.array([cb[2] for cb in cell_boxes], dtype=np.float32)

        # Compute IoU matrix
        iou_matrix = CellTextMatcher.vectorized_iou(text_bbox_array, cell_bbox_array)

        # Initialize result dictionary
        cell_texts: Dict[Tuple[int, int], List[str]] = {}
        for row, col, _ in cell_boxes:
            cell_texts[(row, col)] = []

        # Track matched texts
        matched_texts = set()

        # Strategy 1: IoU-based matching
        for text_idx, text_box in enumerate(text_boxes):
            iou_scores = iou_matrix[text_idx]
            best_cell_idx = int(np.argmax(iou_scores))
            best_iou = iou_scores[best_cell_idx]

            if best_iou >= iou_threshold:
                row, col, _ = cell_boxes[best_cell_idx]
                cell_texts[(row, col)].append(text_box.text)
                matched_texts.add(text_idx)

        # Strategy 2: Centroid fallback for unmatched texts
        if use_centroid_fallback:
            unmatched_indices = [i for i in range(len(text_boxes)) if i not in matched_texts]

            if unmatched_indices:
                # Get centroids of unmatched texts
                unmatched_centroids = np.array([text_boxes[i].centroid for i in unmatched_indices], dtype=np.float32)

                # Check containment
                containment_matrix = CellTextMatcher.point_in_box(unmatched_centroids, cell_bbox_array)

                for centroid_idx, text_idx in enumerate(unmatched_indices):
                    contained_cells = np.where(containment_matrix[centroid_idx])[0]

                    if len(contained_cells) > 0:
                        # If multiple cells contain centroid, pick the smallest one
                        cell_areas = [
                            (cell_bbox_array[ci, 2] - cell_bbox_array[ci, 0]) *
                            (cell_bbox_array[ci, 3] - cell_bbox_array[ci, 1])
                            for ci in contained_cells
                        ]
                        best_cell_idx = contained_cells[np.argmin(cell_areas)]

                        row, col, _ = cell_boxes[best_cell_idx]
                        cell_texts[(row, col)].append(text_boxes[text_idx].text)
                        matched_texts.add(text_idx)

        # Log matching statistics
        total_texts = len(text_boxes)
        matched_count = len(matched_texts)
        logger.debug(f"Matched {matched_count}/{total_texts} texts to {len(cell_boxes)} cells "
                    f"({matched_count/total_texts*100:.1f}% coverage)")

        # Sort texts in each cell (left-to-right, top-to-bottom)
        for cell_key in cell_texts:
            cell_bbox = next(cb[2] for cb in cell_boxes if (cb[0], cb[1]) == cell_key)
            cell_text_boxes = [
                text_boxes[i] for i in range(len(text_boxes))
                if i in matched_texts and text_boxes[i].text in cell_texts[cell_key]
            ]

            # Sort by vertical position first (top-to-bottom), then horizontal (left-to-right)
            sorted_boxes = sorted(cell_text_boxes, key=lambda tb: (tb.bbox[1], tb.bbox[0]))
            cell_texts[cell_key] = [tb.text for tb in sorted_boxes]

        return cell_texts

    @staticmethod
    def format_table_as_toon(
        cell_texts: Dict[Tuple[int, int], List[str]],
        num_rows: int,
        num_cols: int,
        page_num: int,
        table_num: int
    ) -> str:
        """Format matched table as TOON (Token-Oriented Object Notation).

        Args:
            cell_texts: Dict mapping (row, col) to text strings
            num_rows: Total number of rows
            num_cols: Total number of columns
            page_num: Page number
            table_num: Table number on page

        Returns:
            TOON-formatted string
        """
        lines = [f"TABLE {table_num} (Page {page_num}):"]

        for row in range(num_rows):
            row_cells = []
            for col in range(num_cols):
                texts = cell_texts.get((row, col), [])
                cell_content = " ".join(texts) if texts else ""
                row_cells.append(cell_content)

            lines.append(" | ".join(row_cells))

        return "\n".join(lines)

    @staticmethod
    def format_table_as_json(
        cell_texts: Dict[Tuple[int, int], List[str]],
        num_rows: int,
        num_cols: int
    ) -> List[List[str]]:
        """Format matched table as 2D array (for JSON serialization).

        Args:
            cell_texts: Dict mapping (row, col) to text strings
            num_rows: Total number of rows
            num_cols: Total number of columns

        Returns:
            2D list of strings
        """
        table = []

        for row in range(num_rows):
            row_data = []
            for col in range(num_cols):
                texts = cell_texts.get((row, col), [])
                cell_content = " ".join(texts) if texts else ""
                row_data.append(cell_content)
            table.append(row_data)

        return table
