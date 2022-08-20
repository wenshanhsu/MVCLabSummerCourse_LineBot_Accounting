# Homework - LineBot_Accounting

## Setup
### Install InfluxDB(1.X) with apt

    sudo curl -sL https://repos.influxdata.com/influxdb.key | sudo apt-key add -
    sudo echo "deb https://repos.influxdata.com/ubuntu bionic stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
    sudo apt update
    sudo apt install influxdb

### Start InfluxDB service

    sudo systemctl enable influxdb
    sudo systemctl start influxdb
    sudo service influxdb start


### How to run
* **Step 1: Install Python Packages**
    * > pip install -r requirements.txt
* **Step 2: Modifiy `.env.sample` and save as `.env`**
    ```
    LINE_TOKEN = Your Line Token
    LINE_SECRET = Your Line Secret
    LINE_UID = Your Line UID
    ```
* **Step 3: Run `main.py`**
    * The port used in main.py is '8787'
    * > python3 main.py

* **Step 4: Run ngrok**
    * > ngrok http 8787
    

## How to use in LineBot
*  #note [event] [+/-] [money]
    * Accounting !
*  #report
    *  Show current billing !
*  #delete [item]
    * Delete a piece of information !
*  #sum [time shift]
    * Settle consumption for a certain time interval !
    * ex: #sum 1d
*  #help
    * View hint
*  Input any sticker
    * Return random sticker
