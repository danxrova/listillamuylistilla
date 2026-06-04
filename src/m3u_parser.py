import re
import os
import glob

class M3UParser:
    def __init__(self, input_dir):
        self.input_dir = input_dir

    def clean_name(self, name):
        name = name.lower()
        name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
        name = re.sub(r'\b(hd|sd|fhd|4k|uhd|hevc|h264|h265|tdt|pago)\b', '', name)
        name = re.sub(r'[^a-z0-9]', '', name)
        return name.strip()

    def parse_extm3u_attrs(self, line):
        """Parse attributes from the #EXTM3U header line.

        Supported attributes:
          max-conn="N"   -> int, max simultaneous connections for this source
          wait-scan="N"  -> float, seconds to wait between requests to this source
        
        Returns a dict, e.g. {'max_conn': 2, 'wait_scan': 5} or {}.
        """
        attrs = {}
        m = re.search(r'max-conn=["\']?(\d+)["\']?', line, re.IGNORECASE)
        if m:
            attrs['max_conn'] = int(m.group(1))
        m = re.search(r'wait-scan=["\']?([\d.]+)["\']?', line, re.IGNORECASE)
        if m:
            attrs['wait_scan'] = float(m.group(1))
        return attrs

    def parse_file(self, file_path):
        channels = []
        current_channel = None
        source_attrs = {}

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('#EXTM3U'):
                source_attrs = self.parse_extm3u_attrs(line)
                continue

            if line.startswith('#EXTINF:'):
                if current_channel and current_channel['urls']:
                    channels.append(current_channel)
                
                match = re.search(r',(.+)$', line)
                channel_name = match.group(1).strip() if match else "Unknown"
                current_channel = {
                    'name': channel_name,
                    'clean_name': self.clean_name(channel_name),
                    'inf': line,
                    'urls': [],
                    'source_attrs': source_attrs
                }
            elif current_channel:
                if line.startswith('http'):
                    current_channel['urls'].append(line)

        if current_channel and current_channel['urls']:
            channels.append(current_channel)

        return channels

    def parse_all(self):
        all_channels_by_name = {}

        m3u_files = glob.glob(os.path.join(self.input_dir, "*.m3u")) + \
                    glob.glob(os.path.join(self.input_dir, "*.m3u8"))

        for file_path in m3u_files:
            print(f"Parsing file: {file_path}")
            file_channels = self.parse_file(file_path)

            for channel in file_channels:
                clean_name = channel['clean_name']
                if not clean_name:
                    continue

                source_attrs = channel.get('source_attrs', {})

                if clean_name not in all_channels_by_name:
                    all_channels_by_name[clean_name] = {
                        'name': channel['name'],
                        'inf': channel['inf'],
                        'urls': [],
                        'url_set': set()
                    }

                entry = all_channels_by_name[clean_name]
                for url in channel['urls']:
                    if url not in entry['url_set']:
                        entry['url_set'].add(url)
                        entry['urls'].append({
                            'url': url,
                            'max_conn': source_attrs.get('max_conn', None),
                            'wait_scan': source_attrs.get('wait_scan', None)
                        })

        final_channels = []
        for clean_name, data in all_channels_by_name.items():
            final_channels.append({
                'name': data['name'],
                'inf': data['inf'],
                'urls': [u['url'] for u in data['urls']],
                'url_max_conn':  {u['url']: u['max_conn']  for u in data['urls']},
                'url_wait_scan': {u['url']: u['wait_scan'] for u in data['urls']}
            })

        return final_channels

if __name__ == "__main__":
    import tempfile, json
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "list1.m3u"), 'w') as f:
            f.write('#EXTM3U max-conn="2" wait-scan="5"\n')
            f.write('#EXTINF:-1,La 1 HD\nhttp://stream1.es/stream.ts\n')
        with open(os.path.join(td, "list2.m3u"), 'w') as f:
            f.write("#EXTM3U\n")
            f.write("#EXTINF:-1,La 1 (TDT)\nhttp://stream2.es/stream.ts\n")

        parser = M3UParser(td)
        channels = parser.parse_all()
        for ch in channels:
            print(f"Channel: {ch['name']}")
            for url in ch['urls']:
                mc = ch['url_max_conn'].get(url)
                ws = ch['url_wait_scan'].get(url)
                print(f"  {url}  max-conn={mc}  wait-scan={ws}")
