"""生成された音声ファイルの詳細分析"""
import sys
from pathlib import Path
from mutagen.mp3 import MP3

output_dir = Path("C:/Users/h-ham/spec-kit/Slide-Voice-Maker/output/temp")

audio_files = [
    ("slide_000.mp3", "female-Nanami (rate=+0%, pitch=+5%)"),
    ("slide_001.mp3", "female-Shiori (rate=-8%, pitch=-5%)"),
    ("slide_002.mp3", "male-Keita (rate=+0%, pitch=+0%)"),
    ("slide_003.mp3", "male-Masaru (rate=-15%, pitch=-20%)"),
]

print("=" * 70)
print("生成された音声ファイルの分析")
print("=" * 70)

for filename, description in audio_files:
    filepath = output_dir / filename
    
    if not filepath.exists():
        print(f"\n✗ {filename}: ファイルが存在しません")
        continue
    
    try:
        audio = MP3(str(filepath))
        duration = audio.info.length
        bitrate = audio.info.bitrate
        size = filepath.stat().st_size
        
        print(f"\n{description}")
        print(f"  ファイル: {filename}")
        print(f"  サイズ: {size:,} bytes")
        print(f"  再生時間: {duration:.2f} 秒")
        print(f"  ビットレート: {bitrate:,} bps")
        print(f"  1秒あたり: {size/duration:,.0f} bytes/sec")
        
    except Exception as e:
        print(f"\n✗ {filename}: 分析エラー - {e}")

print("\n" + "=" * 70)
print("分析完了")
print("=" * 70)
