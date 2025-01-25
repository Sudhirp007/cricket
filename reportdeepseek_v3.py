import yaml
import requests
import os
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import tempfile
from collections import defaultdict

# --------------------------
# CONFIGURATION SETTINGS
# --------------------------
OPENROUTER_API_KEY = "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"
MODEL = "mistralai/mistral-7b-instruct"

# Visual customization parameters
REPORT_COLORS = {
    'primary': colors.HexColor('#2c3e50'),      # Dark blue
    'secondary': colors.HexColor('#e74c3c'),    # Red
    'accent': colors.HexColor('#3498db'),       # Light blue
    'table_header': colors.HexColor('#ecf0f1'), # Light grey
    'chart1': '#27ae60',                        # Green
    'chart2': '#f39c12'                         # Orange
}

FONT_SETTINGS = {
    'title_size': 18,
    'header1_size': 14,
    'header2_size': 12,
    'body_size': 10
}

CHART_SETTINGS = {
    'dpi': 300,
    'figsize': (8, 4),
    'title_fontsize': 12,
    'label_fontsize': 10
}

# --------------------------
# STYLE DEFINITIONS
# --------------------------
styles = getSampleStyleSheet()
if 'CustomTitle' not in styles:
    styles.add(ParagraphStyle(
        name='CustomTitle', 
        fontSize=FONT_SETTINGS['title_size'], 
        textColor=REPORT_COLORS['primary'],
        alignment=1,
        spaceAfter=14
    ))

if 'Header1' not in styles:
    styles.add(ParagraphStyle(
        name='Header1', 
        fontSize=FONT_SETTINGS['header1_size'], 
        textColor=REPORT_COLORS['secondary'],
        spaceAfter=6
    ))

if 'Header2' not in styles:
    styles.add(ParagraphStyle(
        name='Header2', 
        fontSize=FONT_SETTINGS['header2_size'], 
        textColor=REPORT_COLORS['primary'],
        spaceAfter=4
    ))

if 'Analysis' not in styles:
    styles.add(ParagraphStyle(
        name='Analysis', 
        fontSize=FONT_SETTINGS['body_size'], 
        textColor=colors.black,
        leading=12
    ))

# --------------------------
# DATA PROCESSING FUNCTIONS
# --------------------------
def analyze_match(file_path):
    """Main function to process match data and generate analysis"""
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        stats = process_stats(data)
        analysis = get_ai_analysis(data)
        return stats, analysis
    except Exception as e:
        print(f"Error analyzing match: {str(e)}")
        return None, "Analysis unavailable due to an error."

def process_stats(data):
    """Process ball-by-ball data into structured statistics"""
    stats = {
        'batting': defaultdict(lambda: {'runs': 0, 'balls': 0, '4s': 0, '6s': 0}),
        'bowling': defaultdict(lambda: {'runs': 0, 'wickets': 0, 'balls': 0}),
        'team_scores': defaultdict(int),
    }

    # Process each delivery in the match
    for innings in data['innings']:
        inns_name, inns_data = next(iter(innings.items()))
        team = inns_data['team']
        
        for delivery in inns_data['deliveries']:
            ball_data = next(iter(delivery.values()))
            update_batting_stats(stats['batting'], ball_data)
            update_bowling_stats(stats['bowling'], ball_data)
            stats['team_scores'][team] += ball_data['runs']['total']

    calculate_derived_metrics(stats)
    return stats

def update_batting_stats(batting_stats, ball_data):
    """Update batting statistics for each ball"""
    batsman = ball_data['batsman']
    runs = ball_data['runs']['batsman']
    
    batting_stats[batsman]['runs'] += runs
    batting_stats[batsman]['balls'] += 1
    if runs == 4:
        batting_stats[batsman]['4s'] += 1
    if runs == 6:
        batting_stats[batsman]['6s'] += 1

def update_bowling_stats(bowling_stats, ball_data):
    """Update bowling statistics for each ball"""
    bowler = ball_data['bowler']
    
    bowling_stats[bowler]['runs'] += ball_data['runs']['total']
    bowling_stats[bowler]['balls'] += 1
    if 'wicket' in ball_data:
        bowling_stats[bowler]['wickets'] += 1

def calculate_derived_metrics(stats):
    """Calculate strike rates and economy rates"""
    for batsman, data in stats['batting'].items():
        data['strike_rate'] = round((data['runs'] / data['balls']) * 100, 2) if data['balls'] > 0 else 0
    
    for bowler, data in stats['bowling'].items():
        overs = data['balls'] / 6
        data['economy'] = round(data['runs'] / overs, 2) if overs > 0 else 0
        data['overs'] = round(overs, 1)

# --------------------------
# AI ANALYSIS FUNCTIONS
# --------------------------
def get_ai_analysis(data):
    """Generate analysis using OpenRouter API"""
    match_info = {
        "city": data["info"].get("city", "Unknown"),
        "teams": data["info"].get("teams", []),
        "winner": data["info"].get("outcome", {}).get("winner", "Unknown"),
    }
    
    prompt = f"""Analyze this cricket match data:
    Location: {match_info["city"]}
    Teams: {match_info["teams"]}
    Winner: {match_info["winner"]}
    
    Provide detailed analysis including:
    1. Key performances with statistics
    2. Match turning points
    3. Team comparison
    4. Recommendations
    
    Use markdown formatting with section headers."""
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 1500
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"API Error: {e}")
        return "Analysis unavailable due to API error"

# --------------------------
# PDF GENERATION FUNCTIONS
# --------------------------
def create_pdf_report(stats, analysis, output_file="report.pdf"):
    """Generate professional PDF report with visualizations"""
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    elements = []
    
    # Create pandas DataFrames for visualization
    batting_df = pd.DataFrame.from_dict(stats['batting'], orient='index')
    bowling_df = pd.DataFrame.from_dict(stats['bowling'], orient='index')

    # Add Cover Page
    elements += create_cover_page()
    
    # Add Analysis Section
    elements += create_analysis_section(analysis)
    
    # Add Team Comparison
    elements += create_team_comparison(stats['team_scores'])
    
    # Add Batting Performance
    elements += create_batting_section(batting_df)
    
    # Add Bowling Performance
    elements += create_bowling_section(bowling_df)
    
    # Build PDF document
    doc.build(elements)

def download_image(url, save_path):
    try:
        response = requests.get(url)
        if (response.status_code == 200):
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return save_path
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def create_cover_page():
    """Create report cover page with title"""
    image_url = "https://static.vecteezy.com/system/resources/previews/022/636/367/non_2x/cricket-logo-cricket-icon-design-free-vector.jpg"
    local_image_path = r"C:\Users\DELL\Downloads\12-FA2E5A35-567522-800-100.jpg"
    downloaded_path = download_image(image_url, local_image_path)

    return [
        Paragraph("<b>CRICKET MATCH REPORT</b>", styles['CustomTitle']),
        Spacer(1, 0.5*inch),
        Image(downloaded_path, width=1.5*inch, height=1.5*inch) if downloaded_path else None,
        PageBreak()
    ]

def create_analysis_section(analysis):
    """Create formatted analysis section"""
    section = [
        Paragraph("Expert Analysis", styles['Header1']),
        Spacer(1, 0.1*inch)
    ]
    
    for line in analysis.split('\n'):
        if line.startswith('## '):
            section.append(Paragraph(line[3:], styles['Header2']))
        elif line.startswith('**'):
            section.append(Paragraph(line.replace('**', ''), styles['Header2']))
        else:
            section.append(Paragraph(line, styles['Analysis']))
        section.append(Spacer(1, 0.05*inch))
    
    section.append(PageBreak())
    return section

def create_team_comparison(team_scores):
    """Create team comparison section with chart"""
    fig, ax = plt.subplots(figsize=CHART_SETTINGS['figsize'])
    teams = list(team_scores.keys())
    scores = list(team_scores.values())
    
    ax.bar(teams, scores, color=[REPORT_COLORS['chart1'], REPORT_COLORS['chart2']])
    ax.set_title("Team Score Comparison", fontsize=CHART_SETTINGS['title_fontsize'])
    ax.set_ylabel("Runs", fontsize=CHART_SETTINGS['label_fontsize'])
    
    chart_path = tempfile.mktemp(suffix=".png")
    plt.savefig(chart_path, dpi=CHART_SETTINGS['dpi'], bbox_inches='tight')
    plt.close()

    return [
        Paragraph("Team Comparison", styles['Header1']),
        Spacer(1, 0.2*inch),
        Image(chart_path, width=6*inch, height=3*inch),
        PageBreak()
    ]

def create_batting_section(batting_df):
    """Create batting performance section with table and chart"""
    batting_df = batting_df.sort_values('runs', ascending=False).head(5)
    table_data = [["Batsman", "Runs", "Balls", "4s", "6s", "SR"]]
    table_data += batting_df.reset_index().values.tolist()
    
    fig, ax = plt.subplots(figsize=CHART_SETTINGS['figsize'])
    batting_df['runs'].plot(kind='barh', color=REPORT_COLORS['chart1'], ax=ax)
    ax.set_title("Top Run Scorers", fontsize=CHART_SETTINGS['title_fontsize'])
    ax.set_xlabel("Runs", fontsize=CHART_SETTINGS['label_fontsize'])
    chart_path = tempfile.mktemp(suffix=".png")
    plt.savefig(chart_path, dpi=CHART_SETTINGS['dpi'], bbox_inches='tight')
    plt.close()

    return [
        Paragraph("Batting Performance", styles['Header1']),
        Spacer(1, 0.2*inch),
        create_table(table_data, [1.5*inch]*6),
        Spacer(1, 0.3*inch),
        Image(chart_path, width=6*inch, height=3*inch),
        PageBreak()
    ]

def create_bowling_section(bowling_df):
    """Create bowling performance section with table and chart"""
    bowling_df = bowling_df.sort_values('wickets', ascending=False).head(5)
    table_data = [["Bowler", "Overs", "Runs", "Wickets", "Economy"]]
    table_data += bowling_df[['overs', 'runs', 'wickets', 'economy']].reset_index().values.tolist()
    
    fig, ax = plt.subplots(figsize=CHART_SETTINGS['figsize'])
    bowling_df['wickets'].plot(kind='bar', color=REPORT_COLORS['chart2'], ax=ax)
    ax.set_title("Top Wicket Takers", fontsize=CHART_SETTINGS['title_fontsize'])
    ax.set_ylabel("Wickets", fontsize=CHART_SETTINGS['label_fontsize'])
    chart_path = tempfile.mktemp(suffix=".png")
    plt.savefig(chart_path, dpi=CHART_SETTINGS['dpi'], bbox_inches='tight')
    plt.close()

    return [
        Paragraph("Bowling Performance", styles['Header1']),
        Spacer(1, 0.2*inch),
        create_table(table_data, [1.8*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch]),
        Spacer(1, 0.3*inch),
        Image(chart_path, width=6*inch, height=3*inch)
    ]

def create_table(data, col_widths):
    """Create styled table with consistent formatting"""
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), REPORT_COLORS['table_header']),
        ('TEXTCOLOR', (0,0), (-1,0), REPORT_COLORS['primary']),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), FONT_SETTINGS['body_size']),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    return table

# --------------------------
# MAIN EXECUTION
# --------------------------
if __name__ == "__main__":
    file_path = r"C:\\Users\\DELL\\Downloads\\all\\1416493.yaml"
    stats, analysis = analyze_match(file_path)
    
    if stats:
        create_pdf_report(stats, analysis, "final_report5.pdf")
        print("Report generated successfully!")
    else:
        print("Failed to generate report due to errors")
