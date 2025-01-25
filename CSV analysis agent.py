from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import pandas as pd
import os

# 1. Configure OpenRouter
os.environ['OPENROUTER_API_KEY'] = ""

llm = ChatOpenAI(
    model="mistralai/mistral-7b-instruct",
    temperature=0.1,
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.environ['OPENROUTER_API_KEY']
)

# 2. Create CSV Summary Agent
def csv_summary_agent(file_path):
    try:
        # Load CSV data
        df = pd.read_csv(file_path)
        
        # Generate basic stats
        stats = {
            "columns": list(df.columns),
            "total_rows": len(df),
            "numeric_cols": df.select_dtypes(include='number').columns.tolist(),
            "missing_values": df.isna().sum().to_dict(),
            "basic_stats": df.describe().to_dict()
        }
        
        # Create summary prompt
        prompt = f"""Analyze this CSV data summary:
        {stats}
        
        Provide a concise report with:
        1. Dataset overview
        2. Key column descriptions
        3. Notable patterns/insights
        4. Data quality issues
        5. News about Yuvraj Singh
        
        Use markdown formatting."""
        
        # Generate summary
        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        return f"Error: {str(e)}"

# 3. Usage Example
if __name__ == "__main__":
    summary = csv_summary_agent(r"C:\Users\DELL\Downloads\IPL\1MB.csv")
    print("CSV DATA SUMMARY:\n")
    print(summary)