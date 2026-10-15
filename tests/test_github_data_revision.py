# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 22:47:56 2026

@author: mohak
"""


import ast
import inspect

import pandas as pd

from api.data.github_data import ResearchDataRepository
from api.research.executor import execute_research


REVISION = "a" * 40


def test_tree_uses_requested_revision(monkeypatch):
    repository = ResearchDataRepository()
    requested_urls = []

    def fake_request(url, *args, **kwargs):
        requested_urls.append(url)
        return b'{"tree": []}'

    monkeypatch.setattr(repository, "_request", fake_request)

    assert repository._tree(REVISION) == []
    assert f"/git/trees/{REVISION}?recursive=1" in requested_urls[0]


def test_load_parquet_uses_requested_revision(monkeypatch):
    repository = ResearchDataRepository()
    requested = {}

    def fake_request(url, accept=None):
        requested["url"] = url
        requested["accept"] = accept
        return b"fake-parquet-content"

    monkeypatch.setattr(repository, "_request", fake_request)
    monkeypatch.setattr(
        pd,
        "read_parquet",
        lambda buffer: pd.DataFrame({"CLOSE": [100.0]}),
    )

    result = repository.load_parquet(
        "processed/nifty_50.parquet",
        ref=REVISION,
    )

    assert f"?ref={REVISION}" in requested["url"]
    assert result["CLOSE"].tolist() == [100.0]


def test_load_bhavcopy_pins_tree_and_file_download(monkeypatch):
    repository = ResearchDataRepository()
    tree_revisions = []
    download_calls = []

    path = (
        "processed/bhavcopy/"
        "sec_bhavdata_full_02012024.parquet"
    )

    def fake_tree(ref=None):
        tree_revisions.append(ref)
        return [{"path": path}]

    def fake_download(file_date, file_path, ref=None):
        download_calls.append((file_date, file_path, ref))
        return pd.DataFrame(
            {
                "SYMBOL": ["ABC"],
                "TIMESTAMP": [pd.Timestamp("2024-01-02")],
                "CLOSE": [100.0],
            }
        )

    monkeypatch.setattr(repository, "_tree", fake_tree)
    monkeypatch.setattr(
        repository,
        "_download_bhavcopy_file",
        fake_download,
    )

    result = repository.load_bhavcopy(
        "2024-01-02",
        "2024-01-02",
        ref=REVISION,
    )

    assert tree_revisions == [REVISION]
    assert len(download_calls) == 1
    assert download_calls[0][1] == path
    assert download_calls[0][2] == REVISION
    assert result["SYMBOL"].tolist() == ["ABC"]


def test_load_mto_uses_requested_revision(monkeypatch):
    repository = ResearchDataRepository()
    tree_revisions = []
    requested_urls = []

    path = "raw/nse/mto/MTO_02012024.DAT"

    def fake_tree(ref=None):
        tree_revisions.append(ref)
        return [{"path": path}]

    def fake_request(url, accept=None):
        requested_urls.append(url)
        return b"20,EQ,ABC,unused,1000,500,50"

    monkeypatch.setattr(repository, "_tree", fake_tree)
    monkeypatch.setattr(repository, "_request", fake_request)

    result = repository.load_mto(
        "2024-01-02",
        "2024-01-02",
        ref=REVISION,
    )

    assert tree_revisions == [REVISION]
    assert len(requested_urls) == 1
    assert f"/{REVISION}/{path}" in requested_urls[0]
    assert result["SYMBOL"].tolist() == ["ABC"]


def test_executor_passes_recorded_revision_to_all_loaders():
    source = inspect.getsource(execute_research)
    tree = ast.parse(source)

    expected_loaders = {
        "load_bhavcopy",
        "load_mto",
        "load_parquet",
    }
    verified = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function = node.func
        if not (
            isinstance(function, ast.Attribute)
            and function.attr in expected_loaders
        ):
            continue

        ref_argument = next(
            (
                keyword.value
                for keyword in node.keywords
                if keyword.arg == "ref"
            ),
            None,
        )

        assert isinstance(ref_argument, ast.Name), (
            f"{function.attr} must receive ref=data_revision"
        )
        assert ref_argument.id == "data_revision"
        verified.add(function.attr)

    assert verified == expected_loaders
