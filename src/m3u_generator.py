class M3UGenerator:
    def __init__(self, output_path):
        self.output_path = output_path

    def _normalize(self, name: str) -> str:
        # Normalize channel names for fuzzy matching: lowercase and keep only alphanumerics
        if not name:
            return ""
        return ''.join(ch for ch in name.lower() if ch.isalnum())

    def _reorder_channels_with_preference(self, channels: list) -> list:
        # User-requested preferred order (kept as written by the user)
        preferred = [
            "la 1 uhd",
            "la 1",
            "la 2 hd",
            "la 2 / 2cat",
            "antena 3",
            "cuatro",
            "telecinco",
            "lasexta",
            "neox",
            "nova",
            "mega",
            "a3series",
            "clan",
            "tdp",
            "24h",
            "boing",
            "fdf",
            "energy",
            "divinity",
            "bemad",
            "trece",
            "realmadrid tv",
            "ten",
            "dkiss",
            "dmax",
            "veo 7",
            "squirrel",
            "squirrel2",
        ]

        pref_norm = [self._normalize(p) for p in preferred]

        # Build result: first, any channels that match the preferred list (in that order),
        # then the rest in their original order.
        used = set()
        ordered = []

        for p in pref_norm:
            for ch in channels:
                name = ch.get('name') or ''
                name_norm = self._normalize(name)
                # Flexible match: either preferred key appears in channel name or viceversa
                if not name_norm:
                    continue
                if (p in name_norm or name_norm in p) and id(ch) not in used:
                    ordered.append(ch)
                    used.add(id(ch))

        # Append remaining channels preserving original order
        for ch in channels:
            if id(ch) in used:
                continue
            ordered.append(ch)

        return ordered

    def generate(self, channels):
        # Reorder channels so the user's preferred channels appear first (if present)
        try:
            channels = self._reorder_channels_with_preference(channels)
        except Exception:
            # In case of any unexpected structure, fall back to original order
            pass

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
