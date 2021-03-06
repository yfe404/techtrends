import sys
from os.path import exists
import sqlite3

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort

import logging

# set logger to handle STDOUT and STDERR 
stdout_handler = logging.StreamHandler(sys.stdout) # stdout handler 
stderr_handler = logging.StreamHandler(sys.stderr) # stderr handler 
handlers = [stderr_handler, stdout_handler]


# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    return connection

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'


# Increment counter of DB access by one
def increment_db_access_count():
    connection = sqlite3.connect('database.db')

    cur = connection.cursor()

    cur.execute("UPDATE metrics SET counter = counter + 1 WHERE id like 'access'")
    connection.commit()
    connection.close()

# Define the main route of the web application 
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)


@app.route('/metrics')
def metrics():

    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    count_access = connection.execute('SELECT counter FROM metrics WHERE id = "access"').fetchone()['counter']

    payload = {
        "db_connection_count": count_access,
        "post_count": len(posts)
    }
    
    response = app.response_class(
            response=json.dumps(payload),
            status=200,
            mimetype='application/json'
    )
    
    return response



# Define healthcheck route of the web application 
@app.route('/healthz')
def healthz():

    file_exists = exists("./database.db")

    if file_exists:
        response = app.response_class(
            response=json.dumps({"result":"OK - healthy"}),
            status=200,
            mimetype='application/json'
        )


    else:
        response = app.response_class(
            response=json.dumps({"result":"Error - unhealthy"}),
            status=500,
            mimetype='application/json'
        )

        
    return response


# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
        app.logger.error('Non-existing article is accessed!')
        return render_template('404.html'), 404
    else:
        app.logger.info('Article {} retrieved!'.format(post["title"]))
        increment_db_access_count()
        return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.info('About Us page is accessed.')
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()
            increment_db_access_count()
            app.logger.info('Article has been created!'.format({title}))
            return redirect(url_for('index'))

    return render_template('create.html')

# start the application on port 3111
if __name__ == "__main__":
   for handler in handlers:
      handler.setFormatter(logging.Formatter(
          '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
      ))
      app.logger.addHandler(handler)

   app.logger.setLevel(logging.DEBUG)
   app.run(host='0.0.0.0', port='3111')
