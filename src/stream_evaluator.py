import asyncio
import time
import aiohttp
from urllib.parse import urlparse

class StreamEvaluator:
    def __init__(self, timeout=5, max_concurrent=10):
        self.timeout = timeout
        self.global_semaphore = asyncio.Semaphore(max_concurrent)
        # Cache of per-host semaphores for sources with max-conn declared
        self._host_semaphores = {}

    def _get_host_semaphore(self, url, max_conn):
        """Return a semaphore scoped to the host, created with max_conn slots.
        
        If the same host appears in multiple channels we reuse the same
        semaphore so the limit is enforced globally across all URLs of
        that host, not per-channel.
        """
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host not in self._host_semaphores:
            self._host_semaphores[host] = asyncio.Semaphore(max_conn)
        return self._host_semaphores[host]

    async def evaluate_stream(self, session, url, max_conn=None):
        """Evaluate a single stream URL.
        
        If max_conn is given the call acquires both the global semaphore
        (overall concurrency cap) and a per-host semaphore (connection
        limit declared by the source list via #EXTM3U max-conn="N").
        """
        # Determine which semaphores to acquire
        host_sem = self._get_host_semaphore(url, max_conn) if max_conn is not None else None

        async with self.global_semaphore:
            if host_sem is not None:
                async with host_sem:
                    return await self._do_request(session, url)
            else:
                return await self._do_request(session, url)

    async def _do_request(self, session, url):
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
                url_max_conn = channel.get('url_max_conn', {})
                for url in channel['urls']:
                    max_conn = url_max_conn.get(url)  # None if no limit declared
                    tasks.append(self.evaluate_stream(session, url, max_conn=max_conn))
            
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
    async def main():
        # Simulate two channels: one from a limited source, one unlimited
        channels = [
            {
                'name': 'Test Channel',
                'urls': ['https://www.google.com', 'https://invalid-url-test.com'],
                'url_max_conn': {
                    'https://www.google.com': 2,       # max 2 concurrent
                    'https://invalid-url-test.com': None  # no limit
                }
            }
        ]
        evaluator = StreamEvaluator()
        evaluated_channels = await evaluator.evaluate_all(channels)
        for channel in evaluated_channels:
            print(f"Channel: {channel['name']}")
            for ev in channel['evaluations']:
                print(f"  URL: {ev['url']}, Available: {ev['available']}, "
                      f"Latency: {ev['latency']:.4f}s, Error: {ev['error']}")

    asyncio.run(main())
