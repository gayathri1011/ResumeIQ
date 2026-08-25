from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.resume_factory import (
    create_corrupted_file,
    create_empty_pdf,
    create_sample_docx,
    create_sample_pdf,
)


@pytest.fixture
def fixtures_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "fixtures"
    directory.mkdir()
    return directory


@pytest.fixture
def sample_pdf(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "sample_resume.pdf"
    create_sample_pdf(path)
    return path


@pytest.fixture
def sample_docx(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "sample_resume.docx"
    create_sample_docx(path)
    return path


@pytest.fixture
def empty_pdf(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "empty.pdf"
    create_empty_pdf(path)
    return path


@pytest.fixture
def corrupted_pdf(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "corrupted.pdf"
    create_corrupted_file(path)
    return path
