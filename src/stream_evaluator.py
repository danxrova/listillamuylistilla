import asyncio
import time
import aiohttp
from urllib.parse import urlparse

class StreamEvaluator:
    def __init__(self, timeout=5, max_concurrent=10):
        self.timeout = timeout
        self.global_semaphore = asyncio.Semaphore(max_concurrent)
        self._host_semaphores = {}
        self._host_wait_locks = {}

    def _host_key(self, url):
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _get_host_semaphore(self, url, max_conn):
        host = self._host_key(url)
        if host not in self._host_semaphores:
            self._host_semaphores[host] = asyncio.Semaphore(max_conn)
        return self._host_semaphores[host]

    def _get_host_wait_lock(self, url, wait_scan):
        host = self._host_key(url)
        if host not in self._host_wait_locks:
            self._host_wait_locks[host] = {'lock': asyncio.Lock(), 'wait': wait_scan}
        return self._host_wait_locks[host]

    async def evaluate_stream(self, session, url, max_conn=None, wait_scan=None, no_check=False):
        """Evaluate a single stream URL.

        no_check  → skip the HTTP request entirely and return a synthetic
                    'available' result with zero latency.
        max_conn  → per-host semaphore: at most N concurrent requests to that host.
        wait_scan → per-host sequential lock + sleep between requests.
        """
        if no_check:
            return {
                'url':         url,
                'available':   True,
                'latency':     0.0,
                'status_code': None,
                'error':       None
            }

        host_sem  = self._get_host_semaphore(url, max_conn)  if max_conn  is not None else None
        host_wait = self._get_host_wait_lock(url, wait_scan) if wait_scan is not None else None

        async with self.global_semaphore:
            if host_sem is not None:
                async with host_sem:
                    return await self._request_with_wait(session, url, host_wait)
            else:
                return await self._request_with_wait(session, url, host_wait)

    async def _request_with_wait(self, session, url, host_wait):
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
                    return {'url': url, 'available': True,  'latency': latency, 'status_code': response.status, 'error': None}
                else:
                    return {'url': url, 'available': False, 'latency': latency, 'status_code': response.status, 'error': f"Status code {response.status}"}
        except Exception as e:
            return {'url': url, 'available': False, 'latency': time.time() - start_time, 'status_code': None, 'error': str(e)}

    async def evaluate_all(self, channels):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for channel in channels:
                url_max_conn  = channel.get('url_max_conn',  {})
                url_wait_scan = channel.get('url_wait_scan', {})
                url_no_check  = channel.get('url_no_check',  {})
                for url in channel['urls']:
                    tasks.append(self.evaluate_stream(
                        session, url,
                        max_conn  = url_max_conn.get(url),
                        wait_scan = url_wait_scan.get(url),
                        no_check  = url_no_check.get(url, False)
                    ))

            results = await asyncio.gather(*tasks)

            idx = 0
            for channel in channels:
                channel['evaluations'] = []
                for _ in range(len(channel['urls'])):
                    channel['evaluations'].append(results[idx])
                    idx += 1

            return channels
