"""Language Detection Module.

Provides unified language detection for all text translation tasks.
Supports:
- User-specified language
- Whisper language detection (from transcription results)
- langdetect-based text detection
- Hybrid detection (Whisper + segment-level detection)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from langdetect import detect, detect_langs, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Ensure langdetect results are reproducible
DetectorFactory.seed = 0


@dataclass
class LanguageDetectionResult:
    """Language detection result data class.

    Attributes:
        primary_language: Primary language code (e.g., "zh", "en")
        primary_language_name: Primary language name (e.g., "Chinese", "English")
        confidence: Confidence score (0.0-1.0)
        is_mixed: Whether mixed languages are detected
        language_distribution: Language distribution {code: percentage}
        detection_method: Detection method (whisper/langdetect/hybrid/user_specified/default)
        all_languages: All detected languages
    """

    primary_language: str  # Primary language code (e.g., "zh", "en")
    primary_language_name: str  # Primary language name (e.g., "Chinese", "English")
    confidence: float  # Confidence (0.0-1.0)
    is_mixed: bool  # Whether mixed languages are detected
    language_distribution: Dict[str, float] = field(
        default_factory=dict
    )  # Language distribution {code: percentage}
    detection_method: str = (
        "unknown"  # Detection method: whisper/langdetect/hybrid/user_specified/default
    )
    all_languages: List[str] = field(default_factory=list)  # All detected languages


class LanguageDetector:
    """Unified language detector for all translation tasks.

    Priority order:
    1. User-specified language
    2. Whisper detection result (from transcription)
    3. langdetect text detection
    4. Default (English)
    """

    def __init__(self, language_map: Dict[str, str]):
        """Initialize the language detector.

        Args:
            language_map: Language code to name mapping (e.g., LANGUAGE_MAP)
        """
        self.language_map = language_map

    def detect(
        self,
        result: Optional[Dict[str, Any]] = None,
        text: Optional[str] = None,
        specified_lang: Optional[str] = None,
        segments: Optional[List[Dict[str, Any]]] = None,
    ) -> LanguageDetectionResult:
        """Detect language using the best available method.

        Args:
            result: Whisper transcription result dict (contains "language" and "language_probability")
            text: Text content to detect
            specified_lang: User-specified language code
            segments: List of segments for mixed language detection

        Returns:
            LanguageDetectionResult: Detection result
        """
        # 1. User-specified language takes priority
        if specified_lang:
            return self._create_specified_result(specified_lang)

        # 2. Use Whisper result if available
        if result:
            whisper_lang = result.get("language")
            if whisper_lang and whisper_lang != "unknown":
                # If segments are available, perform mixed language detection
                if segments:
                    return self._detect_mixed_from_whisper(result, segments)
                return self._create_whisper_result(result)

        # 3. Use langdetect for text
        if text:
            return self._detect_from_text(text)

        # 4. Default to English
        return self._create_default_result()

    def _create_specified_result(self, lang_code: str) -> LanguageDetectionResult:
        """Create a result for user-specified language.

        Args:
            lang_code: Language code specified by user

        Returns:
            LanguageDetectionResult with specified language
        """
        lang_name = self.language_map.get(lang_code, lang_code)
        return LanguageDetectionResult(
            primary_language=lang_code,
            primary_language_name=lang_name,
            confidence=1.0,
            is_mixed=False,
            detection_method="user_specified",
            language_distribution={lang_code: 100.0},
            all_languages=[lang_code],
        )

    def _create_whisper_result(self, result: Dict[str, Any]) -> LanguageDetectionResult:
        """Create a result from Whisper detection.

        Args:
            result: Whisper transcription result dict

        Returns:
            LanguageDetectionResult from Whisper
        """
        lang_code = result.get("language", "unknown")
        probability = result.get("language_probability", 0.0)
        lang_name = self.language_map.get(lang_code, lang_code)

        return LanguageDetectionResult(
            primary_language=lang_code,
            primary_language_name=lang_name,
            confidence=probability,
            is_mixed=False,
            detection_method="whisper",
            language_distribution={lang_code: 100.0},
            all_languages=[lang_code],
        )

    def _detect_from_text(self, text: str) -> LanguageDetectionResult:
        """Detect language from text using langdetect.

        Args:
            text: Text content to analyze

        Returns:
            LanguageDetectionResult from text analysis
        """
        try:
            # Detect all possible languages with probabilities
            lang_probs = detect_langs(text)

            if not lang_probs:
                return self._create_default_result()

            # Get the most likely language
            primary = lang_probs[0]
            lang_code = primary.lang
            confidence = primary.prob
            lang_name = self.language_map.get(lang_code, lang_code)

            # Build language distribution
            distribution = {
                lp.lang: lp.prob * 100
                for lp in lang_probs
                if lp.prob > 0.1  # Only keep languages with probability > 10%
            }

            # Determine if mixed language
            is_mixed = len([p for p in lang_probs if p.prob > 0.2]) > 1

            return LanguageDetectionResult(
                primary_language=lang_code,
                primary_language_name=lang_name,
                confidence=confidence,
                is_mixed=is_mixed,
                detection_method="langdetect",
                language_distribution=distribution,
                all_languages=[lp.lang for lp in lang_probs],
            )

        except (LangDetectException, Exception):
            return self._create_default_result()

    def _detect_mixed_from_whisper(
        self, result: Dict[str, Any], segments: List[Dict[str, Any]]
    ) -> LanguageDetectionResult:
        """Detect mixed language from Whisper result + segment-level detection.

        Strategy:
        1. Use Whisper's detected dominant language
        2. Use langdetect to detect each segment's language
        3. Calculate language distribution

        Args:
            result: Whisper transcription result dict
            segments: List of segment dicts with "text" field

        Returns:
            LanguageDetectionResult with mixed language info
        """
        whisper_lang = result.get("language", "unknown")
        whisper_prob = result.get("language_probability", 0.0)
        lang_name = self.language_map.get(whisper_lang, whisper_lang)

        # Count language for each segment
        lang_counts: Dict[str, int] = {}
        total_segments = 0

        for seg in segments:
            text = seg.get("text", "").strip()
            if not text:
                continue

            try:
                detected = detect(text)
                lang_counts[detected] = lang_counts.get(detected, 0) + 1
                total_segments += 1
            except Exception:
                # Detection failed, use Whisper's result
                lang_counts[whisper_lang] = lang_counts.get(whisper_lang, 0) + 1
                total_segments += 1

        # Calculate language distribution
        if total_segments > 0:
            distribution = {
                lang: (count / total_segments) * 100
                for lang, count in lang_counts.items()
            }

            # Find the language with highest proportion
            primary_lang = max(lang_counts, key=lang_counts.get)

            # Determine if mixed language (secondary language > 20%)
            is_mixed = any(
                pct > 20 for lang, pct in distribution.items() if lang != primary_lang
            )

            return LanguageDetectionResult(
                primary_language=primary_lang,
                primary_language_name=self.language_map.get(primary_lang, primary_lang),
                confidence=whisper_prob,
                is_mixed=is_mixed,
                detection_method="hybrid_whisper_segments",
                language_distribution=distribution,
                all_languages=list(lang_counts.keys()),
            )
        else:
            # No valid segments, fall back to Whisper result
            return self._create_whisper_result(result)

    def _create_default_result(self) -> LanguageDetectionResult:
        """Create a default result (English).

        Returns:
            LanguageDetectionResult with default English language
        """
        return LanguageDetectionResult(
            primary_language="en",
            primary_language_name="English",
            confidence=0.0,
            is_mixed=False,
            detection_method="default",
            language_distribution={"en": 100.0},
            all_languages=["en"],
        )
