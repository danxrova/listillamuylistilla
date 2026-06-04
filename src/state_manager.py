import json
import os

class StateManager:
    def __init__(self, state_file):
        self.state_file = state_file
        self.state = self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_state(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=4)

    def update_stream_history(self, url, evaluation):
        if url not in self.state:
            self.state[url] = {
                'history': [],
                'fail_count': 0,
                'success_count': 0
            }
        
        # Add to history (keep last 10)
        self.state[url]['history'].append({
            'timestamp': evaluation.get('timestamp', ''),
            'available': evaluation['available'],
            'latency': evaluation['latency']
        })
        self.state[url]['history'] = self.state[url]['history'][-10:]
        
        if evaluation['available']:
            self.state[url]['success_count'] += 1
        else:
            self.state[url]['fail_count'] += 1

    def get_stream_stats(self, url):
        return self.state.get(url, {
            'history': [],
            'fail_count': 0,
            'success_count': 0
        })
