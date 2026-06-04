import asyncio
import time
import aiohttp
import os

class StreamEvaluator:
    def __init__(self, timeout=5, max_concurrent=10):
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def evaluate_stream(self, session, url):
        async with self.semaphore:
            start_time = time.time()
            try:
                async with session.get(url, timeout=self.timeout) as response:
                    latency = time.time() - start_time
                    if response.status == 200:
                        return {
                            'url': url,
                            'available': True,
                            'latency': latency,
                            'status_code': response.status,
                            'error': None
                        }
                    else:
                        return {
                            'url': url,
                            'available': False,
                            'latency': latency,
                            'status_code': response.status,
                            'error': f"Status code {response.status}"
                        }
            except Exception as e:
                return {
                    'url': url,
                    'available': False,
                    'latency': time.time() - start_time,
                    'status_code': None,
                    'error': str(e)
                }

    async def evaluate_all(self, channels):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for channel in channels:
                for url in channel['urls']:
                    tasks.append(self.evaluate_stream(session, url))
            
            results = await asyncio.gather(*tasks)
            
            # Map results back to channels
            idx = 0
            for channel in channels:
                channel['evaluations'] = []
                for _ in range(len(channel['urls'])):
                    channel['evaluations'].append(results[idx])
                    idx += 1
            
            return channels

if __name__ == "__main__":
    # Simple test
    async def main():
        channels = [
            {'name': 'Test Channel', 'urls': ['https://www.google.com', 'https://invalid-url-test.com']}
        ]
        evaluator = StreamEvaluator()
        evaluated_channels = await evaluator.evaluate_all(channels)
        for channel in evaluated_channels:
            print(f"Channel: {channel['name']}")
            for eval in channel['evaluations']:
                print(f"  URL: {eval['url']}, Available: {eval['available']}, Latency: {eval['latency']:.4f}s, Error: {eval['error']}")

    asyncio.run(main())
