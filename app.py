import json
import os
from flask import Flask, render_template
from fju_scraper import run_scraper # 引入爬蟲模組
app = Flask(__name__)

@app.route("/")
def home():
    run_scraper() 
    
    if os.path.exists("news.json"):
        with open("news.json", "r", encoding="utf-8") as f:
            all_news = json.load(f)
    else:
        all_news = []
        
    return render_template("index.html", news_list=all_news)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/achievements")
def achievements():
    return render_template("achievements.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/update_news")
def update_news():
    print("啟動爬蟲程式，這可能需要幾秒鐘...")
    
    run_scraper() 
    
    return redirect(url_for('home'))

if __name__ == "__main__":

    app.run(host="0.0.0.0",debug=True, port=5000)

