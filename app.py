import os
os.environ['MPLBACKEND'] = 'Agg'

from flask import Flask, render_template, request, send_file
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from peewee import *
from playhouse.db_url import connect

db = connect('sqlite:///movie_database.db')


class Movie(Model):
    title = CharField()
    genre = CharField()
    year = IntegerField()
    rating = FloatField()
    budget = IntegerField()
    revenue = IntegerField()

    class Meta:
        database = db


db.connect()
db.create_tables([Movie], safe=True)


app = Flask(__name__, template_folder='templates')


def load_movie_data():
    if Movie.select().count() == 0:
        df = pd.read_csv('movies_dataset.csv')
        movies_to_insert = []
        for _, row in df.iterrows():
            movie = Movie(
                title=row['title'],
                genre=row['genre'],
                year=row['year'],
                rating=row['rating'],
                budget=row['budget'],
                revenue=row['revenue']
            )
            movies_to_insert.append(movie)
        
        with db.atomic():
            Movie.bulk_create(movies_to_insert)


@app.route('/')
def home():
    load_movie_data()
    total_movies = Movie.select().count()
    return render_template('home.html', total_movies=total_movies)


@app.route('/genre_analysis')
def genre_analysis():
    genre_counts = (Movie
        .select(Movie.genre, fn.COUNT().alias('count'))
        .group_by(Movie.genre)
        .order_by(fn.COUNT().desc())
    )

    plt.figure(figsize=(10, 6))
    genres = [gc.genre for gc in genre_counts]
    counts = [gc.count for gc in genre_counts]
    plt.pie(counts, labels=genres, autopct='%1.1f%%')
    plt.title('Movie Distribution by Genre')
    genre_pie_chart = plot_to_base64()

    return render_template('genre_analysis.html', 
                           genre_counts=genre_counts, 
                           genre_pie_chart=genre_pie_chart)


@app.route('/financial_analysis', methods=['GET', 'POST'])
def financial_analysis():
    min_year = request.form.get('min_year', 2000)
    max_year = request.form.get('max_year', 2022)

    financial_query = (Movie
        .select(
            Movie.year, 
            fn.AVG(Movie.budget).alias('avg_budget'),
            fn.AVG(Movie.revenue).alias('avg_revenue')
        )
        .where((Movie.year >= min_year) & (Movie.year <= max_year))
        .group_by(Movie.year)
        .order_by(Movie.year)
    )

    plt.figure(figsize=(12, 6))
    years = [row.year for row in financial_query]
    budgets = [row.avg_budget for row in financial_query]
    revenues = [row.avg_revenue for row in financial_query]

    x = range(len(years))
    plt.bar([i-0.2 for i in x], budgets, width=0.4, label='Avg Budget', color='blue')
    plt.bar([i+0.2 for i in x], revenues, width=0.4, label='Avg Revenue', color='green')
    plt.xlabel('Year')
    plt.ylabel('Amount ($)')
    plt.title(f'Movie Budget vs Revenue ({min_year}-{max_year})')
    plt.xticks(x, years, rotation=45)
    plt.legend()

    financial_chart = plot_to_base64()

    return render_template('financial_analysis.html', 
                           financial_data=financial_query,
                           financial_chart=financial_chart,
                           min_year=min_year,
                           max_year=max_year)


@app.route('/rating_distribution')
def rating_distribution():
    query = "SELECT * FROM movie"
    movies_df = pd.read_sql(query, db.connection())
    
    plt.figure(figsize=(10, 6))
    plt.hist(movies_df['rating'], bins=20, edgecolor='black')
    plt.title('Distribution of Movie Ratings')
    plt.xlabel('Rating')
    plt.ylabel('Frequency')
    
    rating_histogram = plot_to_base64()
    rating_stats = {
        'mean_rating': movies_df['rating'].mean(),
        'median_rating': movies_df['rating'].median(),
        'min_rating': movies_df['rating'].min(),
        'max_rating': movies_df['rating'].max()
    }

    return render_template('rating_distribution.html', 
                           rating_histogram=rating_histogram,
                           rating_stats=rating_stats)


def plot_to_base64():
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)