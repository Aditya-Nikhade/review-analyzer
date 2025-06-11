# app.py
import os
from flask import Flask, render_template, jsonify, request
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Added a default local connection string for easier local testing
db_url = os.getenv("DATABASE_URL", "mysql+mysqlconnector://root:password123@localhost:3306/review_db")
engine = create_engine(db_url)

# The API server is a "consumer" of the database.
# The pipeline.py script is the "producer" and handles all schema creation.

@app.route('/')
def dashboard():
    """Renders the main dashboard HTML page."""
    return render_template('dashboard.html')

@app.route('/products')
def get_products():
    """Returns a list of unique product IDs from the database to populate the dropdown."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT DISTINCT product_id FROM reviews ORDER BY product_id;"))
            products = [row[0] for row in result]
            return jsonify(products)
    except Exception as e:
        print(f"Error fetching products: {e}")
        return jsonify({"error": "Could not fetch product list from the database."}), 500

@app.route('/dashboard_data')
def get_dashboard_data():
    """Returns aggregated insight data for a specific product."""
    product_id = request.args.get('product_id')
    if not product_id:
        return jsonify({"error": "product_id is a required parameter"}), 400

    try:
        with engine.connect() as connection:
            # Get the most recent sentiment summary for the selected product
            sentiment_query = text("""
                SELECT positive_pct, neutral_pct, negative_pct, top_praise, top_issue
                FROM review_insights
                WHERE product_id = :product_id
                ORDER BY summary_date DESC LIMIT 1
            """)
            sentiment_result = connection.execute(sentiment_query, {'product_id': product_id}).mappings().fetchone()
            
            # Get rating trends for the last 365 days
            rating_query = text("""
                SELECT DATE(review_date) as date, AVG(score) as avg_score, COUNT(*) as review_count
                FROM reviews
                WHERE product_id = :product_id AND review_date >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)
                GROUP BY DATE(review_date) ORDER BY date
            """)
            rating_result = connection.execute(rating_query, {'product_id': product_id}).mappings().fetchall()

            # Prepare a clean response, handling cases where no analysis exists for a product
            response_data = {
                "sentimentDistribution": {
                    "positive": sentiment_result.get('positive_pct', 0) if sentiment_result else 0,
                    "neutral": sentiment_result.get('neutral_pct', 0) if sentiment_result else 0,
                    "negative": sentiment_result.get('negative_pct', 0) if sentiment_result else 0
                },
                "topPraise": sentiment_result.get('top_praise', "No analysis available.") if sentiment_result else "No analysis available.",
                "topIssue": sentiment_result.get('top_issue', "No analysis available.") if sentiment_result else "No analysis available.",
                "ratingTrend": [{
                    "date": row['date'].strftime("%Y-%m-%d"),
                    "avgScore": float(row['avg_score']),
                    "reviewCount": row['review_count']
                } for row in rating_result]
            }
            return jsonify(response_data)
    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        return jsonify({"error": "An internal error occurred while fetching dashboard data."}), 500

if __name__ == '__main__':
    app.run(debug=True)