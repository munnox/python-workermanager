# run this with:
# uwsgi --socket 0.0.0.0:5000 --protocol=http -w wsgi:app
from flask_worker import app

if __name__ == "__main__":
    app.run()