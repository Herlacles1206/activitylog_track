# create virtual environment

    python -m venv myenv

# activate venv

    1. windows
        myenv\Scripts\activate

    2. mac
        source myenv/bin/activate

# install dependencies

    pip install -r requirements.txt

# build exe

    pyinstaller Log.py
