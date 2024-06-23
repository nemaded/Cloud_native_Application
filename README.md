# WebApp 

1
**Installations for local environment**
Steps :
1. Go to the WebApp folder
2. create he .env file in WebApp folder (fields should be PGPASSWORD= Darshan16
PGHOST= localhost
DATABASE_HOSTNAME
DATABASE_PASSWORD
DATABASE_NAME
DATABASE_USERNAME)
3. setup virtual environment using **python -m venv venv**
4. activate the virtual environment **.\venv\Scripts\activate**
5. install the app requirements **pip install -r requirements.txt**
6. start the application using **uvicorn App.main.app**

**Installations for debian environment**
install python, postgressql and psycopg2 manually 
# Copy git_latest_night.zip to remote machine
scp -i ./.ssh/digital_ocean ./ziped_file.zip root@142.93.1.37:~

# Update apt package manager
sudo apt update

# Install Python3
sudo apt install python3

# Install pyenv
curl <https://pyenv.run> | bash

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start and enable PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Set password for PostgreSQL user
sudo -u postgres psql
\\password postgres

# Create database and user
CREATE DATABASE Cloud_Database;
CREATE USER postgres WITH PASSWORD 'Darshan16';
GRANT ALL PRIVILEGES ON DATABASE Cloud_Database TO postgres;
\\q

# Configure PostgreSQL to use password authentication
sudo nano $(pg_config --sysconfdir)/postgresql.conf
# Change "peer" to "md5" for local connections

# Restart PostgreSQL service
sudo systemctl restart postgresql

# Connect to Cloud_Database
psql -h localhost -U postgres -d Cloud_Database
\\q

# Create .env file
nano .env

# Install unzip
sudo apt install unzip

# Unzip DarshanNemade_002790266_03
unzip DarshanNemade_002790266_03

# Install Python3.11-venv
sudo apt install python3.11-venv

# Create and activate virtual environment
python3 -m venv myenv
source myenv/bin/activate

# Edit requirements.txt file
nano requirements.txt
# Remove psycopg2 and install it manually

# Install required packages
pip install -r requirements.txt

sudo apt install libpq-dev

pip install psycopg2-binary

pip install uvicorn

Inthe main.py file in App folder change he path of the users.csv file to the path where you have csv
give the credentials manually 
