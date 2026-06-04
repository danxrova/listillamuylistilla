class M3UGenerator:
    def __init__(self, output_path):
        self.output_path = output_path

    def generate(self, channels):
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for channel in channels:
                if channel.get('best_stream') and channel['best_stream']['available']:
                    f.write(f"{channel['inf']}\n")
                    f.write(f"{channel['best_stream']['url']}\n\n")
                else:
                    # Optional: handle channels with no valid streams
                    # f.write(f"# {channel['name']} - NO VALID STREAM FOUND\n")
                    pass

    def generate_fallback_report(self, channels, report_path):
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# IPTV Stream Status Report\n\n")
            f.write("| Canal | Estado | Mejor URL | Latencia | Candidatos | Límite conn. |\n")
            f.write("| --- | --- | --- | --- | --- | --- |\n")
            
            for channel in channels:
                best = channel.get('best_stream')
                status = "✅ OK" if best and best['available'] else "❌ DOWN"
                url = best['url'] if best else "N/A"
                latency = f"{best['latency']:.3f}s" if best and best['available'] else "N/A"
                candidates = len(channel['urls'])

                # Show max-conn of the chosen stream (if any)
                url_max_conn = channel.get('url_max_conn', {})
                chosen_max_conn = url_max_conn.get(url) if best else None
                conn_label = f"max-conn={chosen_max_conn}" if chosen_max_conn is not None else "sin límite"
                
                f.write(f"| {channel['name']} | {status} | {url} | {latency} | {candidates} | {conn_label} |\n")
