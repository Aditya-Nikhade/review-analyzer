import os
import pandas as pd
import json
from datetime import datetime
import time
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

# --- SETUP ---
load_dotenv()

# Configure Azure AI Client
client = ChatCompletionsClient(
    endpoint=os.getenv("AZURE_AI_ENDPOINT", "https://models.github.ai/inference"),
    credential=AzureKeyCredential(os.getenv("GITHUB_TOKEN")),
)
MODEL = "openai/gpt-4.1"

# Configure Database
db_url = os.getenv("DATABASE_URL")
if not db_url.startswith('mysql'):
    db_url = f"mysql+mysqlconnector://{db_url}"
engine = create_engine(db_url, pool_pre_ping=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REVIEWS_CSV_PATH = os.path.join(SCRIPT_DIR, 'Reviews.csv')

def analyze_review_batch(reviews):
    """Analyzes a batch of reviews using an LLM and returns structured insights."""
    if not reviews:
        return None
        
    reviews_text = "\n\n".join([f"Review {i+1}: {review}" for i, review in enumerate(reviews)])
    
    prompt = f"""
    Analyze the following batch of customer reviews. Provide a valid JSON object with:
    1. "sentiment_breakdown": An object with "positive_pct", "neutral_pct", and "negative_pct" as percentages.
    2. "top_praise": A short string summarizing the most common positive point.
    3. "top_issue": A short string summarizing the most common negative point.

    Reviews:
    {reviews_text}

    JSON Response:
    """
    try:
        response = client.complete(
            messages=[SystemMessage("You are a review analyzer."), UserMessage(prompt)],
            model=MODEL, temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        
        if content.startswith('```'):
            content = '\n'.join(content.split('\n')[1:-1])
        
        return json.loads(content)
    except Exception as e:
        print(f"Error analyzing review batch: {e}")
        return None

def init_db():
    """Ensures database tables exist and are empty before a pipeline run."""
    with engine.connect() as connection:
        trans = connection.begin()
        try:
            print("Initializing database...")
            # Create tables only if they don't already exist
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    score FLOAT,
                    summary TEXT,
                    text TEXT,
                    review_date DATETIME,
                    INDEX idx_product_id (product_id)
                )
            """))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS review_insights (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id VARCHAR(255) NOT NULL,
                    summary_date DATE NOT NULL,
                    positive_pct FLOAT,
                    neutral_pct FLOAT,
                    negative_pct FLOAT,
                    top_praise TEXT,
                    top_issue TEXT,
                    FOREIGN KEY (product_id) REFERENCES reviews(product_id),
                    INDEX idx_product_date (product_id, summary_date)
                )
            """))
            
            # Clear tables for a fresh run
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            connection.execute(text("TRUNCATE TABLE review_insights;"))
            connection.execute(text("TRUNCATE TABLE reviews;"))
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            trans.commit()
            print("Database cleared and ready.")
        except Exception as e:
            trans.rollback()
            print(f"Database initialization failed: {e}")
            raise

def run_etl_pipeline(initial_rows_to_load=5000):
    print("Starting ETL pipeline...")
    
    init_db()
    
    with engine.connect() as connection:
        trans = connection.begin()
        try:
            # === STEP 1: LOAD RAW REVIEWS ===
            print(f"Reading first {initial_rows_to_load} rows from CSV...")
            df = pd.read_csv(REVIEWS_CSV_PATH, nrows=initial_rows_to_load)
            
            # ... (the rest of your data loading logic is perfect) ...
            df['review_date'] = pd.to_datetime(df['Time'], unit='s')
            df_to_load = df[['ProductId', 'UserId', 'Score', 'Summary', 'Text', 'review_date']].rename(columns={'ProductId': 'product_id', 'UserId': 'user_id'})
            df_to_load.to_sql('reviews', con=connection, if_exists='append', index=False)
            print("Raw reviews subset loaded successfully.")

            # === STEP 2: ANALYZE REVIEWS AND GENERATE INSIGHTS ===
            print("\nStep 2: Analyzing reviews for all loaded products...")
            all_products_df = pd.read_sql("SELECT DISTINCT product_id FROM reviews LIMIT 20", connection)
            total_products = len(all_products_df)
            
            for index, row in all_products_df.iterrows():
                product_id = row['product_id']
                print(f"\nProcessing product {index + 1}/{total_products}: {product_id}")

                product_reviews_df = pd.read_sql(
                    text("SELECT text, review_date FROM reviews WHERE product_id = :pid"),
                    connection, params={'pid': product_id}
                )

                if product_reviews_df.empty:
                    continue

                print(f"  Found {len(product_reviews_df)} reviews to analyze...")
                analysis_result = analyze_review_batch(product_reviews_df['text'].tolist())
                
                if analysis_result:
                    summary_date = product_reviews_df['review_date'].max().date()
                    
                    insert_query = text("""
                        INSERT INTO review_insights 
                        (product_id, summary_date, positive_pct, neutral_pct, negative_pct, top_praise, top_issue)
                        VALUES (:pid, :s_date, :pos_pct, :neu_pct, :neg_pct, :praise, :issue)
                    """)
                    
                    connection.execute(insert_query, {
                        'pid': product_id, 's_date': summary_date,
                        'pos_pct': analysis_result['sentiment_breakdown'].get('positive_pct'),
                        'neu_pct': analysis_result['sentiment_breakdown'].get('neutral_pct'),
                        'neg_pct': analysis_result['sentiment_breakdown'].get('negative_pct'),
                        'praise': analysis_result.get('top_praise'),
                        'issue': analysis_result.get('top_issue')
                    })
                    print(f"  Successfully stored insights for product {product_id}")
                
                print("  --- Waiting 25.25 second to respect API rate limits ---")
                time.sleep(25.25) 

            trans.commit()
            print("\nETL pipeline finished successfully!")
        except Exception as e:
            trans.rollback()
            print(f"An error occurred: {e}. Transaction rolled back.")

if __name__ == '__main__':
    run_etl_pipeline(initial_rows_to_load=5000)