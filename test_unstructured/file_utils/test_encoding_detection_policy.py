"""Regression coverage for encoding uncertainty and the fallback in issue #4466."""

import codecs
import io
import warnings
from unittest.mock import patch

import pytest

from unstructured.errors import UnprocessableEntityError
from unstructured.file_utils import encoding as subject

ISSUE_SAMPLES = [
    ("会議室予約", "shift_jis"),
    ("café très à Paris", "iso_8859_1"),
    ("Bonjour, ça va très bien. Le café est déjà prêt.", "iso_8859_1"),
]

LEGACY_SAMPLES = ISSUE_SAMPLES + [
    ("Привет, как дела? Это тестовое сообщение для проверки.", "cp1251"),
    ("สวัสดีครับ ยินดีต้อนรับสู่ห้องประชุมของเรา", "cp874"),
    ("髙﨑様と﨑山様が来社されました。", "cp932"),
    ("점심 메뉴는 똠얌꿍으로 예약했습니다.", "cp949"),
    ("Türkçe bir cümle: şu güzel çiçekler İstanbul.", "cp1254"),
    ("Příliš žluťoučký kůň úpěl ďábelské ódy.", "cp1250"),
    ("Ελληνικό κείμενο για δοκιμή της κωδικοποίησης.", "cp1253"),
    ("مرحبا بكم في هذا الاجتماع المهم اليوم.", "cp1256"),
    ("“Hello,” she said — it’s a beautiful day.", "cp1252"),
]


def source_kwargs(payload, via, tmp_path):
    if via == "filename":
        path = tmp_path / "sample.txt"
        path.write_bytes(payload)
        return {"filename": str(path)}
    return {"file": payload if via == "bytes" else io.BytesIO(payload)}


@pytest.mark.parametrize(("text", "encoding"), ISSUE_SAMPLES)
@pytest.mark.parametrize("via", ["filename", "bytes", "stream"])
def test_issue_samples_do_not_silently_return_guessed_text(text, encoding, via, tmp_path):
    with pytest.warns(UserWarning, match="encoding was inferred") as caught:
        subject.detect_file_encoding(**source_kwargs(text.encode(encoding), via, tmp_path))

    assert len(caught) == 1
    assert caught[0].category is subject.EncodingDetectionWarning
    assert "encoding=" in str(caught[0].message)
    assert text not in str(caught[0].message)


@pytest.mark.parametrize(("text", "encoding"), ISSUE_SAMPLES)
def test_callers_can_reject_statistical_decoding(text, encoding):
    with warnings.catch_warnings():
        warnings.simplefilter("error", subject.EncodingDetectionWarning)
        with pytest.raises(subject.EncodingDetectionWarning):
            subject.detect_file_encoding(file=text.encode(encoding))


@pytest.mark.parametrize(("text", "encoding"), LEGACY_SAMPLES)
@pytest.mark.parametrize("via", ["filename", "bytes", "stream"])
def test_explicit_encoding_is_authoritative(text, encoding, via, tmp_path):
    with warnings.catch_warnings(), patch.object(subject, "detect") as detect:
        warnings.simplefilter("error")
        _, actual = subject.read_txt_file(
            **source_kwargs(text.encode(encoding), via, tmp_path),
            encoding=encoding,
        )
    assert actual == text
    detect.assert_not_called()


@pytest.mark.parametrize(("text", "encoding"), LEGACY_SAMPLES[3:])
def test_valid_detected_codecs_are_not_rejected_by_a_common_encoding_allowlist(text, encoding):
    with (
        patch.object(subject, "detect", return_value={"encoding": encoding, "confidence": 1.0}),
        patch.object(subject, "COMMON_ENCODINGS", ["utf_8"]),
        pytest.warns(UserWarning, match="encoding was inferred"),
    ):
        _, actual = subject.detect_file_encoding(file=text.encode(encoding))
    assert actual == text


@pytest.mark.parametrize("via", ["filename", "bytes", "stream"])
@pytest.mark.parametrize("confidence", [None, 0.1])
def test_fallback_ranks_actual_candidates_instead_of_using_latin1(via, confidence, tmp_path):
    text = "髙﨑様と﨑山様が来社されました。"
    with (
        patch.object(
            subject, "detect", return_value={"encoding": "cp932", "confidence": confidence}
        ),
        pytest.warns(UserWarning, match="encoding was inferred"),
    ):
        _, actual = subject.detect_file_encoding(
            **source_kwargs(text.encode("cp932"), via, tmp_path),
        )
    assert actual == text


@pytest.mark.parametrize("via", ["filename", "bytes", "stream"])
def test_binary_junk_is_not_accepted_by_latin1(via, tmp_path):
    with patch.object(subject, "detect", return_value={"encoding": None, "confidence": None}):
        with pytest.raises(UnprocessableEntityError, match="Unable to determine file encoding"):
            subject.detect_file_encoding(**source_kwargs(bytes(range(256)) * 4, via, tmp_path))


@pytest.mark.parametrize(
    ("bom", "encoding"),
    [
        (codecs.BOM_UTF8, "utf-8"),
        (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
        (codecs.BOM_UTF32_LE, "utf-32-le"),
        (codecs.BOM_UTF32_BE, "utf-32-be"),
    ],
)
@pytest.mark.parametrize("via", ["filename", "bytes", "stream"])
def test_bom_takes_precedence_without_statistical_detection(bom, encoding, via, tmp_path):
    text = "会議室予約 / café / 🦊"
    with warnings.catch_warnings(), patch.object(subject, "detect") as detect:
        warnings.simplefilter("error")
        _, actual = subject.detect_file_encoding(
            **source_kwargs(bom + text.encode(encoding), via, tmp_path),
        )
    assert actual == text
    detect.assert_not_called()


@pytest.mark.parametrize("text", ["ASCII text", "café 会議室 🦊", ""])
@pytest.mark.parametrize("via", ["filename", "bytes", "stream"])
def test_utf8_and_empty_input_need_no_warning(text, via, tmp_path):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _, actual = subject.detect_file_encoding(
            **source_kwargs(text.encode("utf-8"), via, tmp_path)
        )
    assert actual == text


@pytest.mark.parametrize("char", ["​", "­", " ", "—", "中"])
@pytest.mark.parametrize("via", ["filename", "bytes", "stream"])
def test_valid_utf8_is_not_overridden_by_a_confident_detector(char, via, tmp_path):
    # -- charset_normalizer reports mac_iceland / cp850 at confidence 1.0 for the first two --
    text = f"The protocol identifier is PU-7788-ZX and it must be unique.{char}\n"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        encoding, actual = subject.detect_file_encoding(
            **source_kwargs(text.encode("utf-8"), via, tmp_path)
        )
    assert (encoding, actual) == ("utf-8", text)


BOM_LESS_UTF16_32 = ["utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"]
# -- NUL-padded ASCII is valid UTF-8; U+8ACB in UTF-16LE is `CB 8A`, valid UTF-8 for U+02CA --
NUL_PADDED_TEXTS = ["Meeting notes: 請\n", "hello world"]


@pytest.mark.parametrize("text", NUL_PADDED_TEXTS)
@pytest.mark.parametrize("encoding", BOM_LESS_UTF16_32)
@pytest.mark.parametrize("via", ["filename", "bytes", "stream"])
def test_bom_less_utf16_and_utf32_are_not_claimed_by_the_utf8_check(text, encoding, via, tmp_path):
    with (
        patch.object(subject, "detect", return_value={"encoding": encoding, "confidence": 1.0}),
        pytest.warns(UserWarning, match="encoding was inferred"),
    ):
        _, actual = subject.detect_file_encoding(
            **source_kwargs(text.encode(encoding), via, tmp_path)
        )
    assert actual == text


@pytest.mark.parametrize("text", NUL_PADDED_TEXTS)
@pytest.mark.parametrize("encoding", BOM_LESS_UTF16_32)
def test_callers_can_reject_bom_less_utf16_and_utf32(text, encoding):
    with (
        patch.object(subject, "detect", return_value={"encoding": encoding, "confidence": 1.0}),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("error", subject.EncodingDetectionWarning)
        with pytest.raises(subject.EncodingDetectionWarning):
            subject.detect_file_encoding(file=text.encode(encoding))


@pytest.mark.parametrize(
    "payload",
    [
        codecs.BOM_UTF16_LE + "aaa\U0001f600".encode("utf-16-le"),
        codecs.BOM_UTF16_BE + "aaa\U0001f600".encode("utf-16-be"),
        codecs.BOM_UTF8 + "aaa\U0001f600".encode("utf-8"),
        "aaa\U0001f600".encode("utf-8"),
    ],
)
def test_a_prefix_may_end_inside_a_multibyte_sequence(payload):
    assert subject.detect_file_encoding(file=payload[:-1], final=False)[1] == "aaa"


def test_a_prefix_still_rejects_an_invalid_byte_before_its_end():
    with pytest.raises(UnprocessableEntityError, match="decode failed"):
        subject.detect_file_encoding(file=codecs.BOM_UTF8 + b"a\xffa", final=False)


def test_invalid_detected_codec_has_a_lightweight_error():
    with patch.object(
        subject, "detect", return_value={"encoding": "not-a-codec", "confidence": 1.0}
    ):
        with pytest.raises(UnprocessableEntityError, match="decode failed") as caught:
            subject.detect_file_encoding(file=b"example")
    assert not hasattr(caught.value, "object")


def test_incorrect_explicit_encoding_is_not_replaced_by_a_guess():
    with patch.object(subject, "detect") as detect:
        with pytest.raises(UnicodeDecodeError):
            subject.read_txt_file(file="会議室予約".encode("shift_jis"), encoding="utf-8")
    detect.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        codecs.BOM_UTF8 + b"\xff",
        codecs.BOM_UTF16_LE + b"A",
        codecs.BOM_UTF16_BE + b"A",
        codecs.BOM_UTF32_LE + b"A\x00",
        codecs.BOM_UTF32_BE + b"\x00A",
    ],
)
def test_malformed_unicode_with_a_bom_is_not_reinterpreted(payload):
    with patch.object(subject, "detect") as detect:
        with pytest.raises(UnprocessableEntityError, match="decode failed") as caught:
            subject.detect_file_encoding(file=payload)
    detect.assert_not_called()
    assert not hasattr(caught.value, "object")


@pytest.mark.parametrize("codec", ["UTF_8", "utf8", "UTF-8-SIG", "US-ASCII"])
def test_utf8_and_ascii_aliases_do_not_warn(codec):
    with (
        patch.object(subject, "detect", return_value={"encoding": codec, "confidence": 1.0}),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("error")
        assert subject.detect_file_encoding(file=b"text")[1] == "text"


def test_fallback_uses_the_same_byte_snapshot_for_paths_and_streams(tmp_path):
    text = "髙﨑様と﨑山様が来社されました。\r\n髙﨑様と﨑山様。\r"
    payload = text.encode("cp932")
    with (
        patch.object(subject, "detect", return_value={"encoding": None, "confidence": None}),
        warnings.catch_warnings(),
    ):
        warnings.simplefilter("ignore", subject.EncodingDetectionWarning)
        results = [
            subject.detect_file_encoding(**source_kwargs(payload, via, tmp_path))[1]
            for via in ["filename", "bytes", "stream"]
        ]
    assert results == [text] * 3


@pytest.mark.parametrize("via", ["filename", "bytes", "stream"])
def test_explicit_encoding_accepts_an_empty_document(via, tmp_path):
    assert subject.read_txt_file(**source_kwargs(b"", via, tmp_path), encoding="utf-8")[1] == ""
