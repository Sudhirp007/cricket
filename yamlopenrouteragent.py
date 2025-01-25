from langchain_openai import ChatOpenAI
import yaml
import os
from collections import defaultdict

# 1. Configure OpenRouter
os.environ['OPENROUTER_API_KEY'] = "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"

llm = ChatOpenAI(
    model="mistralai/mistral-7b-instruct",
    temperature=0.1,
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.environ['OPENROUTER_API_KEY']
)

def analyze_cricket_match(file_path):
    try:
        # Load YAML data
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Process match data
        match_stats = process_match_data(data)
        
        # Generate analysis
        return generate_match_report(data, match_stats)
        
    except Exception as e:
        return f"Error: {str(e)}"

def process_match_data(data):
    """Process ball-by-ball match data"""
    stats = {
        'batting': defaultdict(lambda: {'runs': 0, 'balls': 0}),
        'bowling': defaultdict(lambda: {'runs': 0, 'wickets': 0, 'balls': 0}),
        'extras': defaultdict(int),
        'team_scores': defaultdict(int)
    }

    # Process each innings
    for innings in data['innings']:
        inns_name = next(iter(innings))
        team = innings[inns_name]['team']
        
        for delivery in innings[inns_name]['deliveries']:
            ball = next(iter(delivery))
            ball_data = delivery[ball]
            
            # Batting stats
            batsman = ball_data['batsman']
            stats['batting'][batsman]['runs'] += ball_data['runs']['batsman']
            stats['batting'][batsman]['balls'] += 1
            
            # Bowling stats
            bowler = ball_data['bowler']
            stats['bowling'][bowler]['runs'] += ball_data['runs']['total']
            stats['bowling'][bowler]['balls'] += 1
            
            # Extras
            if 'extras' in ball_data:
                for extra_type in ball_data['extras']:
                    stats['extras'][extra_type] += 1
                    stats['extras']['total'] += 1
            
            # Team totals
            stats['team_scores'][team] += ball_data['runs']['total']

    # Calculate derived metrics
    for batsman in stats['batting']:
        stats['batting'][batsman]['strike_rate'] = round(
            (stats['batting'][batsman]['runs'] / stats['batting'][batsman]['balls']) * 100, 2
        )

    for bowler in stats['bowling']:
        stats['bowling'][bowler]['economy'] = round(
            (stats['bowling'][bowler]['runs'] / (stats['bowling'][bowler]['balls'] / 6)), 2
        )

    return stats

def generate_match_report(data, stats):
    """Generate natural language match report"""
    # Prepare summary
    summary = {
        'match_info': {
            'competition': data['info']['competition'],
            'date': data['info']['dates'][0],
            'venue': data['info']['venue'],
            'result': f"{data['info']['outcome']['winner']} won by {data['info']['outcome']['by']['runs']} runs"
        },
        'batting_leaders': sorted(
            stats['batting'].items(),
            key=lambda x: x[1]['runs'],
            reverse=True
        )[:3],
        'bowling_leaders': sorted(
            stats['bowling'].items(),
            key=lambda x: x[1]['wickets'],
            reverse=True
        )[:3],
        'extras': dict(stats['extras']),
        'team_scores': dict(stats['team_scores'])
    }

    # Create analysis prompt
    prompt = f"""Analyze this cricket match data:
    {summary}

    Provide a detailed match report including:
    1. Match overview and result
    2. Key batting performances
    3. Key bowling performances
    4. Analysis of extras
    5. Turning points in the match
    6. Impact on tournament standings

    Use markdown formatting with cricket terminology."""

    # Generate report
    response = llm.invoke(prompt)
    return response.content

# Example usage
if __name__ == "__main__":
    analysis = analyze_cricket_match(r"C:\Users\DELL\Downloads\all\1417725.yaml")
    print("CRICKET MATCH ANALYSIS REPORT\n")
    print(analysis)