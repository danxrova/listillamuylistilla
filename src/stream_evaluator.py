import asyncio
import time
import aiohttp
from urllib.parse import urlparse

class StreamEvaluator:
    def __init__(self, timeout=5, max_concurrent=10):
        self.timeout = timeout
        self.global_semaphore = asyncio.Semaphore(max_concurrent)
        # Per-host semaphores for sources with max-conn declared
        self._host_semaphores = {}
        # Per-host sequential locks for sources with wait-scan declared
        # Each entry: {'lock': asyncio.Lock(), 'wait': float}
        self._host_wait_locks = {}

    def _get_host_semaphore(self, url, max_conn):
        """Return (and lazily create) a per-host semaphore capped at max_conn."""
        host = self._host_key(url)
        if host not in self._host_semaphores:
            self._host_semaphores[host] = asyncio.Semaphore(max_conn)
        return self._host_semaphores[host]

    def _get_host_wait_lock(self, url, wait_scan):
        """Return (and lazily create) a per-host sequential lock + wait config."""
        host = self._host_key(url)
        if host not in self._host_wait_locks:
            self._host_wait_locks[host] = {
                'lock': asyncio.Lock(),
                'wait': wait_scan
            }
        return self._host_wait_locks[host]

    def _host_key(self, url):
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    async def evaluate_stream(self, session, url, max_conn=None, wait_scan=None):
        """Evaluate a single stream URL respecting max-conn and wait-scan limits.

        max_conn  → per-host semaphore: at most N concurrent requests to that host
        wait_scan → per-host sequential lock + sleep: requests to that host are
                    serialised and each one waits `wait_scan` seconds before the
                    next one starts, preventing temporary bans from burst traffic.

        Both limits can be combined on the same source.
        """
        host_sem   = self._get_host_semaphore(url, max_conn)  if max_conn  is not None else None
        host_wait  = self._get_host_wait_lock(url, wait_scan) if wait_scan is not None else None

        async with self.global_semaphore:
            if host_sem is not None:
                async with host_sem:
                    return await self._request_with_wait(session, url, host_wait)
            else:
                return await self._request_with_wait(session, url, host_wait)

    async def _request_with_wait(self, session, url, host_wait):
        """Run the HTTP request.  If host_wait is set, serialise requests to
        this host and sleep `wait` seconds after each one so the server is not
        hammered with simultaneous probes."""
        if host_wait is not None:
            async with host_wait['lock']:
                result = await self._do_request(session, url)
                await asyncio.sleep(host_wait['wait'])
                return result
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
                url_max_conn  = channel.get('url_max_conn',  {})
                url_wait_scan = channel.get('url_wait_scan', {})
                for url in channel['urls']:
                    tasks.append(self.evaluate_stream(
                        session, url,
                        max_conn  = url_max_conn.get(url),
                        wait_scan = url_wait_scan.get(url)
                    ))

            results = await asyncio.gather(*tasks)

            idx = 0
            for channel in channels:
                channel['evaluations'] = []
                for _ in range(len(channel['urls'])):
                    channel['evaluations'].append(results[idx])
                    idx += 1

            return channels

if __name__ == "__main__":
    async def main():
        channels = [
            {
                'name': 'Test Channel',
                'urls': ['https://www.google.com', 'https://invalid-url-test.com'],
                'url_max_conn':  {'https://www.google.com': 2,    'https://invalid-url-test.com': None},
                'url_wait_scan': {'https://www.google.com': 1.0,  'https://invalid-url-test.com': None}
            }
        ]
        evaluator = StreamEvaluator()
        evaluated = await evaluator.evaluate_all(channels)
        for ch in evaluated:
            print(f"Channel: {ch['name']}")
            for ev in ch['evaluations']:
                print(f"  {ev['url']}  available={ev['available']}  "
                      f"latency={ev['latency']:.3f}s  error={ev['error']}")

    asyncio.run(main())
