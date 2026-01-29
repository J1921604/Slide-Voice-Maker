"""Edge TTS パラメータテスト - デバッグ用

注意:
edge-tts は入力テキストを内部でSSML化する実装のため、<speak>...</speak> を文字列として渡すと
タグがSSMLとして解釈されず、そのまま読み上げられることがあります。

このスクリプトは Communicate の rate/pitch/volume 引数で制御が効くことを確認します。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_ssml_direct():
    """Edge TTSにパラメータを渡してテスト"""
    import edge_tts
    
    output_dir = Path(__file__).parent / "output" / "temp"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    test_cases = [
        {
            "name": "plain_text",
            "text": "これは普通のテキストです。",
            "voice": "ja-JP-NanamiNeural",
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
        },
        {
            "name": "ssml_with_rate",
            "text": "これは遅いテキストです。",
            "voice": "ja-JP-NanamiNeural",
            "rate": "-20%",
            "pitch": "+0Hz",
            "volume": "+0%",
        },
        {
            "name": "ssml_with_pitch",
            "text": "これは高い声です。",
            "voice": "ja-JP-NanamiNeural",
            "rate": "+0%",
            "pitch": "+30Hz",
            "volume": "+0%",
        },
        {
            "name": "ssml_all_params",
            "text": "これは重厚な声です。",
            "voice": "ja-JP-KeitaNeural",
            "rate": "-15%",
            "pitch": "-45Hz",
            "volume": "+10%",
        },
    ]
    
    print("=" * 70)
    print("Edge TTS パラメータ直接テスト")
    print("=" * 70)
    
    for case in test_cases:
        output_file = output_dir / f"debug_{case['name']}.mp3"
        
        print(f"\nテスト: {case['name']}")
        print(f"Voice: {case['voice']}")
        print(f"Params: rate={case['rate']} pitch={case['pitch']} volume={case['volume']}")
        print(f"Text: {case['text'][:80]}...")
        
        try:
            communicate = edge_tts.Communicate(
                case['text'],
                case['voice'],
                rate=case['rate'],
                pitch=case['pitch'],
                volume=case['volume'],
            )
            await communicate.save(str(output_file))
            
            if output_file.exists():
                size = output_file.stat().st_size
                print(f"✓ 生成成功: {size} bytes")
            else:
                print(f"✗ ファイルが生成されませんでした")
        except Exception as e:
            print(f"✗ エラー: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("output/tempの音声ファイルを再生して確認してください")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_ssml_direct())
