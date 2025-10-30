"""Overall quality scorer."""


class QualityScorer:
    """Calculates overall quality score."""

    SHARPNESS_THRESHOLD = 100.0
    CONTRAST_THRESHOLD = 50.0
    ROTATION_THRESHOLD = 2.0
    NOISE_THRESHOLD = 30.0

    @staticmethod
    def calculate_score(
        sharpness: float,
        contrast: float,
        rotation: float,
        noise: float,
        is_scan: bool
    ) -> float:
        """
        Calculate overall quality score (0-100).

        Args:
            sharpness: Sharpness score
            contrast: Contrast score
            rotation: Rotation angle
            noise: Noise level
            is_scan: Whether image is likely a scan

        Returns:
            Overall quality score (0-100)
        """
        score = 100.0

        if sharpness < QualityScorer.SHARPNESS_THRESHOLD:
            score -= (QualityScorer.SHARPNESS_THRESHOLD - sharpness) / 2

        if contrast < QualityScorer.CONTRAST_THRESHOLD:
            score -= (QualityScorer.CONTRAST_THRESHOLD - contrast) / 2

        if abs(rotation) > QualityScorer.ROTATION_THRESHOLD:
            score -= abs(rotation) * 2

        if noise > QualityScorer.NOISE_THRESHOLD:
            score -= (noise - QualityScorer.NOISE_THRESHOLD)

        if is_scan:
            score += 10.0

        return float(max(0.0, min(100.0, score)))
