#!/bin/bash

# Update the package list to get the latest version of packages
sudo apt update

# Install unzip, Git, Python, and PostgreSQL
sudo apt install unzip git python3 -y

sudo apt install -y python3.11-venv
# Create a Python virtual environment
python3 -m venv myenv

# Activate the virtual environment
source myenv/bin/activate



# Install dependencies from requirements.txt
pip install -r requirements.txt

# Install psycopg2
sudo apt install -y libpq-dev
pip install psycopg2-binary




# Output a message indicating the installation and setup is complete
echo "Git, Python, PostgreSQL, database 'cloud_database', user 'postgres', and password 'Darshan16' have been installed and configured."
echo "GitHub repository cloned, Python environment has been set up, dependencies installed, and the application is running."
