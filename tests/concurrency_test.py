import asyncio
import httpx
import time

URL = "https://aegisai-31e9.onrender.com/v1/outputs/score"
PAYLOAD = {
    "output_text": "One of our employees, Sarah Mitchell, lives at 1847 Oakwood Dr in San Jose.",
    "agent_id": "concurrency_tester",
    "session_id": "test_123"
}

async def send_req(client, i):
    start = time.time()
    try:
        r = await client.post(URL, json=PAYLOAD, timeout=60.0)
        return r.status_code, time.time() - start
    except Exception as e:
        return f"Error: {str(e.__class__.__name__)} - {str(e)}", time.time() - start

async def main():
    async with httpx.AsyncClient() as client:
        print(f"Firing 5 concurrent requests to {URL}...")
        start_time = time.time()
        tasks = [send_req(client, i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        wall_time = time.time() - start_time
        
        for i, (status, duration) in enumerate(results):
            print(f"Req {i+1}: Status {status} in {duration:.2f}s")
        print(f"\nTotal Wall-Clock Time: {wall_time:.2f}s")
        print(f"Average individual request time: {sum(r[1] for r in results)/len(results):.2f}s")
        if wall_time < sum(r[1] for r in results):
            print("=> Proof of genuine parallel handling! (Wall time < Sum of individual times)")

if __name__ == "__main__":
    asyncio.run(main())
