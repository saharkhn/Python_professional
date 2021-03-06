import mysql.connector
import re
from bs4 import BeautifulSoup
import requests
import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlalchemy import create_engine


cnx = mysql.connector.connect(user='root', password='sahar1376',
                              host='127.0.0.1',
                              database='bama_cars')

cursor = cnx.cursor()
cursor.execute('SET NAMES utf8;')
cursor.execute('SET CHARACTER SET utf8;')
cursor.execute('SET character_set_connection=utf8;')

# Get data from pages
# You can change the number of pages
for i in range(1, 10):
    url_name = ('https://bama.ir/car/all-brands/all-models/all-trims?page=%d' % i)
    res = requests.get(url_name)
    web_data = res.text
    soup = BeautifulSoup(web_data, 'html.parser')
    list_data = soup.find_all('div', attrs={'class': 'listdata'})

    for data in list_data:
        car_name_model = data.find('h2', attrs={'itemprop': 'name'})
        car_name_model = re.sub(r'\s+', ' ', car_name_model.text).strip('،').split('،')
        car_name = '%s' % (car_name_model[1])

        try:
            car_model = car_name_model[2]
        except IndexError:
            car_model = '-'
        performance = data.find('p', attrs={'class': 'price hidden-xs'})
        performance = performance.get_text()
        performance = re.sub(r'\s+', '', performance).strip()
        performance = performance.replace('کارکرد', '')
        performance = performance.replace(',', '')
        if performance == 'صفر':
            performance = 0
        try:
            performance = int(performance)
        except ValueError:
            continue
        if data.find('span', attrs={'itemprop': 'price'}):
            price = data.find('span', attrs={'itemprop': 'price'})
        elif data.find('p', attrs={'itemprop': 'price'}):
            price = data.find('p', attrs={'itemprop': 'price'})
        else:
            price = data.find('span', attrs={'itemprop': 'priceCurrency'})
        price = re.sub(r'\s+', '', price.text).strip()
        price = price.replace(',', '')
        try:
            price = int(price)
        except ValueError:
            continue
        city = data.find('span', attrs={'class': 'provice-mobile'})
        city = re.sub(r'\s+', '', city.text).strip()
        city = city.replace('،', '')

        query = 'INSERT INTO car_all_info(car_name, car_model, performance, city, price) VALUES (\'%s\', \'%s\', \'%i\', \'%s\', \'%i\')' % (
        car_name, car_model, performance, city, price)

        try:
            cursor.execute(query)
            cnx.commit()
        except (mysql.connector.errors.IntegrityError, mysql.connector.errors.InterfaceError):
            continue


#Query on Database
cursor.execute('select DISTINCT car_name from car_all_info where price > 100000000')
selected_data = cursor.fetchall()
for data in selected_data:
    print('%s' % data)


# ML Coding
db_connection_str = 'mysql+pymysql://root:sahar1376@127.0.0.1/bama_cars'
db_connection = create_engine(db_connection_str)

# new_data -> guess price !
new_data = [' توسان (ix35) ', ' 2.0 لیتر دو دیفرانسیل ', 26000, 'تهران ']
data_to_predict = [new_data[2]]

# Limit data in database
query = ('select * from car_all_info where car_name = %s and city = %s')
data_car_name_city = (new_data[0], new_data[3],)
df = pd.read_sql(query, con=db_connection, params=data_car_name_city)

# LabelEncoding -> car_model
car_model_list = []
dummies = pd.get_dummies(df.car_model)
for dum in dummies:
    if dum == new_data[1]:
        model = 1
        data_to_predict.append(model)
    else:
        model = 0
        data_to_predict.append(model)

merged = pd.concat([df, dummies], axis='columns')
final = merged.drop(['car_model', 'car_name', 'city'], axis='columns')
model = LinearRegression()

X = final.drop('price', axis='columns')
y = final.price

model.fit(X, y)
print(model.predict([data_to_predict]))

cnx.close()
