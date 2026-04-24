import json
from unittest.mock import MagicMock, patch

from ocr_manga_title.schemas import PipelineResult


class TestCLI:
    def test_main_no_args_exits_1(self):
        from ocr_manga_title.cli import main

        with patch("sys.argv", ["cli.py"]):
            try:
                main()
            except SystemExit as e:
                assert e.code == 1

    @patch("ocr_manga_title.cli.OCREngine")
    @patch("ocr_manga_title.cli.load_ocr_config")
    @patch("ocr_manga_title.cli.load_config")
    def test_main_with_valid_image(
        self, mock_load_config, mock_load_ocr_config, mock_engine_cls, tmp_path, capsys
    ):
        from ocr_manga_title.cli import main

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n")

        mock_result = PipelineResult(
            input_path=str(img),
            ocr_results=[],
            extracted=None,
            errors=[],
        )
        mock_engine = MagicMock()
        mock_engine.process.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        with patch("sys.argv", ["cli.py", str(img)]):
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["input_path"] == str(img)

    @patch("ocr_manga_title.cli.OCREngine")
    @patch("ocr_manga_title.cli.load_ocr_config")
    @patch("ocr_manga_title.cli.load_config")
    def test_main_nonexistent_image_exits_1(
        self, mock_load_config, mock_load_ocr_config, mock_engine_cls
    ):
        from ocr_manga_title.cli import main

        mock_engine = MagicMock()
        mock_engine.process.side_effect = FileNotFoundError("not found")
        mock_engine_cls.return_value = mock_engine

        with patch("sys.argv", ["cli.py", "/nonexistent.png"]):
            try:
                main()
            except SystemExit as e:
                assert e.code == 1
