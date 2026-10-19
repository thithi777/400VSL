"""So sánh động tác người học với video mẫu (DTW theo bộ phận) và sinh nhận xét tiếng Việt."""
from .compare import compare_sequences, load_calibration
from .feedback import build_feedback, headline, verdict_of
from .features import PARTS

__all__ = ["PARTS", "build_feedback", "compare_sequences", "headline", "load_calibration", "verdict_of"]
