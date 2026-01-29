"""E2Eテスト: 音声選択機能（4種類のプリセット）"""
import base64
import os
import socket
import subprocess
import time
from pathlib import Path

import fitz
import pytest
import requests
from PIL import Image


def _wait_port(host: str, port: int, *, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.1)
    raise TimeoutError(f"HTTPサーバーが起動しませんでした: {host}:{port} ({last_err})")


def _make_sample_pdf(path: Path, *, pages: int = 1, width: float = 1280, height: float = 720) -> None:
    doc = fitz.open()
    try:
        for i in range(pages):
            page = doc.new_page(width=width, height=height)
            page.insert_text((72, 72), f"Slide {i+1}")
        doc.save(path)
    finally:
        doc.close()


@pytest.mark.e2e
def test_voice_selection_all_presets(tmp_path: Path) -> None:
    """4種類の音声プリセットすべてが音声生成可能であることを確認"""
    repo_root = Path(__file__).resolve().parents[2]

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1ページのテストPDFを作成
    pdf_path = tmp_path / "test_voice.pdf"
    _make_sample_pdf(pdf_path, pages=1)

    # PDFを画像に変換（Base64エンコード）
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        img_data = f"data:image/png;base64,{img_b64}"
    finally:
        doc.close()

    host = "127.0.0.1"
    port = 8124

    base_url = f"http://{host}:{port}"

    env = os.environ.copy()
    env["SVM_INPUT_DIR"] = str(input_dir)
    env["SVM_OUTPUT_DIR"] = str(output_dir)
    env["USE_VP8"] = "1"
    env["OUTPUT_FPS"] = "5"
    env["SLIDE_RENDER_SCALE"] = "1.0"
    env["SILENCE_SLIDE_DURATION"] = "0.5"

    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        cmd = [str(venv_python)]
    else:
        cmd = ["py", "-3.10"]

    server = subprocess.Popen(
        cmd
        + [
            "-m",
            "uvicorn",
            "src.server:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_port(host, port, timeout_s=30.0)

        # 音声プリセット4種類をテスト
        voice_presets = [
            "女声1",
            "女声2",
            "女声3",
            "男声1",
        ]

        for voice in voice_presets:
            print(f"\nTesting voice preset: {voice}")

            # 音声生成APIを呼び出し
            payload = {
                "output_name": "test_voice",
                "slide_index": 0,
                "script": "これはテスト音声です。",
                "image_data": img_data,
                "resolution": "720p",
                "voice_gender": voice,
            }

            res = requests.post(
                f"{base_url}/api/generate_audio",
                json=payload,
                timeout=60,
            )

            # ステータスコード確認
            assert res.status_code == 200, f"音声生成失敗（{voice}）: {res.status_code} {res.text}"

            # レスポンスJSON確認
            data = res.json()
            assert "audio_url" in data, f"audio_urlが返されませんでした（{voice}）"

            # 音声ファイルが生成されていることを確認
            audio_path = data.get("path")
            if audio_path:
                assert Path(audio_path).exists(), f"音声ファイルが存在しません（{voice}）: {audio_path}"
                assert Path(audio_path).stat().st_size > 0, f"音声ファイルが空です（{voice}）: {audio_path}"
                print(f"✓ {voice}: 音声生成成功（{Path(audio_path).stat().st_size} bytes）")

    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


@pytest.mark.e2e
def test_voice_mapping_consistency(tmp_path: Path) -> None:
    """音声プリセットのマッピング/デフォルト適用が一貫していることを確認

    新仕様:
    - 実声は Nanami / Keita の2種のみ
    - デフォルト（無加工）:
        * female-Nanami == female
        * male-Keita == male
    - 速度(rate)が変わるプリセットは、同一テキストでも音声長が変わり、MP3サイズにも差が出る
    """
    repo_root = Path(__file__).resolve().parents[2]

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = tmp_path / "test_mapping.pdf"
    _make_sample_pdf(pdf_path, pages=1)

    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        img_data = f"data:image/png;base64,{img_b64}"
    finally:
        doc.close()

    host = "127.0.0.1"
    port = 8125

    base_url = f"http://{host}:{port}"

    env = os.environ.copy()
    env["SVM_INPUT_DIR"] = str(input_dir)
    env["SVM_OUTPUT_DIR"] = str(output_dir)

    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        cmd = [str(venv_python)]
    else:
        cmd = ["py", "-3.10"]

    server = subprocess.Popen(
        cmd
        + [
            "-m",
            "uvicorn",
            "src.server:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_port(host, port, timeout_s=30.0)

        # 速度差がサイズ差に出るよう、長文でテストする
        long_text = "これは音声プリセット検証用の長文です。" * 30

        def gen_size(voice_gender: str) -> int:
            payload = {
                "output_name": "test_mapping",
                "slide_index": 0,
                "script": long_text,
                "image_data": img_data,
                "resolution": "720p",
                "voice_gender": voice_gender,
            }
            res = requests.post(
                f"{base_url}/api/generate_audio",
                json=payload,
                timeout=120,
            )
            assert res.status_code == 200, res.text
            data = res.json()
            audio_path = data.get("path")
            assert audio_path
            p = Path(audio_path)
            assert p.exists()
            assert p.stat().st_size > 0
            return int(p.stat().st_size)

        # x1.5倍速デフォルト対応:
        # - 女声1: rate +50% (x1.5倍速デフォルト)
        # - female (無指定): rate +0% (旧デフォルト/無加工)
        # よって 女声1 の方が短く、ファイルサイズも小さくなる
        size_female_default = gen_size("female")
        size_女声1 = gen_size("女声1")
        print(f"female(default): {size_female_default} bytes")
        print(f"女声1:   {size_女声1} bytes")
        # x1.5倍速化により、女声1の方が小さいことを確認（50%前後の差異を許容）
        assert size_女声1 < size_female_default, "女声1(x1.5倍速)の方が小さいはず"

        # 女声2: rate +40% (x1.5倍速相当)
        # 女声1とほぼ同速度なので、サイズも近似
        size_女声2 = gen_size("女声2")
        print(f"女声2:      {size_女声2} bytes")
        # 許容: 20%差異（rate差が10%程度あるため）
        assert abs(size_女声2 - size_女声1) / max(size_女声1, 1) < 0.20

        # 男声1: rate +50% (x1.5倍速デフォルト)
        # male (無指定): rate +0% (旧デフォルト/無加工)
        # よって 男声1の方が短く、ファイルサイズも小さくなる
        size_male_default = gen_size("male")
        size_男声1 = gen_size("男声1")
        print(f"male(default): {size_male_default} bytes")
        print(f"男声1:    {size_男声1} bytes")
        assert size_男声1 < size_male_default, "男声1(x1.5倍速)の方が小さいはず"

        print("✓ 音声プリセットのデフォルト/差分適用を確認")

    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
