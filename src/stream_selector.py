class StreamSelector:
    def __init__(self, weights=None):
        # Default weights for scoring
        self.weights = weights or {
            'availability': 1000,
            'latency': -100,  # Lower latency is better
            'reliability': 50  # Based on success/fail ratio
        }

    def calculate_score(self, evaluation, stats):
        if not evaluation['available']:
            return -10000
        
        score = self.weights['availability']
        score += self.weights['latency'] * evaluation['latency']
        
        total_checks = stats['success_count'] + stats['fail_count']
        if total_checks > 0:
            reliability = stats['success_count'] / total_checks
            score += self.weights['reliability'] * reliability * 10
            
        return score

    def select_best_streams(self, channels, state_manager):
        for channel in channels:
            best_score = -float('inf')
            best_stream = None
            
            # Evaluate all URLs for this channel
            scored_urls = []
            for evaluation in channel['evaluations']:
                url = evaluation['url']
                stats = state_manager.get_stream_stats(url)
                score = self.calculate_score(evaluation, stats)
                
                scored_urls.append({
                    'url': url,
                    'score': score,
                    'evaluation': evaluation
                })
                
                if score > best_score:
                    best_score = score
                    best_stream = evaluation
            
            # Sort URLs by score for fallback
            scored_urls.sort(key=lambda x: x['score'], reverse=True)
            
            channel['best_stream'] = best_stream
            channel['all_candidates'] = scored_urls
            
        return channels
