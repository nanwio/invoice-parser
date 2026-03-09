"""Scan vs photo classifier."""


class ScanDetector:
    """Determines if image is likely a scan vs a photo."""

    @staticmethod
    def is_scan(sharpness: float, contrast: float, noise: float) -> bool:
        """
        Determine if image is likely a scan.

        Args:
            sharpness: Sharpness score
            contrast: Contrast score
            noise: Noise level

        Returns:
            True if likely a scan, False if likely a photo
        """
        scan_indicators = 0

        if sharpness > 150.0:
            scan_indicators += 1
        if contrast > 60.0:
            scan_indicators += 1
        if noise < 15.0:
            scan_indicators += 1

        return scan_indicators >= 2
