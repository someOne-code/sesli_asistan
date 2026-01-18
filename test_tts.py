import edge_tts
import asyncio

async def test_tts():
    print("Testing edge-tts...")
    communicate = edge_tts.Communicate("Merhaba test", "tr-TR-EmelNeural")
    
    chunk_count = 0
    audio_chunks = 0
    
    async for chunk in communicate.stream():
        chunk_count += 1
        if chunk["type"] == "audio":
            audio_chunks += 1
            print(f"Audio chunk {audio_chunks}: {len(chunk['data'])} bytes")
    
    print(f"\nTotal chunks: {chunk_count}")
    print(f"Audio chunks: {audio_chunks}")
    
    if audio_chunks == 0:
        print("❌ NO AUDIO GENERATED!")
    else:
        print("✅ Audio generated successfully")

asyncio.run(test_tts())
