import re
import os
import glob

class M3UParser:
    def __init__(self, input_dir):
        self.input_dir = input_dir

    def clean_name(self, name):
        # Remove common prefixes/suffixes and normalize for matching
        name = name.lower()
        name = re.sub(r'\[.*?\]|\(.*?\)', '', name) # Remove content in brackets/parens
        name = re.sub(r'\b(hd|sd|fhd|hevc|h264|h265|tdt|pago)\b', '', name)
        name = re.sub(r'[^a-z0-9]', '', name) # Keep only alphanumeric
        return name.strip()

    def parse_extm3u_attrs(self, line):
        """Parse attributes from the #EXTM3U header line.
        
        Supported attributes:
          max-conn="N"  -> integer max simultaneous connections for this source
        
        Returns a dict, e.g. {'max_conn': 2} or {} if no attributes found.
        """
        attrs = {}
        match = re.search(r'max-conn=["\']?(\d+)["\']?', line, re.IGNORECASE)
        if match:
            attrs['max_conn'] = int(match.group(1))
        return attrs

    def parse_file(self, file_path):
        channels = []
        current_channel = None
        source_attrs = {}  # Attributes parsed from #EXTM3U header

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
                    'source_attrs': source_attrs  # carry header attrs into every channel
                }
            elif current_channel:
                if line.startswith('http'):
                    current_channel['urls'].append(line)

        if current_channel and current_channel['urls']:
            channels.append(current_channel)

        return channels

    def parse_all(self):
        all_channels_by_name = {} # Map clean_name -> channel_data
        
        # Look for all .m3u and .m3u8 files in the input directory
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
                        'name': channel['name'], # Use the first name encountered
                        'inf': channel['inf'],
                        'urls': [],       # list of dicts: {url, max_conn}
                        'url_set': set()  # for dedup
                    }
                
                entry = all_channels_by_name[clean_name]
                for url in channel['urls']:
                    if url not in entry['url_set']:
                        entry['url_set'].add(url)
                        entry['urls'].append({
                            'url': url,
                            'max_conn': source_attrs.get('max_conn', None)
                        })
        
        # Convert back to list format expected by the rest of the pipeline
        final_channels = []
        for clean_name, data in all_channels_by_name.items():
            final_channels.append({
                'name': data['name'],
                'inf': data['inf'],
                # Keep backward-compatible plain list of URL strings
                'urls': [u['url'] for u in data['urls']],
                # Extra: per-URL connection limit metadata
                'url_max_conn': {u['url']: u['max_conn'] for u in data['urls']}
            })
            
        return final_channels

if __name__ == "__main__":
    # Test logic
    test_dir = "/home/ubuntu/iptv-m3u-manager/data/inputs"
    os.makedirs(test_dir, exist_ok=True)
    
    with open(os.path.join(test_dir, "list1.m3u"), 'w') as f:
        f.write('#EXTM3U max-conn="2"\n#EXTINF:-1,La 1 HD\nhttp://stream1.es/stream.ts\n')
    with open(os.path.join(test_dir, "list2.m3u"), 'w') as f:
        f.write("#EXTM3U\n#EXTINF:-1,La 1 (TDT)\nhttp://stream2.es/stream.ts\n")
        
    parser = M3UParser(test_dir)
    channels = parser.parse_all()
    for channel in channels:
        print(f"Channel: {channel['name']}, URLs: {len(channel['urls'])}")
        for url in channel['urls']:
            mc = channel['url_max_conn'].get(url)
            limit = f"max-conn={mc}" if mc else "sin límite"
            print(f"  - {url}  [{limit}]")
