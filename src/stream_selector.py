class StreamSelector:
    def __init__(self, weights=None):
        # Default weights for scoring
        self.weights = weights or {
            'availability': 1000,
            'latency': -100,  # Lower latency is better
            'reliability': 50  # Based on success/fail ratio
        }
        # Penalty applied to streams from sources with a max-conn limit.
        # This ensures unlimited sources are preferred when both are available.
        self.limited_conn_penalty = 500

    def calculate_score(self, evaluation, stats, max_conn=None):
        if not evaluation['available']:
            return -10000
        
        score = self.weights['availability']
        score += self.weights['latency'] * evaluation['latency']
        
        total_checks = stats['success_count'] + stats['fail_count']
        if total_checks > 0:
            reliability = stats['success_count'] / total_checks
            score += self.weights['reliability'] * reliability * 10

        # Penalise streams whose source declares a connection limit so that,
        # when an unlimited alternative exists for the same channel, it is
        # chosen first.  A source with max-conn=1 is penalised more than one
        # with max-conn=10 (tighter limit → stronger penalty).
        if max_conn is not None:
            # penalty = base_penalty / max_conn  (fewer slots → bigger penalty)
            penalty = self.limited_conn_penalty / max(max_conn, 1)
            score -= penalty
            
        return score

    def select_best_streams(self, channels, state_manager):
        for channel in channels:
            best_score = -float('inf')
            best_stream = None
            
            url_max_conn = channel.get('url_max_conn', {})

            # Evaluate all URLs for this channel
            scored_urls = []
            for evaluation in channel['evaluations']:
                url = evaluation['url']
                max_conn = url_max_conn.get(url)  # None means no limit declared
                stats = state_manager.get_stream_stats(url)
                score = self.calculate_score(evaluation, stats, max_conn=max_conn)
                
                scored_urls.append({
                    'url': url,
                    'score': score,
                    'evaluation': evaluation,
                    'max_conn': max_conn
                })
                
                if score > best_score:
                    best_score = score
                    best_stream = evaluation
            
            # Sort URLs by score for fallback
            scored_urls.sort(key=lambda x: x['score'], reverse=True)
            
            channel['best_stream'] = best_stream
            channel['all_candidates'] = scored_urls
            
        return channels
