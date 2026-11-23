#!/usr/bin/env python3
"""Verify the public reports before moving them between daily-demo jobs."""
import argparse
import os
from pathlib import Path

from check_secrets import PATTERNS


LANGUAGES = ('zh', 'en', 'ru')
REQUIRED_SECTIONS = ('trials', 'conferences', 'ai-summary', 'research-activity')


def verify(folder: Path, key: bytes = b'') -> None:
    for lang in LANGUAGES:
        page = (folder / f'latest-report.{lang}.html').read_bytes()
        if any(f'id="{section}"'.encode() not in page for section in REQUIRED_SECTIONS):
            raise ValueError(f'{lang}: required report section is missing')
        if b'id="prompt"' in page or 'data-no-i18n>🗓️ 学术会议'.encode() in page:
            raise ValueError(f'{lang}: private prompt or untranslated heading in public report')
        if (key and key in page) or any(pattern.search(page) for pattern in PATTERNS):
            raise ValueError(f'{lang}: credential detected in public report')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    try:
        verify(args.folder, os.environ.get('DEEPSEEK_API_KEY', '').encode())
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
    print('Public report sections and credentials checked in all three languages.')
